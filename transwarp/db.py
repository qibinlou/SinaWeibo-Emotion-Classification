#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__ = 'Michael Liao'

'''
Database operation module. This module is independent with web module.
'''

import os, re, sys, time, uuid, socket, datetime, functools, threading, logging, collections

logging.basicConfig(level=logging.INFO)

class _IdGenerator():
    def __init__(self, server_id=0):
        '''
        Init an id generator with server id. Server id can be automatically got from 
        hostname. e.g. 'server-100' => 100, 'test01' => 1.

        Server id makes each server generate different id at the same time.
        '''
        if server_id == 0:
            m = re.match('^[^0-9]*([0-9]+)$', socket.gethostname())
            if m:
                server_id = int(m.group(1)) & 255
        self.server_id = server_id
        self.time_reduction = 1262275200000
        self.last_time = self._get_current_time()
        self.auto_increase = 0

    def _get_current_time(self):
        return long((time.time() * 1000 - self.time_reduction)) >> 8

    def next_id(self):
        current = self._get_current_time()
        if current < self.last_time:
            current = self.last_time
            self.auto_increase = 0
        elif current > self.last_time:
            self.auto_increase = 0
        elif (current == self.last_time) and ((self.auto_increase & 0x1fffff) == 0x100000):
            current += 1
            self.auto_increase = 0
        self.last_time = current
        next = (current << 28) | (0xfffff00L & (self.auto_increase << 8)) | self.server_id
        self.auto_increase += 1
        return next

_id_generator = None

def next_int():
    return _id_generator.next_id()

def next_str():
    return '%018d%s' % (int(time.time()*100000), uuid.uuid4().hex)

class _Dict(dict):
    '''
    Simple dict but support access as x.y style.

    >>> d1 = _Dict()
    >>> d1['x'] = 100
    >>> d1.x
    100
    >>> d1.y = 200
    >>> d1['y']
    200
    >>> d2 = _Dict(a=1, b=2, c='3')
    >>> d2.c
    '3'
    >>> d2['empty']
    Traceback (most recent call last):
        ...
    KeyError: 'empty'
    >>> d2.empty
    Traceback (most recent call last):
        ...
    KeyError: 'empty'
    >>> d3 = _Dict(('a', 'b', 'c'), (1, 2, 3))
    >>> d3.a
    1
    >>> d3.b
    2
    >>> d3.c
    3
    '''
    def __init__(self, names=(), values=(), **kw):
        super(_Dict, self).__init__(**kw)
        for k, v in zip(names, values):
            self[k] = v

    def __getattr__(self, key):
        return self[key]

    def __setattr__(self, key, value):
        self[key] = value

class DBError(Exception):
    pass

class MultiResultsError(DBError):
    pass

class MultiColumnsError(DBError):
    pass

class NoResultError(DBError):
    pass

def _log(s):
    logging.info(s)

def _db_connect():
    '''
    Connect function used for get db connection. This function will be relocated in init(dbn, ...).
    '''
    raise DBError('Database is not initialized. call init(dbn, ...) first.')

_db_convert = '?'

class DbCtx(threading.local):
    '''
    Thread local object that holds connection info.
    '''
    def __init__(self):
        self.connection = None
        self.transactions = 0

    def init(self):
        _log('open connection...')
        self.connection = _db_connect()
        self.transactions = 0

    def cleanup(self):
        _log('cleanup connection...')
        self.connection.close()
        self.connection = None

    def open_cursor(self):
        '''
        Return cursor
        '''
        return self.connection.cursor()

_db_ctx = DbCtx()

class _Connection(object):
    '''
    Connection object that can open and close connection. Connection object can be nested and only the most 
    outer connection has effect.

    with _Connection():
        pass
        with _Connection():
            pass
    '''
    def __enter__(self):
        global _db_ctx
        self.should_cleanup = False
        if _db_ctx.connection is None:
            _db_ctx.init()
            self.should_cleanup = True
        return self

    def __exit__(self, exctype, excvalue, traceback):
        global _db_ctx
        if self.should_cleanup:
            _db_ctx.cleanup()

def connection():
    '''
    Return _Connection object that can be used by 'with' statement:

    with connection():
        pass
    '''
    return _Connection()

def with_connection(func):
    '''
    Decorator for reuse connection.

    @with_connection
    def foo(*args, **kw):
        f1()
        f2()
        f3()
    '''
    @functools.wraps(func)
    def _wrapper(*args, **kw):
        with _Connection():
            return func(*args, **kw)
    return _wrapper

class _Transaction(object):
    '''
    Transaction object that can handle transactions.

    with _Transaction():
        pass
    '''

    def __enter__(self):
        global _db_ctx
        _db_ctx.transactions = _db_ctx.transactions + 1
        _log('begin transaction...' if _db_ctx.transactions==1 else 'join current transaction...')
        return self

    def __exit__(self, exctype, excvalue, traceback):
        global _db_ctx
        _db_ctx.transactions = _db_ctx.transactions - 1
        if _db_ctx.transactions==0:
            if exctype is None:
                self.commit()
            else:
                self.rollback()

    def commit(self):
        global _db_ctx
        _log('commit transaction...')
        try:
            _db_ctx.connection.commit()
            _log('commit ok.')
        except:
            _log('commit failed. try rollback...')
            _db_ctx.connection.rollback()
            log('rollback ok.')
            raise

    def rollback(self):
        global _db_ctx
        _log('rollback transaction...')
        _db_ctx.connection.rollback()
        _log('rollback ok.')

def transaction():
    '''
    Create a transaction object so can use with statement:

    with transaction():
        pass
    '''
    # make sure a transaction is associated a valid connection:
    with _Connection():
        return _Transaction()

def with_transaction(func):
    '''
    A decorator that makes function around transaction.

    >>> @with_transaction
    ... def update_profile(id, name, rollback):
    ...     u = dict(id=id, name=name, email='%s@test.org' % name, passwd=name, last_modified=time.time())
    ...     insert('user', **u)
    ...     r = update('update user set passwd=? where id=?', name.upper(), id)
    ...     if rollback:
    ...         raise StandardError('will cause rollback...')
    >>> update_profile(8080, 'Julia', False)
    >>> select_one('select * from user where id=?', 8080).passwd
    u'JULIA'
    >>> update_profile(9090, 'Robert', True)
    Traceback (most recent call last):
      ...
    StandardError: will cause rollback...
    >>> select('select * from user where id=?', 9090)
    []
    '''
    @functools.wraps(func)
    def _wrapper(*args, **kw):
        # make sure a transaction is associated a valid connection:
        with _Connection():
            with _Transaction():
                return func(*args, **kw)
    return _wrapper

def _select(sql, unique, *args):
    ' execute select SQL and return unique result or list results.'
    global _db_ctx, _db_convert
    cursor = None
    if _db_convert != '?':
        sql = sql.replace('?', _db_convert)
    _log('SQL: %s, ARGS: %s' % (sql, args))
    try:
        cursor = _db_ctx.connection.cursor()
        cursor.execute(sql, args)
        if cursor.description:
            names = [x[0] for x in cursor.description]
        if unique:
            values = cursor.fetchone()
            if not values:
                raise NoResultError('Empty result')
            if cursor.fetchone():
                raise MultiResultsError('Expect unique result')
            return _Dict(names, values)
        return [_Dict(names, x) for x in cursor.fetchall()]
    finally:
        if cursor:
            cursor.close()

@with_connection
def select_one(sql, *args):
    '''
    Execute select SQL and expected one and only one result. 
    If no result found, NoResultError raises. 
    If multiple results found, MultiResultsError raises.

    >>> u1 = dict(id=100, name='Alice', email='alice@test.org', passwd='ABC-12345', last_modified=time.time())
    >>> u2 = dict(id=101, name='Sarah', email='sarah@test.org', passwd='ABC-12345', last_modified=time.time())
    >>> insert('user', **u1)
    1
    >>> insert('user', **u2)
    1
    >>> u = select_one('select * from user where id=?', 100)
    >>> u.name
    u'Alice'
    >>> select_one('select * from user where email=?', 'abc@email.com')
    Traceback (most recent call last):
        ...
    NoResultError: Empty result
    >>> select_one('select * from user where passwd=?', 'ABC-12345')
    Traceback (most recent call last):
        ...
    MultiResultsError: Expect unique result
    '''
    return _select(sql, True, *args)

@with_connection
def select_int(sql, *args):
    '''
    Execute select SQL and expected one int and only one int result. 
    If no result found, NoResultError raises. 
    If multiple results found, MultiResultsError raises.

    >>> n = update('delete from user')
    >>> u1 = dict(id=96900, name='Ada', email='ada@test.org', passwd='A-12345', last_modified=time.time())
    >>> u2 = dict(id=96901, name='Adam', email='adam@test.org', passwd='A-12345', last_modified=time.time())
    >>> insert('user', **u1)
    1
    >>> insert('user', **u2)
    1
    >>> select_int('select count(*) from user')
    2
    >>> select_int('select count(*) from user where email=?', 'ada@test.org')
    1
    >>> select_int('select count(*) from user where email=?', 'notexist@test.org')
    0
    >>> select_int('select id from user where email=?', 'ada@test.org')
    96900
    >>> select_int('select id, name from user where email=?', 'ada@test.org')
    Traceback (most recent call last):
        ...
    MultiColumnsError: Expect only one column.
    '''
    d = _select(sql, True, *args)
    if len(d)!=1:
        raise MultiColumnsError('Expect only one column.')
    return d.values()[0]

@with_connection
def select(sql, *args):
    '''
    Execute select SQL and return list or empty list if no result.

    >>> u1 = dict(id=200, name='Wall.E', email='wall.e@test.org', passwd='back-to-earth', last_modified=time.time())
    >>> u2 = dict(id=201, name='Eva', email='eva@test.org', passwd='back-to-earth', last_modified=time.time())
    >>> insert('user', **u1)
    1
    >>> insert('user', **u2)
    1
    >>> L = select('select * from user where id=?', 900900900)
    >>> L
    []
    >>> L = select('select * from user where id=?', 200)
    >>> L[0].email
    u'wall.e@test.org'
    >>> L = select('select * from user where passwd=? order by id desc', 'back-to-earth')
    >>> L[0].name
    u'Eva'
    >>> L[1].name
    u'Wall.E'
    '''
    return _select(sql, False, *args)

def _update(sql, args):
    global _db_ctx, _db_convert
    cursor = None
    if _db_convert != '?':
        sql = sql.replace('?', _db_convert)
    _log('SQL: %s, ARGS: %s' % (sql, args))
    try:
        cursor = _db_ctx.connection.cursor()
        cursor.execute(sql, args)
        r = cursor.rowcount
        if _db_ctx.transactions==0:
            # no transaction enviroment:
            _log('auto commit')
            _db_ctx.connection.commit()
        return r
    finally:
        if cursor:
            cursor.close()

@with_connection
def insert(table, **kw):
    '''
    Execute insert SQL.

    >>> u1 = dict(id=2000, name='Bob', email='bob@test.org', passwd='bobobob', last_modified=time.time())
    >>> insert('user', **u1)
    1
    >>> u2 = select_one('select * from user where id=?', 2000)
    >>> u2.name
    u'Bob'
    >>> insert('user', **u2)
    Traceback (most recent call last):
      ...
    IntegrityError: column id is not unique
    '''
    cols, args = zip(*kw.iteritems())
    sql = 'insert into %s (%s) values (%s)' % (table, ','.join(cols), ','.join([_db_convert for i in range(len(cols))]))
    return _update(sql, args)

@with_connection
def update(sql, *args):
    '''
    Execute update SQL.

    >>> u1 = dict(id=1000, name='Michael', email='michael@test.org', passwd='123456', last_modified=time.time())
    >>> insert('user', **u1)
    1
    >>> u2 = select_one('select * from user where id=?', 1000)
    >>> u2.email
    u'michael@test.org'
    >>> u2.passwd
    u'123456'
    >>> update('update user set email=?, passwd=? where id=?', 'michael@example.org', '654321', 1000)
    1
    >>> u3 = select_one('select * from user where id=?', 1000)
    >>> u3.email
    u'michael@example.org'
    >>> u3.passwd
    u'654321'
    '''
    return _update(sql, args)

def update_kw(table, where, *args, **kw):
    '''
    Execute update SQL by table, where, args and kw.

    >>> u1 = dict(id=900900, name='Maya', email='maya@test.org', passwd='MAYA', last_modified=time.time())
    >>> insert('user', **u1)
    1
    >>> u2 = select_one('select * from user where id=?', 900900)
    >>> u2.email
    u'maya@test.org'
    >>> u2.passwd
    u'MAYA'
    >>> update_kw('user', 'id=?', 900900, name='Kate', email='kate@example.org')
    1
    >>> u3 = select_one('select * from user where id=?', 900900)
    >>> u3.name
    u'Kate'
    >>> u3.email
    u'kate@example.org'
    >>> u3.passwd
    u'MAYA'
    '''
    if len(kw)==0:
        raise ValueError('No kw args.')
    sqls = ['update', table, 'set']
    params = []
    updates = []
    for k, v in kw.iteritems():
        updates.append('%s=?' % k)
        params.append(v)
    sqls.append(', '.join(updates))
    sqls.append('where')
    sqls.append(where)
    sql = ' '.join(sqls)
    params.extend(args)
    return update(sql, *params)

def init_connector(func_connect, convert_char='%s'):
    global _db_connect, _db_convert
    _log('init connector...')
    _db_connect = func_connect
    _db_convert = convert_char

def init(db_type, db_schema, db_host, db_port=0, db_user=None, db_password=None, db_driver=None, **db_args):
    '''
    Initialize database.

    Args:
      db_type: db type, 'mysql', 'sqlite3'.
      db_schema: schema name.
      db_host: db host.
      db_user: username.
      db_password: password.
      db_driver: db driver, default to None.
      **db_args: other parameters, e.g. use_unicode=True
    '''
    global _db_connect, _db_convert
    if db_type=='mysql':
        _log('init mysql...')
        import MySQLdb
        if not 'use_unicode' in db_args:
            db_args['use_unicode'] = True
        if not 'charset' in db_args:
            db_args['charset'] = 'utf8'
        if db_port==0:
            db_port = 3306
        _db_connect = lambda: MySQLdb.connect(db_host, db_user, db_password, db_schema, db_port, **db_args)
        _db_convert = '%s'
    elif db_type=='sqlite3':
        _log('init sqlite3...')
        import sqlite3
        _db_connect = lambda: sqlite3.connect(db_schema)
    else:
        raise DBError('Unsupported db: %s' % db_type)

if __name__=='__main__':
    sys.path.append('.')
    dbpath = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'doc_test.sqlite3.db')
    _log(dbpath)
    if os.path.isfile(dbpath):
        os.remove(dbpath)
    init('sqlite3', dbpath, '')
    update('create table user (id int primary key, name text, email text, passwd text, last_modified real)')
    import doctest
    doctest.testmod()
    os.remove(dbpath)
