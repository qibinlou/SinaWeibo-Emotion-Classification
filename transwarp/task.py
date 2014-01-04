#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__ = 'Michael Liao'

'''
Task queue module for distributed async task.

A task statuses:

pending -> executing -> done -+-> notify
   |            |             |
   +-------- retry ? -> error +
'''

__SQL__ = '''
create table tasks (
    id varchar(50) not null,
    queue varchar(50) not null,
    name varchar(50) not null,
    callback varchar(1000) not null,
    timeout bigint not null,
    status varchar(50) not null,
    max_retry int not null,
    retried int not null,
    creation_time real not null,
    execution_time real not null,
    execution_start_time real not null,
    execution_end_time real not null,
    execution_expired_time real not null,
    version bigint not null,
    task_data blob not null,
    task_result blob not null,
    primary key(id),
    index(execution_time)
);
'''

import os, sys, time, uuid, random, datetime, functools, threading, logging, collections

from web import Dict
import db

logging.basicConfig(level=logging.INFO)

_DEFAULT_QUEUE = 'default'

_PENDING = 'pending'
_EXECUTING = 'executing'
_ERROR = 'error'
_DONE = 'done'

class ConflictError(StandardError):
    pass

def _log(s):
    logging.info(s)

def cleanup(queue=None):
    '''
    Remove tasks that already done.
    '''
    pass

def get_tasks(queue, status=None, offset=0, limit=100):
    '''
    Get tasks by queue and status.

    >>> tid1 = create_task('the_queue', 'task1', task_data='data1')
    >>> time.sleep(0.1)
    >>> tid2 = create_task('the_queue', 'task2', task_data='data2')
    >>> ts = get_tasks('the_queue')
    >>> ts[0].name
    u'task1'
    >>> ts[1].name
    u'task2'
    '''
    if offset<0:
        raise ValueError('offset must >=0')
    if limit<1 or limit>100:
        raise ValueError('limit must be 1 - 100')
    if status:
        return db.select('select * from tasks where queue=? and status=? order by execution_time limit ?,?', queue, status, offset, limit)
    return db.select('select * from tasks where queue=? order by execution_time limit ?,?', queue, offset, limit)

def create_task(queue, name, task_data=None, callback=None, max_retry=3, execution_time=None, timeout=60):
    '''
    Create a task.

    >>> tid = create_task('sample_queue', 'sample_task', 'task data')
    >>> f = fetch_task('sample_queue')
    >>> f.id==tid
    True
    >>> f.task_data
    u'task data'
    >>> f2 = fetch_task('sample_queue')
    >>> f2 is None
    True
    '''
    if not queue:
        queue = _DEFAULT_QUEUE
    if not name:
        name = 'unamed'
    if callback is None:
        callback = ''
    if callback and not callback.startswith('http://') and not callback.startswith('https://'):
        return dict(error='cannot_create_task', description='invalid callback')
    if task_data is None:
        task_data = ''
    if max_retry < 0:
        max_retry = 0
    if timeout <= 0:
        return dict(error='cannot_create_task', description='invalid timeout')
    current = time.time()
    if execution_time is None:
        execution_time = current
    task = dict( \
        id=db.next_str(), \
        queue=queue, \
        name=name, \
        callback=callback, \
        timeout=timeout, \
        status=_PENDING, \
        max_retry=max_retry, \
        retried=0, \
        creation_time=current, \
        execution_time=execution_time, \
        execution_start_time=0.0, \
        execution_end_time=0.0, \
        execution_expired_time=0.0, \
        task_data=task_data,
        task_result='',
        version=0)
    db.insert('tasks', **task)
    return task['id']

def _do_fetch_task(queue):
    task = None
    current = time.time()
    with db.transaction():
        tasks = db.select('select * from tasks where execution_time<? and queue=? and status=? order by execution_time limit ?', current, queue, _PENDING, 1)
        if tasks:
            task = tasks[0]
    if not task:
        return None
    expires = current + task.timeout
    with db.transaction():
        if 0==db.update('update tasks set status=?, execution_start_time=?, execution_expired_time=?, version=version+1 where id=? and version=?', _EXECUTING, current, expires, task.id, task.version):
            raise ConflictError()
    return Dict(id=task.id, queue=task.queue, name=task.name, task_data=task.task_data, version=task.version+1)

def fetch_task(queue):
    if not queue:
        queue = _DEFAULT_QUEUE
    for n in range(3):
        try:
            return _do_fetch_task(queue)
        except ConflictError:
            sleep(random.random() / 4)
    return None

def set_task_result(task_id, success, task_result=''):
    task = db.select_one('select id, status, max_retry, retried from tasks where id=?', task_id)
    kw = dict()
    if success:
        kw['status'] = _DONE
        kw['task_result'] = task_result
    else:
        retried = task.retried + 1
        kw['retried'] = retried
        kw['status'] = _ERROR if task.retried >= task.max_retry else _PENDING
    db.update_kw('tasks', 'id=?', task_id, **kw)

def set_task_timeout(task_id):
    pass

def delete_task(task_id):
    db.update('delete from tasks where id=?', task_id)

def notify_task(task):
    pass

if __name__=='__main__':
    sys.path.append('.')
    dbpath = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'doc_test.sqlite3.db')
    _log(dbpath)
    if os.path.isfile(dbpath):
        os.remove(dbpath)
    db.init('sqlite3', dbpath, '')
    db.update('create table tasks (id text not null, queue text not null, name text not null, callback text not null, timeout integer not null, status text not null, max_retry integer not null, retried integer not null, creation_time real not null, execution_time real not null, execution_start_time real not null, execution_end_time real not null, execution_expired_time real not null, version integer not null, task_data text not null, task_result text not null);')
    import doctest
    doctest.testmod()
    os.remove(dbpath)
