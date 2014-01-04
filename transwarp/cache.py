#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__ = 'Michael Liao'

'''
A simple cache interface.
'''

import os, time, datetime, functools, logging

class DummyClient(object):

    def set(self, key, value, expires=0):
        pass

    def get(self, key, default=None):
        return default

    def gets(self, *keys):
        return [None] * len(keys)

    def delete(self, key):
        pass

    def incr(self, key):
        pass

    def decr(self, key):
        pass

class MemcacheClient(object):

    def __init__(self, servers, debug=False):
        import memcache
        if isinstance(servers, basestring):
            servers = [servers]
        self._client = memcache.Client(servers, debug)

    def set(self, key, value, expires=0):
        '''
        Set object with key.

        Args:
            key: cache key as str.
            value: object value.
            expires: cache time, default to 0 (using default expires time)

        >>> key = uuid.uuid4().hex
        >>> c = MemcacheClient('localhost:11211')
        >>> c.set(key, u'Python\u4e2d\u6587')
        >>> c.get(key)
        u'Python\u4e2d\u6587'
        >>> c.set(key, 'Expires after 1 sec', 1)
        >>> c.get(key)
        'Expires after 1 sec'
        >>> time.sleep(2)
        >>> c.get(key, 'Not Exist')
        'Not Exist'
        '''
        self._client.set(key, value, expires)

    def get(self, key, default=None):
        '''
        Get object by key.

        Args:
            key: cache key as str.
            default: default value if key not found. default to None.
        Returns:
            object or default value if not found.

        >>> key = uuid.uuid4().hex
        >>> c = MemcacheClient('localhost:11211')
        >>> c.get(key)
        >>> c.get(key, 'DEFAULT_MC')
        'DEFAULT_MC'
        >>> c.set(key, 'hello, mc')
        >>> c.get(key)
        'hello, mc'
        '''
        r = self._client.get(key)
        return default if r is None else r

    def gets(self, *keys):
        '''
        Get objects by keys.

        Args:
            keys: cache keys as str.
        Returns:
            list of object.

        >>> key1 = uuid.uuid4().hex
        >>> key2 = uuid.uuid4().hex
        >>> key3 = uuid.uuid4().hex
        >>> c = MemcacheClient('localhost:11211')
        >>> c.gets(key1, key2, key3)
        [None, None, None]
        >>> c.set(key1, 'Key1')
        >>> c.set(key3, 'Key3')
        >>> c.gets(key1, key2, key3)
        ['Key1', None, 'Key3']
        '''
        r = self._client.get_multi(keys)
        return map(lambda k: r.get(k), keys)

    def delete(self, key):
        '''
        Delete object from cache by key.

        Args:
            key: cache key as str.

        >>> key = uuid.uuid4().hex
        >>> c = MemcacheClient('localhost:11211')
        >>> c.set(key, 'delete from mc')
        >>> c.get(key)
        'delete from mc'
        >>> c.delete(key)
        >>> c.get(key)
        '''
        self._client.delete(key)

    def incr(self, key):
        '''
        Increase counter.

        Args:
            key: cache key as str.

        >>> key = uuid.uuid4().hex
        >>> c = MemcacheClient('localhost:11211')
        >>> c.incr(key)
        1
        >>> c.incr(key)
        2
        >>> c.set(key, 100)
        >>> c.incr(key)
        101
        '''
        r = self._client.incr(key)
        if r is None:
            self._client.set(key, 1)
            r = 1
        return r

    def decr(self, key):
        '''
        Decrease counter. NOTE the memcache does not allow negative number, 
        so decr key = 0 will still return 0

        Args:
            key: cache key as str.

        >>> key = uuid.uuid4().hex
        >>> c = MemcacheClient('localhost:11211')
        >>> c.decr(key)
        0
        >>> c.decr(key)
        0
        >>> c.set(key, 100)
        >>> c.decr(key)
        99
        '''
        r = self._client.decr(key)
        if r is None:
            self._client.set(key, 0)
            r = 0
        return r

def _redis_after_get(r):
    if isinstance(r, str):
        if r.startswith('str:'):
            return r[4:]
        if r.startswith('uni:'):
            return r[4:].decode('utf-8')
    return r

class RedisClient(object):

    def __init__(self, servers, debug=False):
        import redis
        self._client = redis.StrictRedis(host=servers)

    def set(self, key, value, expires=0):
        '''
        Set object with key.

        Args:
            key: cache key as str.
            value: object value.
            expires: cache time, default to 0 (using default expires time)

        >>> key = uuid.uuid4().hex
        >>> c = RedisClient('localhost')
        >>> c.set(key, u'Python\u4e2d\u6587')
        >>> c.get(key)
        u'Python\u4e2d\u6587'
        >>> c.set(key, 'Expires after 1 sec', 1)
        >>> c.get(key)
        'Expires after 1 sec'
        >>> time.sleep(2)
        >>> c.get(key, 'Not Exist')
        'Not Exist'
        '''
        if isinstance(value, str):
            value = 'str:%s' % value
        if isinstance(value, unicode):
            value = 'uni:%s' % value.encode('utf-8')
        self._client.set(key, value)
        if expires:
            self._client.expire(key, expires)

    def get(self, key, default=None):
        '''
        Get object by key.

        Args:
            key: cache key as str.
            default: default value if key not found. default to None.
        Returns:
            object or default value if not found.

        >>> key = uuid.uuid4().hex
        >>> c = RedisClient('localhost')
        >>> c.get(key)
        >>> c.get(key, 'DEFAULT_REDIS')
        'DEFAULT_REDIS'
        >>> c.set(key, 'hello redis')
        >>> c.get(key)
        'hello redis'
        >>> c.set(key, 12345)
        >>> c.get(key)
        '12345'
        '''
        r = self._client.get(key)
        if r is None:
            return default
        return _redis_after_get(r)

    def gets(self, *keys):
        '''
        Get objects by keys.

        Args:
            keys: cache keys as str.
        Returns:
            list of object.

        >>> key1 = uuid.uuid4().hex
        >>> key2 = uuid.uuid4().hex
        >>> key3 = uuid.uuid4().hex
        >>> c = RedisClient('localhost')
        >>> c.gets(key1, key2, key3)
        [None, None, None]
        >>> c.set(key1, 'Key1')
        >>> c.set(key3, 'Key3')
        >>> c.gets(key1, key2, key3)
        ['Key1', None, 'Key3']
        '''
        return map(_redis_after_get, self._client.mget(keys))

    def delete(self, key):
        '''
        Delete object from cache by key.

        Args:
            key: cache key as str.

        >>> key = uuid.uuid4().hex
        >>> c = RedisClient('localhost')
        >>> c.set(key, 'delete from redis')
        >>> c.get(key)
        'delete from redis'
        >>> c.delete(key)
        >>> c.get(key)
        '''
        self._client.delete(key)

    def incr(self, key):
        '''
        Increase counter.

        Args:
            key: cache key as str.

        >>> key = uuid.uuid4().hex
        >>> c = RedisClient('localhost')
        >>> c.incr(key)
        1
        >>> c.incr(key)
        2
        >>> c.set(key, 100)
        >>> c.incr(key)
        101
        '''
        return self._client.incr(key)

    def decr(self, key):
        '''
        Decrease counter.

        Args:
            key: cache key as str.

        >>> key = uuid.uuid4().hex
        >>> c = RedisClient('localhost')
        >>> c.decr(key)
        -1
        >>> c.decr(key)
        -2
        >>> c.set(key, 100)
        >>> c.decr(key)
        99
        '''
        return self._client.decr(key)

client = DummyClient()

if __name__=='__main__':
    import uuid, doctest
    doctest.testmod()
