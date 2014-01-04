#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''
A simple, lightweight, WSGI-compatible web framework.
'''

__author__ = 'Michael Liao'

import __builtin__
import types, sys, os, re, cgi, sys, base64, json, time, hashlib, inspect, datetime, functools, mimetypes, threading, logging, urllib, collections, linecache

# thread local object for storing request and response.
ctx = threading.local()

class Dict(dict):
    '''
    Simple dict but support access as x.y style.

    >>> d1 = Dict()
    >>> d1['x'] = 100
    >>> d1.x
    100
    >>> d1.y = 200
    >>> d1['y']
    200
    >>> d2 = Dict(a=1, b=2, c='3')
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
    '''
    def __getattr__(self, key):
        return self[key]

    def __setattr__(self, key, value):
        self[key] = value

def _json_loads(s, expected=None):
    '''
    Loads json.

    >>> r = _json_loads(r'{"test": "ok", "users": [{"name": "Michael"}, {"name": "Tracy"}]}')
    >>> r.test
    u'ok'
    >>> r.users[0].name
    u'Michael'
    >>> r.users[1].name
    u'Tracy'
    >>> r = _json_loads(r'{"test": "ok"}', expected=(list, tuple))
    Traceback (most recent call last):
      ...
    TypeError: Object loaded from json is not expected type: (<type 'list'>, <type 'tuple'>)
    '''
    r = json.loads(s, object_pairs_hook=Dict)
    if expected:
        if not isinstance(r, expected):
            raise TypeError('Object loaded from json is not expected type: %s' % str(expected))
    return r

def _json_dumps(obj):
    '''
    Dumps any object as json string.

    >>> class Person(object):
    ...     def __init__(self, name):
    ...         self.name = name
    >>> _json_dumps([Person('Bob'), None])
    '[{"name": "Bob"}, null]'
    '''
    def _dump_obj(obj):
        if isinstance(obj, dict):
            return obj
        d = dict()
        for k in dir(obj):
            if not k.startswith('_'):
                d[k] = getattr(obj, k)
        return d
    return json.dumps(obj, default=_dump_obj)

# all known response statues:
_RESPONSE_STATUSES = {
    # Informational
    100: 'Continue',
    101: 'Switching Protocols',
    102: 'Processing',

    # Successful
    200: 'OK',
    201: 'Created',
    202: 'Accepted',
    203: 'Non-Authoritative Information',
    204: 'No Content',
    205: 'Reset Content',
    206: 'Partial Content',
    207: 'Multi Status',
    226: 'IM Used',

    # Redirection
    300: 'Multiple Choices',
    301: 'Moved Permanently',
    302: 'Found',
    303: 'See Other',
    304: 'Not Modified',
    305: 'Use Proxy',
    307: 'Temporary Redirect',

    # Client Error
    400: 'Bad Request',
    401: 'Unauthorized',
    402: 'Payment Required',
    403: 'Forbidden',
    404: 'Not Found',
    405: 'Method Not Allowed',
    406: 'Not Acceptable',
    407: 'Proxy Authentication Required',
    408: 'Request Timeout',
    409: 'Conflict',
    410: 'Gone',
    411: 'Length Required',
    412: 'Precondition Failed',
    413: 'Request Entity Too Large',
    414: 'Request URI Too Long',
    415: 'Unsupported Media Type',
    416: 'Requested Range Not Satisfiable',
    417: 'Expectation Failed',
    418: "I'm a teapot",
    422: 'Unprocessable Entity',
    423: 'Locked',
    424: 'Failed Dependency',
    426: 'Upgrade Required',

    # Server Error
    500: 'Internal Server Error',
    501: 'Not Implemented',
    502: 'Bad Gateway',
    503: 'Service Unavailable',
    504: 'Gateway Timeout',
    505: 'HTTP Version Not Supported',
    507: 'Insufficient Storage',
    510: 'Not Extended',
}

_RE_RESPONSE_STATUS = re.compile(r'^\d\d\d(\ [\w\ ]+)?$')

_RESPONSE_HEADERS = (
    'Accept-Ranges',
    'Age',
    'Allow',
    'Cache-Control',
    'Connection',
    'Content-Encoding',
    'Content-Language',
    'Content-Length',
    'Content-Location',
    'Content-MD5',
    'Content-Disposition',
    'Content-Range',
    'Content-Type',
    'Date',
    'ETag',
    'Expires',
    'Last-Modified',
    'Link',
    'Location',
    'P3P',
    'Pragma',
    'Proxy-Authenticate',
    'Refresh',
    'Retry-After',
    'Server',
    'Set-Cookie',
    'Strict-Transport-Security',
    'Trailer',
    'Transfer-Encoding',
    'Vary',
    'Via',
    'Warning',
    'WWW-Authenticate',
    'X-Frame-Options',
    'X-XSS-Protection',
    'X-Content-Type-Options',
    'X-Forwarded-Proto',
    'X-Powered-By',
    'X-UA-Compatible',
)

_RESPONSE_HEADER_DICT = {}

for hdr in _RESPONSE_HEADERS:
    _RESPONSE_HEADER_DICT[hdr.upper()] = hdr

_HEADER_X_POWERED_BY = ('X-Powered-By', 'iTranswarp/1.0')

class HttpError(StandardError):
    '''
    HttpError that defines http error code.

    >>> e = HttpError(404)
    >>> e.status
    '404 Not Found'
    '''
    def __init__(self, code):
        '''
        Init an HttpError with response code.
        '''
        super(HttpError, self).__init__()
        self.status = '%d %s' % (code, _RESPONSE_STATUSES[code])

    def header(self, name, value):
        if not hasattr(self, '_headers'):
            self._headers = [_HEADER_X_POWERED_BY]
        self._headers.append((name, value))

    @property
    def headers(self):
        if hasattr(self, '_headers'):
            return self._headers
        return []

    def __str__(self):
        return self.status

class RedirectError(StandardError):
    '''
    RedirectError that defines http redirect code.

    >>> e = RedirectError(302, 'http://www.apple.com/')
    >>> e.status
    '302 Found'
    >>> e.location
    'http://www.apple.com/'
    '''
    def __init__(self, code, location):
        '''
        Init an HttpError with response code.
        '''
        super(RedirectError, self).__init__()
        self.status = '%d %s' % (code, _RESPONSE_STATUSES[code])
        self.location = location

    def __str__(self):
        return self.status

class JsonRpcError(StandardError):
    pass

def badrequest():
    '''
    Send a bad request response.

    >>> raise badrequest()
    Traceback (most recent call last):
      ...
    HttpError: 400 Bad Request
    '''
    return HttpError(400)

def unauthorized():
    '''
    Send an unauthorized response.

    >>> raise unauthorized()
    Traceback (most recent call last):
      ...
    HttpError: 401 Unauthorized
    '''
    return HttpError(401)

def forbidden():
    '''
    Send a forbidden response.

    >>> raise forbidden()
    Traceback (most recent call last):
      ...
    HttpError: 403 Forbidden
    '''
    return HttpError(403)

def notfound():
    '''
    Send a not found response.

    >>> raise notfound()
    Traceback (most recent call last):
      ...
    HttpError: 404 Not Found
    '''
    return HttpError(404)

def conflict():
    '''
    Send a conflict response.

    >>> raise conflict()
    Traceback (most recent call last):
      ...
    HttpError: 409 Conflict
    '''
    return HttpError(409)

def internalerror():
    '''
    Send an internal error response.

    >>> raise internalerror()
    Traceback (most recent call last):
      ...
    HttpError: 500 Internal Server Error
    '''
    return HttpError(500)

def _redirect(code, location):
    return RedirectError(code, location)

def redirect(location):
    '''
    Do permanent redirect.

    >>> raise redirect('http://www.itranswarp.com/')
    Traceback (most recent call last):
      ...
    RedirectError: 301 Moved Permanently
    '''
    return _redirect(301, location)

def found(location):
    '''
    Do temporary redirect.

    >>> raise found('http://www.itranswarp.com/')
    Traceback (most recent call last):
      ...
    RedirectError: 302 Found
    '''
    return _redirect(302, location)

def seeother(location):
    '''
    Do temporary redirect.

    >>> raise seeother('http://www.itranswarp.com/')
    Traceback (most recent call last):
      ...
    RedirectError: 303 See Other
    >>> e = seeother('http://www.itranswarp.com/seeother?r=123')
    >>> e.location
    'http://www.itranswarp.com/seeother?r=123'
    '''
    return _redirect(303, location)

def _safe_str(s):
    if isinstance(s, str):
        return s
    if isinstance(s, unicode):
        return s.encode('utf-8')
    return str(s)

def _unicode(s, encoding='utf-8'):
    return s.decode('utf-8')

def _quote(s, encoding='utf-8'):
    '''
    Url quote as str.

    >>> _quote('http://example/test?a=1+')
    'http%3A//example/test%3Fa%3D1%2B'
    >>> _quote(u'hello world!')
    'hello%20world%21'
    '''
    if isinstance(s, unicode):
        s = s.encode(encoding)
    return urllib.quote(s)

def _unquote(s, encoding='utf-8'):
    '''
    Url unquote as unicode.

    >>> _unquote('http%3A//example/test%3Fa%3D1+')
    u'http://example/test?a=1+'
    '''
    return urllib.unquote(s).decode(encoding)

def _unquote_plus(s, encoding='utf-8'):
    '''
    Url unquote_plus as unicode.

    >>> _unquote_plus('http%3A//example/test%3Fa%3D1+')
    u'http://example/test?a=1 '
    '''
    return urllib.unquote_plus(s).decode(encoding)

def _log(s):
    logging.info(s)

def _json2str(s):
    if s.startswith(r'"') and s.endswith(r'"'):
        return _json_loads(s, expected=unicode).decode('utf-8')
    return s

def _json2unicode(s):
    if s.startswith(r'"') and s.endswith(r'"'):
        return _json_loads(s, expected=unicode)
    return s.decode('utf-8')

def _json2bool(s):
    if s=='true':
        return True
    if s=='false':
        return False
    raise ValueError('Cannot decode JSON to bool.')

_JSON_CONVERTERS = {
    'bool': _json2bool,
    'int': int,
    'long': int,
    'float': float,
    'str': _json2str,
    'unicode': _json2unicode,
    'object': functools.partial(_json_loads, expected=(dict, list, tuple, types.NoneType)),
    'dict': functools.partial(_json_loads, expected=(dict, types.NoneType)),
    'list': functools.partial(_json_loads, expected=(list, tuple, types.NoneType)),
}

def jsonresult(func):
    '''
    Autoconvert result to json str.

    >>> @jsonresult
    ... def hello(name):
    ...     return dict(name=name)
    >>> ctx.response = Response()
    >>> hello('Bob')
    '{"name": "Bob"}'
    >>> ctx.response.header('CONTENT-TYPE')
    'application/json; charset=utf-8'
    >>> hello(None)
    '{"name": null}'
    '''
    @functools.wraps(func)
    def _wrapper(*args, **kw):
        r = func(*args, **kw)
        ctx.response.content_type = 'application/json; charset=utf-8'
        return _json_dumps(r)
    return _wrapper

def jsonrpc(*type_args):
    '''
    A json rpc wrapper that convert all args and return value into json objects. 
    The function decorated by @jsonrpc can only be called by keyword args.

    >>> @jsonrpc(int, unicode, dict)
    ... def show(id, name, job):
    ...     return (id, name, [job.title, job.salary])
    >>> from StringIO import StringIO
    >>> ctx.request = Request({'REQUEST_METHOD':'POST', 'wsgi.input':StringIO('id=123&name=%22Michael%22&job=%7B%22title%22%3A%22Architect%22%2C+%22salary%22%3A+875000%7D')})
    >>> ctx.response = Response()
    >>> show()
    '[123, "Michael", ["Architect", 875000]]'
    >>> ctx.response.header('CONTENT-TYPE')
    'application/json; charset=utf-8'
    >>> ctx.request = Request({'REQUEST_METHOD':'POST', 'wsgi.input':StringIO('id=123&name=Michael&job=true')})
    >>> show() # expected dict args but pass list args!
    Traceback (most recent call last):
      ...
    TypeError: Object loaded from json is not expected type: (<type 'dict'>, <type 'NoneType'>)
    >>> @jsonrpc(int) # args are not match the decorating function!
    ... def bad(id, name):
    ...     pass
    >>> bad()
    Traceback (most recent call last):
      ...
    JsonRpcError: @jsonrpc args and function args are not match.
    >>> @jsonrpc(xrange) # not supported json types: xrange!
    ... def badrange(range):
    ...     pass
    Traceback (most recent call last):
      ...
    JsonRpcError: Not supported type: xrange
    '''
    _f_toname = lambda s: s.__name__ if isinstance(s, type) else str(s)
    t_args = [_f_toname(ta) for ta in type_args]
    for t in t_args:
        if not t in _JSON_CONVERTERS:
            raise JsonRpcError('Not supported type: %s' % t)

    def _decorator(func):
        def _defaults_dict(f_args, f_defaults):
            if f_defaults:
                num = len(f_args) - len(f_defaults)
                r = {}
                for k, v in zip(f_args[num:], f_defaults):
                    r[k] = v
                return r
            return {}

        def _convert_json(type_arg, str_arg):
            return _JSON_CONVERTERS[type_arg](str_arg)

        @functools.wraps(func)
        def _wrapper(**anykw):
            if len(_wrapper.__args__)!=len(t_args):
                raise JsonRpcError('@jsonrpc args and function args are not match.')
            kw = ctx.request.input()
            vargs = []
            count = _wrapper.__required_args__
            for arg, targ in zip(_wrapper.__args__, t_args):
                if count > 0:
                    if arg in kw:
                        vargs.append(_convert_json(targ, kw[arg]))
                    else:
                        raise JsonRpcError('Not enough args.')
                else:
                    if arg in kw:
                        vargs.append(_convert_json(targ, kw[arg]))
                    else:
                        vargs.append(_wrapper.__defaults_dict__[arg])
                count = count - 1

            _log('call jsonrpc.wrapper args: %s' % str(vargs))
            r = func(*vargs)
            jr = _json_dumps(r)
            ctx.response.set_header('CONTENT-TYPE', 'application/json; charset=utf-8')
            return jr
        fargs, fvarargs, fkw, fdefaults = inspect.getargspec(func)
        if fvarargs:
            raise JsonRpcError('function decorated with @jsonrpc cannot have varargs.')
        if fkw:
            raise JsonRpcError('function decorated with @jsonrpc cannot have keyword args.')
        _wrapper.__args__ = fargs
        if fdefaults:
            _wrapper.__required_args__ = len(fargs) - len(fdefaults)
            _wrapper.__defaults_dict__ = _defaults_dict(fargs, fdefaults)
        else:
            _wrapper.__required_args__ = len(fargs)
            _wrapper.__defaults_dict__ = {}
        return _wrapper
    return _decorator

def _route_decorator_maker(path, allow_get, allow_post):
    '''
    A decorator that has args:

    @route('/')
    def index():
        pass
    '''
    def _decorator(func):
        @functools.wraps(func)
        def _wrapper(*args, **kw):
            _log('call route.wrapper: %s, %s' % (str(args), str(kw)))
            return func(*args, **kw)
        _wrapper.__web_route__ = path
        _wrapper.__web_get__ = allow_get
        _wrapper.__web_post__ = allow_post
        return _wrapper
    return _decorator

def _route_decorator(func, allow_get, allow_post):
    '''
    A decorator that does not have args:

    @route
    def foo():
        pass
    '''
    @functools.wraps(func)
    def _wrapper(*args, **kw):
        _log('call route.wrapper: %s, %s' % (str(args), str(kw)))
        return func(*args, **kw)
    _wrapper.__web_route__ = '/%s/%s' % (func.__module__.replace('.', '/'), func.__name__)
    _wrapper.__web_get__ = allow_get
    _wrapper.__web_post__ = allow_post
    return _wrapper

def route(func_or_path=None):
    '''
    @route decorator for both GET and POST.
    '''
    if callable(func_or_path):
        return _route_decorator(func_or_path, True, True)
    else:
        return _route_decorator_maker(func_or_path, True, True)

def get(func_or_path=None):
    '''
    @get decorator for GET only.
    '''
    if callable(func_or_path):
        return _route_decorator(func_or_path, True, False)
    else:
        return _route_decorator_maker(func_or_path, True, False)

def post(func_or_path=None):
    '''
    @post decorator for POST only.
    '''
    if callable(func_or_path):
        return _route_decorator(func_or_path, False, True)
    else:
        return _route_decorator_maker(func_or_path, False, True)

_re_route = re.compile(r'\<(\w*\:?\w*)\>')
_convert = {'int' : int, \
            'long' : long, \
            'float' : float, \
            'bool' : bool, \
            'str' : str, \
            'unicode' : lambda s: s.decode('utf-8'), \
            '' : lambda s: s.decode('utf-8') }

class Route(object):

    def execute(self, *args, **kw):
        return self.func(*args, **kw)

    def _parse_var(self, var):
        if not var:
            raise BadRouteError('var name required')
        var_type = ''
        var_name = var
        pos = var.find(':')
        if pos!=(-1):
            var_type = var[:pos]
            var_name = var[pos+1:]
            if not var_type:
                raise BadRouteError('var type required before :')
            ch = var_type[0]
            if ch>='0' and ch<='9':
                raise BadRouteError('invalid var type')
        if not var_name:
            raise BadRouteError('var name required')
        ch = var_name[0]
        if ch>='0' and ch<='9':
            raise BadRouteError('invalid var name')
        return (var_type, var_name)

    def _parse_static(self, s):
        L = []
        for ch in s:
            if ch>='0' and ch<='9':
                L.append(ch)
            elif ch>='A' and ch<='Z':
                L.append(ch)
            elif ch>='a' and ch<='z':
                L.append(ch)
            else:
                L.append(r'\%s' % ch)
        return ''.join(L)

    def __init__(self, path, func):
        rl = ['^']
        vl = []
        var = False
        for s in _re_route.split(path):
            if var:
                var_type, var_name = self._parse_var(s)
                vl.append(var_type)
                rl.append(r'(?P<%s>.+)' % var_name if var_type=='path' else r'(?P<%s>[^\/]+)' % var_name)
            else:
                rl.append(self._parse_static(s))
            var = not var
        rl.append('$')

        self.str_route = path
        self.re_route = ''.join(rl)
        self.route = re.compile(self.re_route)
        self.types = vl
        self.static = len(vl)==0
        self.func = func

    def __str__(self):
        return '(path=%s, compiled=%s, types=%s)' % (self.str_route, self.re_route, str(self.types))

    __repr__ = __str__

def _static_file_generator(fpath):
    BLOCK_SIZE = 8192
    with open(fpath, 'rb') as f:
        block = f.read(BLOCK_SIZE)
        while block:
            yield block
            block = f.read(BLOCK_SIZE)

def static_file_handler(*args, **kw):
    pathinfo = ctx.request.path_info
    if not pathinfo.startswith('/'):
        raise HttpError('403')
    fpath = os.path.join(ctx.document_root, pathinfo[1:])
    _log('static file: %s' % fpath)
    if not os.path.isfile(fpath):
        raise HttpError(404)
    fext = os.path.splitext(fpath)[1]
    ctx.response.content_type = mimetypes.types_map.get(fext.lower(), 'application/octet-stream')
    ctx.response.content_length = os.path.getsize(fpath)
    return _static_file_generator(fpath)

def favicon_handler():
    return static_file_handler('/favicon.ico')

class MultipartFile(object):
    '''
    Multipart file storage get from request input.

    f = ctx.request['file']
    f.filename # 'test.png'
    f.file # file-like object
    '''
    def __init__(self, storage):
        self.filename = _unicode(storage.filename)
        self.file = storage.file

class _InputDict(dict):
    '''
    Simple dict but support access as x.y style and list value.

    >>> d1 = _InputDict(x=u'100', y=u'200')
    >>> d1.x
    u'100'
    >>> d1['y']
    u'200'
    >>> d1['empty']
    Traceback (most recent call last):
        ...
    KeyError: 'empty'
    >>> d1.empty
    Traceback (most recent call last):
        ...
    KeyError: 'empty'
    >>> d2 = _InputDict(a=u'1', b=[u'X', u'Y', u'Z'])
    >>> d2.b
    u'X'
    >>> d2.gets('b')
    [u'X', u'Y', u'Z']
    >>> d2.gets('a')
    [u'1']
    >>> d2.gets('empty')
    Traceback (most recent call last):
        ...
    KeyError: 'empty'
    '''
    def __init__(self, **kw):
        d = {}
        ld = {}
        for k, v in kw.iteritems():
            if isinstance(v, list):
                d[k] = v[0]
                ld[k] = v
            else:
                d[k] = v
        super(_InputDict, self).__init__(**d)
        self._multidict = ld

    def __getattr__(self, key):
        return self[key]

    def gets(self, key):
        if key in self._multidict:
            return self._multidict[key][:]
        return [self[key]]

class Request(object):
    '''
    Request object for obtaining all http request information.
    '''

    def __init__(self, environ):
        self._environ = environ
        self._cache = {}

    def _fromcache(self, key, func, *args, **kw):
        r = self._cache.get(key)
        if r is None:
            r = func(*args, **kw)
        self._cache[key] = r
        return r

    def _get_raw_input(self):
        ' return raw input as dict with key=field name, value=list or MultipartFile. '
        def _do_get_raw_input():
            def _convert_item(item):
                if isinstance(item, list):
                    return [_unicode(i.value) for i in item]
                if item.filename:
                    # convert to file:
                    return MultipartFile(item)
                # single value:
                return _unicode(item.value)
            fs = cgi.FieldStorage(fp=self._environ['wsgi.input'], environ=self._environ, keep_blank_values=True)
            form = dict()
            for key in fs:
                form[key] = _convert_item(fs[key])
            return form
        return self._fromcache('CACHED_INPUT', _do_get_raw_input)

    def input(self, **kw):
        '''
        Get input from request.

        >>> from StringIO import StringIO
        >>> r = Request({'REQUEST_METHOD':'POST', 'wsgi.input':StringIO('a=1&b=M%20M&c=ABC&c=XYZ&e=')})
        >>> i = r.input(x=2008)
        >>> i.a
        u'1'
        >>> i.b
        u'M M'
        >>> i.c
        u'ABC'
        >>> i.x
        2008
        >>> i.gets('c')
        [u'ABC', u'XYZ']
        >>> i.get('d', u'100')
        u'100'
        >>> i.x
        2008
        '''
        copy = _InputDict(**self._get_raw_input())
        if kw:
            for k, v in kw.iteritems():
                if not k in copy:
                    copy[k] = v
        return copy

    def __getitem__(self, key):
        '''
        Get input parameter value. If the specified key has multiple value, the first one is returned.
        If the specified key is not exist, then raise KeyError.

        >>> from StringIO import StringIO
        >>> r = Request({'REQUEST_METHOD':'POST', 'wsgi.input':StringIO('a=1&b=M%20M&c=ABC&c=XYZ&e=')})
        >>> r['a']
        u'1'
        >>> r['c']
        u'ABC'
        >>> r['empty']
        Traceback (most recent call last):
            ...
        KeyError: 'empty'
        >>> b = '----WebKitFormBoundaryQQ3J8kPsjFpTmqNz'
        >>> pl = ['--%s' % b, 'Content-Disposition: form-data; name=\\"name\\"\\n', 'Scofield', '--%s' % b, 'Content-Disposition: form-data; name=\\"name\\"\\n', 'Lincoln', '--%s' % b, 'Content-Disposition: form-data; name=\\"file\\"; filename=\\"test.txt\\"', 'Content-Type: text/plain\\n', 'just a test', '--%s' % b, 'Content-Disposition: form-data; name=\\"id\\"\\n', '4008009001', '--%s--' % b, '']
        >>> payload = '\\n'.join(pl)
        >>> r = Request({'REQUEST_METHOD':'POST', 'CONTENT_LENGTH':str(len(payload)), 'CONTENT_TYPE':'multipart/form-data; boundary=%s' % b, 'wsgi.input':StringIO(payload)})
        >>> r.get('name')
        u'Scofield'
        >>> r.gets('name')
        [u'Scofield', u'Lincoln']
        >>> f = r.get('file')
        >>> f.filename
        u'test.txt'
        >>> f.file.read()
        'just a test'
        '''
        r = self._get_raw_input()[key]
        if isinstance(r, list):
            return r[0]
        return r

    def get(self, key, default=None):
        '''
        The same as request[key], but return default value if key is not found.

        >>> from StringIO import StringIO
        >>> r = Request({'REQUEST_METHOD':'POST', 'wsgi.input':StringIO('a=1&b=M%20M&c=ABC&c=XYZ&e=')})
        >>> r.get('a')
        u'1'
        >>> r.get('empty')
        >>> r.get('empty', 'DEFAULT')
        'DEFAULT'
        '''
        r = self._get_raw_input().get(key, default)
        if isinstance(r, list):
            return r[0]
        return r

    def gets(self, key):
        '''
        Get multiple values for specified key.

        >>> from StringIO import StringIO
        >>> r = Request({'REQUEST_METHOD':'POST', 'wsgi.input':StringIO('a=1&b=M%20M&c=ABC&c=XYZ&e=')})
        >>> r.gets('a')
        [u'1']
        >>> r.gets('c')
        [u'ABC', u'XYZ']
        >>> r.gets('empty')
        Traceback (most recent call last):
            ...
        KeyError: 'empty'
        '''
        r = self._get_raw_input()[key]
        if isinstance(r, list):
            return r[:]
        return [r]

    def __iter__(self):
        '''
        Get all input parameter names.
        >>> from StringIO import StringIO
        >>> r = Request({'REQUEST_METHOD':'POST', 'wsgi.input':StringIO('a=1&b=M%20M&c=ABC&c=XYZ&e=')})
        >>> [key for key in r]
        ['a', 'c', 'b', 'e']
        '''
        return self._get_raw_input().__iter__()

    @property
    def remote_addr(self):
        '''
        Get remote addr.

        >>> r = Request({'REMOTE_ADDR': '192.168.0.100'})
        >>> r.remote_addr
        '192.168.0.100'
        '''
        return self._environ.get('REMOTE_ADDR', '0.0.0.0')

    @property
    def document_root(self):
        '''
        Get raw document_root as str. Return '' if no document_root.

        >>> r = Request({'DOCUMENT_ROOT': '/srv/path/to/doc'})
        >>> r.document_root
        '/srv/path/to/doc'
        '''
        return self._environ.get('DOCUMENT_ROOT', '')

    @property
    def query_string(self):
        '''
        Get raw query string as str. Return '' if no query string.

        >>> r = Request({'QUERY_STRING': 'a=1&c=2'})
        >>> r.query_string
        'a=1&c=2'
        >>> r = Request({})
        >>> r.query_string
        ''
        '''
        return self._environ.get('QUERY_STRING', '')

    @property
    def environ(self):
        '''
        Get raw environ as dict, both key, value are str.

        >>> r = Request({'REQUEST_METHOD': 'GET', 'wsgi.url_scheme':'http'})
        >>> r.environ.get('REQUEST_METHOD')
        'GET'
        >>> r.environ.get('wsgi.url_scheme')
        'http'
        >>> r.environ.get('SERVER_NAME')
        >>> r.environ.get('SERVER_NAME', 'unamed')
        'unamed'
        '''
        return self._environ

    @property
    def request_method(self):
        '''
        Get request method. The valid returned values are u'GET', u'POST', u'HEAD'.

        >>> r = Request({'REQUEST_METHOD': 'GET'})
        >>> r.request_method
        u'GET'
        >>> r = Request({'REQUEST_METHOD': 'POST'})
        >>> r.request_method
        u'POST'
        '''
        return unicode(self._environ.get('REQUEST_METHOD', 'GET'))

    @property
    def path_info(self):
        '''
        Get request path as unicode.

        >>> r = Request({'PATH_INFO': '/test/a%20b.html'})
        >>> r.path_info
        '/test/a b.html'
        '''
        return urllib.unquote(self._environ.get('PATH_INFO', ''))

    @property
    def host(self):
        '''
        Get request host as unicode.

        >>> r = Request({'HTTP_HOST': 'localhost:8080'})
        >>> r.host
        u'localhost:8080'
        '''
        return unicode(self._environ.get('HTTP_HOST', ''))

    @property
    def headers(self):
        '''
        Get all HTTP headers with kv both unicode. The header names are 'XXX-XXX' uppercase.

        >>> r = Request({'HTTP_USER_AGENT': 'Mozilla/5.0', 'HTTP_ACCEPT': 'text/html'})
        >>> L = r.headers.items()
        >>> L.sort()
        >>> L
        [(u'ACCEPT', u'text/html'), (u'USER-AGENT', u'Mozilla/5.0')]
        '''
        def _headers():
            hdrs = {}
            for k, v in self._environ.iteritems():
                if k.startswith('HTTP_'):
                    # convert 'HTTP_ACCEPT_ENCODING' to 'ACCEPT-ENCODING'
                    hdrs[unicode(k[5:].replace('_', '-').upper())] = v.decode('utf-8')
            return hdrs
        return self._fromcache('CACHED_HTTP_HEADERS', _headers)

    def header(self, header, default=None):
        '''
        Get header from request as unicode, return None if not exist, or default if specified. 
        The header name is case-insensitive such as 'USER-AGENT' or u'content-type'.

        >>> r = Request({'HTTP_USER_AGENT': 'Mozilla/5.0', 'HTTP_ACCEPT': 'text/html'})
        >>> r.header('User-Agent')
        u'Mozilla/5.0'
        >>> r.header('USER-AGENT')
        u'Mozilla/5.0'
        >>> r.header(u'Accept')
        u'text/html'
        >>> r.header(u'Test')
        >>> r.header(u'Test', u'DEFAULT')
        u'DEFAULT'
        '''
        return self.headers.get(header.upper(), default)

    @property
    def cookies(self):
        '''
        Return all cookies as dict. Both the cookie name and values are unicode.

        >>> r = Request({'HTTP_COOKIE':'A=123; url=http%3A%2F%2Fwww.example.com%2F'})
        >>> r.cookies[u'A']
        u'123'
        >>> r.cookies[u'url']
        u'http://www.example.com/'
        '''
        def _cookies():
            cookies = self._environ.get('HTTP_COOKIE')
            cs = {}
            if cookies:
                for c in cookies.split(';'):
                    pos = c.find('=')
                    if pos>0:
                        cs[unicode(c[:pos].strip())] = _unquote(c[pos+1:])
            return cs
        return self._fromcache('CACHED_COOKIES', _cookies)

    def cookie(self, name, default=None):
        '''
        Return specified cookie value as unicode. Default to None if cookie not exists.

        >>> r = Request({'HTTP_COOKIE':'A=123; url=http%3A%2F%2Fwww.example.com%2F'})
        >>> r.cookie(u'A')
        u'123'
        >>> r.cookie(u'url')
        u'http://www.example.com/'
        >>> r.cookie(u'test')
        >>> r.cookie(u'test', u'DEFAULT')
        u'DEFAULT'
        '''
        return self.cookies.get(name, default)

_TIMEDELTA_ZERO = datetime.timedelta(0)

_RE_TZ = re.compile('^([\+\-])([0-9]{1,2})\:([0-9]{1,2})$')

class UTC(datetime.tzinfo):
    '''
    A UTC tzinfo object. 

    >>> tz0 = UTC('+00:00')
    >>> tz0.tzname(None)
    'UTC+00:00'
    >>> tz8 = UTC('+8:00')
    >>> tz8.tzname(None)
    'UTC+8:00'
    >>> tz7 = UTC('+7:30')
    >>> tz7.tzname(None)
    'UTC+7:30'
    >>> tz5 = UTC('-05:30')
    >>> tz5.tzname(None)
    'UTC-05:30'
    >>> from datetime import datetime
    >>> u = datetime.utcnow().replace(tzinfo=tz0)
    >>> l1 = u.astimezone(tz8)
    >>> l2 = u.replace(tzinfo=tz8)
    >>> d1 = u - l1
    >>> d2 = u - l2
    >>> d1.seconds
    0
    >>> d2.seconds
    28800
    '''

    def __init__(self, utc):
        utc = str(utc.strip().upper())
        mt = _RE_TZ.match(utc)
        if mt:
            minus = mt.group(1)=='-'
            h = int(mt.group(2))
            m = int(mt.group(3))
            if minus:
                h, m = (-h), (-m)
            self._utcoffset = datetime.timedelta(hours=h, minutes=m)
            self._tzname = 'UTC%s' % utc
        else:
            raise ValueError('bad utc time zone')

    def utcoffset(self, dt):
        return self._utcoffset

    def dst(self, dt):
        return _TIMEDELTA_ZERO

    def tzname(self, dt):
        return self._tzname

    def __str__(self):
        return 'UTC tzinfo object (%s)' % self._tzname

    __repr__ = __str__

UTC_0 = UTC('+00:00')

class Response(object):

    def __init__(self):
        self._status = '200 OK'
        self._headers = {'CONTENT-TYPE': 'text/html; charset=utf-8'}
        self._output = []
        self._cookies = {}

    @property
    def headers(self):
        '''
        Return response headers as [(key1, value1), (key2, value2)...] including cookies.

        >>> r = Response()
        >>> r.headers
        [('Content-Type', 'text/html; charset=utf-8'), ('X-Powered-By', 'iTranswarp/1.0')]
        >>> r.set_cookie('s1', 'ok', 3600)
        >>> r.headers
        [('Content-Type', 'text/html; charset=utf-8'), ('Set-Cookie', 's1=ok; Max-Age=3600; Path=/'), ('X-Powered-By', 'iTranswarp/1.0')]
        '''
        L = [(_RESPONSE_HEADER_DICT.get(k, k), v) for k, v in self._headers.iteritems()]
        if self._cookies:
            for v in self._cookies.itervalues():
                L.append(('Set-Cookie', v))
        L.append(_HEADER_X_POWERED_BY)
        return L

    def header(self, name):
        '''
        Get header by name, case-insensitive.

        >>> r = Response()
        >>> r.header('content-type')
        'text/html; charset=utf-8'
        >>> r.header('CONTENT-type')
        'text/html; charset=utf-8'
        >>> r.header('X-Powered-By')
        '''
        key = name.upper()
        if not key in _RESPONSE_HEADER_DICT:
            key = name
        return self._headers.get(key)

    def unset_header(self, name):
        '''
        Unset header by name and value.

        >>> r = Response()
        >>> r.header('content-type')
        'text/html; charset=utf-8'
        >>> r.unset_header('CONTENT-type')
        >>> r.header('content-type')
        >>> r.unset_header('content-TYPE')
        '''
        key = name.upper()
        if not key in _RESPONSE_HEADER_DICT:
            key = name
        if key in self._headers:
            del self._headers[key]

    def set_header(self, name, value):
        '''
        Set header by name and value.

        >>> r = Response()
        >>> r.header('content-type')
        'text/html; charset=utf-8'
        >>> r.set_header('CONTENT-type', 'image/png')
        >>> r.header('content-TYPE')
        'image/png'
        '''
        key = name.upper()
        if not key in _RESPONSE_HEADER_DICT:
            key = name
        self._headers[key] = _safe_str(value)

    @property
    def content_type(self):
        '''
        Get content type from response. This is a shortcut for header('Content-Type').

        >>> r = Response()
        >>> r.content_type
        'text/html; charset=utf-8'
        >>> r.content_type = 'application/json'
        >>> r.content_type
        'application/json'
        '''
        return self.header('CONTENT-TYPE')

    @content_type.setter
    def content_type(self, value):
        '''
        Set content type for response. This is a shortcut for set_header('Content-Type', value).
        '''
        self.set_header('CONTENT-TYPE', value)

    @property
    def content_length(self):
        '''
        Get content length. Return None if not set.

        >>> r = Response()
        >>> r.content_length
        >>> r.content_length = 100
        >>> r.content_length
        '100'
        '''
        return self.header('CONTENT-LENGTH')

    @content_length.setter
    def content_length(self, value):
        '''
        Set content length, the value can be int or str.

        >>> r = Response()
        >>> r.content_length = '1024'
        >>> r.content_length
        '1024'
        >>> r.content_length = 1024 * 8
        >>> r.content_length
        '8192'
        '''
        self.set_header('CONTENT-LENGTH', str(value))

    def delete_cookie(self, name):
        '''
        Delete a cookie immediately.

        Args:
          name: the cookie name.
        '''
        self.set_cookie(name, '__deleted__', expires=time.time() - 31536000)

    def set_cookie(self, name, value, max_age=None, expires=None, path='/', domain=None, secure=False, http_only=False):
        '''
        Set a cookie.

        Args:
          name: the cookie name.
          value: the cookie value.
          max_age: optional, seconds of cookie's max age.
          expires: optional, unix timestamp, datetime or date object that indicate an absolute time of the 
                   expiration time of cookie. Note that if expires specified, the max_age will be ignored.
          path: the cookie path, default to '/'.
          domain: the cookie domain, default to None.
          secure: if the cookie secure, default to False.
          http_only: if the cookie is for http only, default to False.

        >>> r = Response()
        >>> r.set_cookie('company', 'Abc, Inc.', max_age=3600)
        >>> r._cookies
        {'company': 'company=Abc%2C%20Inc.; Max-Age=3600; Path=/'}
        >>> r.set_cookie('company', r'Example="Limited"', expires=1342274794.123, path='/sub/')
        >>> r._cookies
        {'company': 'company=Example%3D%22Limited%22; Expires=Sat, 14-Jul-2012 14:06:34 GMT; Path=/sub/'}
        >>> dt = datetime.datetime(2012, 7, 14, 22, 6, 34, tzinfo=UTC('+8:00'))
        >>> r.set_cookie('company', 'Expires', expires=dt)
        >>> r._cookies
        {'company': 'company=Expires; Expires=Sat, 14-Jul-2012 14:06:34 GMT; Path=/'}
        '''
        L = ['%s=%s' % (_quote(name), _quote(value))]
        if expires is not None:
            if isinstance(expires, (float, int, long)):
                L.append('Expires=%s' % datetime.datetime.fromtimestamp(expires, UTC_0).strftime('%a, %d-%b-%Y %H:%M:%S GMT'))
            if isinstance(expires, (datetime.date, datetime.datetime)):
                L.append('Expires=%s' % expires.astimezone(UTC_0).strftime('%a, %d-%b-%Y %H:%M:%S GMT'))
        elif isinstance(max_age, (int, long)):
            L.append('Max-Age=%d' % max_age)
        L.append('Path=%s' % path)
        if domain:
            L.append('Domain=%s' % domain)
        if secure:
            L.append('Secure')
        if http_only:
            L.append('HttpOnly')
        self._cookies[name] = '; '.join(L)

    def unset_cookie(self, name):
        '''
        Unset a cookie.

        >>> r = Response()
        >>> r.set_cookie('company', 'Abc, Inc.', max_age=3600)
        >>> r._cookies
        {'company': 'company=Abc%2C%20Inc.; Max-Age=3600; Path=/'}
        >>> r.unset_cookie('company')
        >>> r._cookies
        {}
        '''
        if name in self._cookies:
            del self._cookies[name]

    @property
    def status_code(self):
        '''
        Get response status code as int.

        >>> r = Response()
        >>> r.status_code
        200
        >>> r.status = 404
        >>> r.status_code
        404
        >>> r.status = '500 Internal Error'
        >>> r.status_code
        500
        '''
        return int(self._status[:3])

    @property
    def status(self):
        '''
        Get response status. Default to '200 OK'.

        >>> r = Response()
        >>> r.status
        '200 OK'
        >>> r.status = 404
        >>> r.status
        '404 Not Found'
        >>> r.status = '500 SERVER ERR'
        >>> r.status
        '500 SERVER ERR'
        '''
        return self._status

    @status.setter
    def status(self, value):
        '''
        Set response status as int or str.

        >>> r = Response()
        >>> r.status = 404
        >>> r.status
        '404 Not Found'
        >>> r.status = '500 ERR'
        >>> r.status
        '500 ERR'
        >>> r.status = u'403 Denied'
        >>> r.status
        '403 Denied'
        >>> r.status = 99
        Traceback (most recent call last):
          ...
        ValueError: Bad response code: 99
        >>> r.status = 'ok'
        Traceback (most recent call last):
          ...
        ValueError: Bad response code: ok
        >>> r.status = [1, 2, 3]
        Traceback (most recent call last):
          ...
        TypeError: Bad type of response code.
        '''
        if isinstance(value, (int, long)):
            if value>=100 and value<=999:
                st = _RESPONSE_STATUSES.get(value, '')
                if st:
                    self._status = '%d %s' % (value, st)
                else:
                    self._status = str(value)
            else:
                raise ValueError('Bad response code: %d' % value)
        elif isinstance(value, unicode):
            value = value.encode('utf-8')
        elif isinstance(value, str):
            if _RE_RESPONSE_STATUS.match(value):
                self._status = value
            else:
                raise ValueError('Bad response code: %s' % value)
        else:
            raise TypeError('Bad type of response code.')

    @property
    def body(self):
        '''
        Get response body as list.
        '''
        return self._output

    def write(self, value):
        s = ''
        if isinstance(value, str):
            s = value
        elif isinstance(value, unicode):
            s = value.encode('utf-8')
        elif value is not None:
            s = str(value)
        if s:
            self._output.append(s)

    def reset(self):
        self._output[:] = []

class Page(object):
    '''
    Page object that can be used for calculate pagination.
    '''

    def __init__(self, page_index, page_size, total):
        '''
        Init Page object with:
            page_index: starts from 1.
            page_size: page size, at least 1.
            total: total items, non-negative value.
        '''
        if page_index < 1:
            raise ValueError('page_index must be greater than 0')
        if page_size < 1:
            raise ValueError('page_size must be greater than 0')
        if total < 0:
            raise ValueError('total must be non-negative')
        self._total = total
        self._index = page_index
        self._size = page_size
        if total > 0:
            page_count = total // page_size + (0 if (total % page_size)==0 else 1)
            if page_index > page_count:
                raise ValueError('page_index is out of range [1..%s]' % page_count)
            offset = page_size * (page_index - 1)
            limit = page_size if page_index < page_count else total - (page_index - 1) * page_size
            self._offset = offset
            self._limit = limit
            self._pages = page_count
        else:
            self._offset = 0
            self._limit = 0
            self._pages = 0

    @property
    def offset(self):
        '''
        The offset of first item of current page.

        >>> Page(1, 10, 99).offset
        0
        >>> Page(2, 10, 99).offset
        10
        >>> Page(3, 15, 99).offset
        30
        >>> Page(1, 10, 0).offset
        0
        '''
        return self._offset

    @property
    def limit(self):
        '''
        The number of items of current page.

        >>> Page(1, 10, 99).limit
        10
        >>> Page(2, 10, 99).limit
        10
        >>> Page(10, 10, 91).limit
        1
        >>> Page(10, 10, 99).limit
        9
        >>> Page(10, 10, 100).limit
        10
        >>> Page(1, 10, 0).limit
        0
        '''
        return self._limit

    @property
    def index(self):
        '''
        The current page index.

        >>> Page(1, 10, 99).index
        1
        >>> Page(2, 10, 99).index
        2
        >>> Page(10, 10, 99).index
        10
        >>> Page(11, 10, 99).index
        Traceback (most recent call last):
            ...
        ValueError: page_index is out of range [1..10]
        '''
        return self._index

    @property
    def size(self):
        '''
        The page size.

        >>> Page(1, 5, 100).size
        5
        >>> Page(1, 10, 100).size
        10
        >>> Page(1, 0, 100).size
        Traceback (most recent call last):
            ...
        ValueError: page_size must be greater than 0
        '''
        return self._size

    @property
    def pages(self):
        '''
        Get how many pages.

        >>> Page(1, 10, 0).pages
        0
        >>> Page(1, 10, 1).pages
        1
        >>> Page(1, 10, 9).pages
        1
        >>> Page(1, 10, 10).pages
        1
        >>> Page(1, 10, 11).pages
        2
        >>> Page(1, 10, 19).pages
        2
        >>> Page(1, 10, 20).pages
        2
        >>> Page(1, 10, 21).pages
        3
        >>> Page(1, 10, 100).pages
        10
        >>> Page(1, 10, 101).pages
        11
        '''
        return self._pages

    @property
    def empty(self):
        '''
        Test if should show "no items to display".

        >>> Page(1, 10, 0).empty
        True
        >>> Page(1, 10, 1).empty
        False
        '''
        return self._pages==0

    @property
    def total(self):
        '''
        Get total items.

        >>> Page(1, 10, 0).total
        0
        >>> Page(1, 10, 99).total
        99
        '''
        return self._total

    @property
    def previous(self):
        '''
        Get previous page index. 0 if no previous.

        >>> Page(1, 10, 100).previous
        0
        >>> Page(2, 10, 100).previous
        1
        '''
        return (self._index - 1) if self._index > 1 else 0

    @property
    def next(self):
        '''
        Get next page index. 0 if no next.

        >>> Page(1, 10, 100).next
        2
        >>> Page(10, 10, 100).next
        0
        '''
        return (self._index + 1) if self._index < self._pages else 0

    def nearby(self, number=5):
        '''
        Get nearby page indexes as list. For example, current page index is 10, 
        the nearby() returns [5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15].

        >>> Page(1, 10, 1000).nearby()
        [1, 2, 3, 4, 5, 6]
        >>> Page(2, 10, 1000).nearby()
        [1, 2, 3, 4, 5, 6, 7]
        >>> Page(6, 10, 1000).nearby()
        [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]
        >>> Page(7, 10, 1000).nearby()
        [2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]
        >>> Page(95, 10, 1000).nearby()
        [90, 91, 92, 93, 94, 95, 96, 97, 98, 99, 100]
        >>> Page(96, 10, 1000).nearby()
        [91, 92, 93, 94, 95, 96, 97, 98, 99, 100]
        >>> Page(99, 10, 1000).nearby()
        [94, 95, 96, 97, 98, 99, 100]
        >>> Page(100, 10, 1000).nearby()
        [95, 96, 97, 98, 99, 100]
        >>> Page(6, 10, 1000).nearby(3)
        [3, 4, 5, 6, 7, 8, 9]
        >>> Page(6, 10, 1000).nearby(1)
        [5, 6, 7]
        >>> Page(1, 10, 0).nearby()
        []
        '''
        if number < 1:
            raise ValueError('number must be greater than 0.')
        if self._pages==0:
            return []
        lower = self._index - number
        higher = self._index + number
        if lower < 1:
            lower = 1
        if higher > self._pages:
            higher = self._pages
        return range(lower, higher + 1)

class Template(object):

    def __init__(self, template_name, model=None, **kw):
        '''
        Init a template object with template name, model as dict, and additional kw that will append to model.

        >>> t = Template('hello.html', {'title': 'Hello', 'copyright':'@2010'}, copyright='@2012')
        >>> t.model['title']
        'Hello'
        >>> t.model['copyright']
        '@2012'
        '''
        self.template_name = template_name
        self.model = dict()
        if model:
            self.model.update(model)
        self.model.update(kw)
        if '_' in __builtin__.__dict__:
            self.model['_'] = _

def _init_mako(templ_dir, **kw):
    '''
    Render using mako.

    >>> tmpl_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'test')
    >>> func = _init_mako(tmpl_path)
    >>> r = func('mako-test.html', names=['Michael', 'Tracy'])
    >>> r.replace('\\n', '')
    '<p>Hello, Michael.</p><p>Hello, Tracy.</p>'
    '''
    from mako.lookup import TemplateLookup
    lookup = TemplateLookup(directories=[templ_dir], output_encoding='utf-8', **kw)
    def _render(_mako_temp_name_, **model):
        return lookup.get_template(_mako_temp_name_).render(**model)
    return _render

def _init_jinja2(templ_dir, **kw):
    '''
    Render using jinja2.

    >>> tmpl_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'test')
    >>> func = _init_jinja2(tmpl_path)
    >>> r = func('jinja2-test.html', names=['Michael', 'Tracy'])
    >>> r.replace('\\n', '')
    '<p>Hello, Michael.</p><p>Hello, Tracy.</p>'
    '''
    from jinja2 import Environment, FileSystemLoader
    env = Environment(loader=FileSystemLoader(templ_dir, **kw))
    def datetime_filter(value, format='%y-%m-%d %H:%M'):
        if isinstance(value, (float, int, long)):
            value = datetime.datetime.fromtimestamp(value)
        return value.strftime(format)
    def date_filter(value, format='%y-%m-%d'):
        if isinstance(value, (float, int, long)):
            value = datetime.datetime.fromtimestamp(value)
        return value.strftime(format)
    def time_filter(value, format='%H:%M'):
        if isinstance(value, (float, int, long)):
            value = datetime.datetime.fromtimestamp(value)
        return value.strftime(format)
    def jsstr_filter(value):
        if isinstance(value, str):
            value = value.decode('utf-8')
        return value.replace('\"', '\\\"').replace('\'', '\\\'').replace('\n', '\\n').replace('\r', '\\r')
    def ellipsis_filter(value):
        if isinstance(value, basestring):
            if len(value) > 33:
                return '%s...%s' % (value[:20], value[-10:])
        return value
    env.filters['dt'] = datetime_filter
    env.filters['d'] = date_filter
    env.filters['t'] = time_filter
    env.filters['jsstr'] = jsstr_filter
    env.filters['elli'] = ellipsis_filter
    def _render(_jinja2_temp_name_, **model):
        return env.get_template(_jinja2_temp_name_).render(**model).encode('utf-8')
    return _render

def _init_cheetah(templ_dir, **kw):
    '''
    Render using cheetah.

    >>> tmpl_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'test')
    >>> func = _init_cheetah(tmpl_path)
    >>> r = func('cheetah-test.html', names=['Michael', 'Tracy'])
    >>> r.replace('\\n', '')
    '<p>Hello, Michael.</p><p>Hello, Tracy.</p>'
    '''
    from Cheetah.Template import Template
    def _render(_cheetah_temp_name_, **model):
        return str(Template(file=os.path.join(templ_dir, _cheetah_temp_name_), searchList=[model]))
    return _render

def _install_template_engine(name, templ_dir, **kw):
    name = str(name).lower()
    if name=='mako':
        return _init_mako(templ_dir, **kw)
    if name=='jinja2':
        return _init_jinja2(templ_dir, **kw)
    if name=='cheetah':
        return _init_cheetah(templ_dir, **kw)
    raise StandardError('no such template engine: %s' % name)

def _default_error_handler(e, start_response, is_debug):
    if isinstance(e, HttpError):
        logging.info('HttpError: %s' % e.status)
        start_response(e.status, e.headers)
        return ('<html><body><h1>%s</h1></body></html>' % e.status)
    logging.exception('Exception:')
    start_response('500 Internal Server Error', [_HEADER_X_POWERED_BY])
    if is_debug:
        return _debug()
    return ('<html><body><h1>500 Internal Server Error</h1><h3>%s</h3></body></html>' % str(e))

def view(path):
    '''
    A view decorator that render a view by dict.

    >>> @view('test/view.html')
    ... def hello():
    ...     return dict(name='Bob')
    >>> t = hello()
    >>> isinstance(t, Template)
    True
    '''
    def _decorator(func):
        @functools.wraps(func)
        def _wrapper(*args, **kw):
            _log('call @view: %s' % path)
            r = func(*args, **kw)
            if isinstance(r, dict):
                return Template(path, **r)
            return r
        return _wrapper
    return _decorator

def _html_encode(s):
    return s.replace('<', '&lt;').replace('>', '&gt;').replace(' ', '&nbsp;')

def _debug():
    etype, evalue, tb = sys.exc_info()
    while tb.tb_next:
        tb = tb.tb_next
    stack = []
    f = tb.tb_frame
    while f:
        stack.append(f)
        f = f.f_back
    stack.reverse()
    L = [r'''
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8" />
    <title>Debug Info</title>
    <style>
html {
  font-size: 100%;
  -webkit-text-size-adjust: 100%;
      -ms-text-size-adjust: 100%;
}
body {
  margin: 0;
  font-family: Menlo, Monaco, Consolas, "Courier New", monospace;
  font-size: 13px;
  line-height: 18px;
  color: #333;
  background-color: #fff;
}
a {
  color: #0088cc;
  text-decoration: none;
}
a:hover {
  color: #005580;
  text-decoration: underline;
}
h1,
h2,
h3 {
  margin: 0;
  font-family: inherit;
  font-weight: bold;
  color: inherit;
  text-rendering: optimizelegibility;
}
h1 {
  font-size: 30px;
  line-height: 36px;
}
h1 small {
  font-size: 18px;
}
h2 {
  font-size: 24px;
  line-height: 36px;
}
h3 {
  font-size: 18px;
  line-height: 27px;
}
div {
  padding: 0px;
  margin: 0px;
}
div.line {
  border-top: solid 1px #ccc;
  margin: 6px 0px;
}
div.icon {
  background-position: 2px center;
  background-repeat: no-repeat;
  padding-left: 28px;
}
div.open {
  background-image: url(data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAABGdBTUEAAK/INwWK6QAAABl0RVh0U29mdHdhcmUAQWRvYmUgSW1hZ2VSZWFkeXHJZTwAAADpSURBVHjapFNLCoMwEB1LFHHlTtDLpBdx6aGydNsrFPQk3Sm4qisXfpsXTKBYbCQDA2Z48/IyvvG2bSOX8EAghMB3xRjjQRCQTnlWoHmeaRxHk/Jcy/K9KApSiHVdqyzLeJqmVre2bcubpqlActtv4EmS0LIsVgksetCrFKAImVcCPYZgmiaVV0LjmR4SCn3f/yXyfZ/iODaKjQJMdxgGyvP8lKAsS4qi6FuBfgJYX+9z6VrtgQAKEM+HOCWAN4D9OYMwDK0HeJiB019w8YF2Yi2tae1EYPd9MLtwh7e7rru0TGYbXeIjwADyUf86yz+/bQAAAABJRU5ErkJggg==);
}
div.closed {
  background-image: url(data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAABGdBTUEAAK/INwWK6QAAABl0RVh0U29mdHdhcmUAQWRvYmUgSW1hZ2VSZWFkeXHJZTwAAAFESURBVHjapFM7a4RAEF6DL7QRLAT9M16dFMEmXJPSv5PeKoRASCMJpPf+ioWChWCl4DPOxB334iUkODDu7MznvHZGmqaJ7SEZPlEUwZHIsuyrqso4z3cE9X3P2rYlnu+nWX0Iw/DLwTiOied5vuu6f4qa57mfZVkCTuQlgu84DhuGgUBlWWI0IMjGtm2yATZNU59KgB8hTZGapmFBEKAcx/HGzoOhg67rkEWCH4Zxlb/b+V0WAVVVnQG7cY02142yoijMsizKiDKAeuu6Zrd39+SgXVpyHRxJ9/b6xAzDOM+Al4DPNfz+AjzbjQPe8fg5IvDNMcTz42XVwWwA9mIPdF0nIPZDaCLULTZw04Ndr3BpDiRJYu+PD5T2T3NwtUQ4zaOJSs6apjHTNJFBFm2AXfaBduEAs10Uxb+WCTPdu86fAgwA4uoU1viDGFwAAAAASUVORK5CYII=);
}
div.indent {
  padding-left: 26px;
}
div.local {
  background-color: #efefef;
}
div.normal {
  color: #0088cc;
  cursor: pointer;
}
div.hl {
  color: #0088cc;
  cursor: pointer;
  background-color: #efefef;
}
    </style>
    <script type="text/javascript">
function changeClass(ele, fromCls, toCls) {
  ele.className = ele.className.replace(fromCls, toCls);
}
function changeIcon(ele, childId) {
  if (ele.className.indexOf('open')!=(-1)) {
    ele.className = ele.className.replace('open', 'closed');
    document.getElementById(childId).style.display='none';
  }
  else {
    ele.className = ele.className.replace('closed', 'open');
    document.getElementById(childId).style.display='';
  }
}
    </script>
</head>
<body>
    ''', '<div><h3>500 Internal Server Error</h3></div><div class="line"></div><div><div class="indent icon">Traceback (most recent call last):</div></div>']
    n = 0
    for frame in stack:
        n = n + 1
        line1 = r'File "%s", line %s, in %s' % (frame.f_code.co_filename, frame.f_lineno, frame.f_code.co_name)
        line2 = linecache.getline(frame.f_code.co_filename, frame.f_lineno, frame.f_globals)
        part1 = '<div><div class="indent icon closed normal" onclick="changeIcon(this, \'div-%s\')" onmouseover="changeClass(this, \'normal\', \'hl\')" onmouseout="changeClass(this, \'hl\', \'normal\')">&nbsp;&nbsp;%s</div>' \
                % (n, line1)
        part2 = ''
        if line2:
            part2 = '<div class="indent icon">&nbsp;&nbsp;&nbsp;&nbsp;%s</div>' % line2.strip()

        part3 = '<div id="div-%s" class="icon local" style="display:none">' % n

        local_L = []
        for key, value in frame.f_locals.items():
            s = '<Error get value>'
            try:
                s = str(value)
            except Exception, e:
                pass
            local_L.append(r'<div class="indent">&nbsp;&nbsp;&nbsp;&nbsp;%s = %s <span class="t">%s</span></div>' % (key, _html_encode(s), _html_encode(str(type(value)))))
        if not local_L:
            local_L.append(r'<div class="indent">&nbsp;&nbsp;&nbsp;&nbsp;no local variable</div>')
        part4 = ''.join(local_L)
        part5 = '</div></div>'
        L.append(part1)
        L.append(part2)
        L.append(part3)
        L.append(part4)
        L.append(part5)
    L.append('<div><div class="icon">%s: %s</div></div>' % (etype.__name__, evalue.message))
    L.append(r'<div class="line"></div><div>Powered by <a href="http://www.itranswarp.com/" target="_blank">iTranswarp</a></div></body></html>')
    return L

class WSGIApplication(object):

    def _getmtime(self, fpath):
        if fpath.endswith('.pyc'):
            fpath = fpath[:-1]
        return os.path.getmtime(fpath)

    def _autoreload(self):
        shouldreload = False
        for mod in self.modules:
            if self._getmtime(mod.__file__) > mod.mtime:
                _log('[DEBUG] auto reload module: %s' % mod.__name__)
                reload(mod)
                mod.mtime = self._getmtime(mod.__file__)
                shouldreload = True
        if shouldreload:
            self.get_static_routes, self.post_static_routes, self.get_re_routes, self.post_re_routes = self._parse_routes(self.modules, self._debug)

    def _parse_modules(self, modules, debug):
        L = []
        for mod in modules:
            last = mod.rfind('.')
            name = mod if last==(-1) else mod[:last]
            spam = __import__(mod, globals(), locals(), [name])
            if debug:
                spam.mtime = self._getmtime(spam.__file__)
            L.append(spam)
        return L

    def _parse_routes(self, mods, debug):
        get_static_routes = {}
        post_static_routes = {}
        get_re_routes = []
        post_re_routes = []
        for mod in mods:
            for p in dir(mod):
                f = getattr(mod, p)
                if callable(f):
                    route = getattr(f, '__web_route__', None)
                    if route:
                        r = Route(route, f)
                        if r.static:
                            if f.__web_get__:
                                get_static_routes[r.str_route] = r
                                _log('found static route: GET %s' % route)
                            if f.__web_post__:
                                post_static_routes[r.str_route] = r
                                _log('found static route: POST %s' % route)
                        else:
                            if f.__web_get__:
                                get_re_routes.append(r)
                                _log('found regex route: GET %s' % route)
                            if f.__web_post__:
                                post_re_routes.append(r)
                                _log('found regex route: POST %s' % route)
        # append '^/static/.*$' to serv static files:
        get_re_routes.append(Route('/static/<path:path>', static_file_handler))
        # append '^/favicon.ico$' to serv fav icon:
        get_re_routes.append(Route('/favicon.ico', favicon_handler))
        return get_static_routes, post_static_routes, get_re_routes, post_re_routes

    def _mkfilters(self, filters):
        if filters:
            L = list(filters)
            L.reverse()
            func = self._exec
            for f in L:
                func = f(func)
            return func
        else:
            return self._exec

    def __init__(self, modules, filters=None, document_root=None, encoding='utf-8', template_engine=None, **kw):
        '''
        Init a WSGIApplication.

        Args:
          modules: a list of modules that contains routes.
          document_root: document root path, default to None.
          template_engine: name of template engine, or function that can install a template engine.
                           The built-in supported template engines are 'mako', 'jinja2' and 'cheetah'.
          kw: keywords args:
              DEBUG = True|False, default to False. Modules will automatically reloaded if changed in debug mode.
        '''
        self._debug = kw.pop('DEBUG', False)
        self.modules = self._parse_modules(modules, self._debug)
        self._filters = self._mkfilters(filters)
        self.get_static_routes, self.post_static_routes, self.get_re_routes, self.post_re_routes = self._parse_routes(self.modules, self._debug)
        self.error_handler = _default_error_handler
        self.document_root = document_root
        _log('load document_root: %s' % str(self.document_root))

        if isinstance(template_engine, basestring):
            self.template_render = _install_template_engine(template_engine, self.document_root)
        elif callable(template_engine):
            self.template_render = template_engine

    def _exec(self, r, kw, start_response):
        global ctx
        try:
            ret = r.execute() if kw is None else r.execute(**kw)
        except RedirectError as e:
            ctx.response.set_header('Location', e.location)
            start_response(e.status, ctx.response.headers)
            return ()
        except Exception as e:
            return self.error_handler(e, start_response, self._debug)
        if isinstance(ret, types.GeneratorType):
            start_response(ctx.response.status, ctx.response.headers)
            return ret
        # if ret instance of Template...
        if isinstance(ret, str):
            ctx.response.write(ret)
        elif isinstance(ret, unicode):
            ctx.response.write(ret.encode('utf-8'))
        elif isinstance(ret, Template):
            ctx.response.write(self.template_render(ret.template_name, **ret.model))
        elif ret is not None:
            ctx.response.write(str(ret))
        start_response(ctx.response.status, ctx.response.headers)
        return ctx.response.body

    def __call__(self, environ, start_response):
        if self._debug:
            self._autoreload()
        method = environ['REQUEST_METHOD']
        is_get = method=='GET'
        is_post = method=='POST'
        if not is_get and not is_post:
            return self.error_handler(HttpError(400), start_response, self._debug)
        kw = None
        static_routes = self.get_static_routes if is_get else self.post_static_routes
        path_info = environ['PATH_INFO']
        r = static_routes.get(path_info, None)
        if r:
            _log('matched static route: %s' % path_info)
        else:
            re_routes = self.get_re_routes if is_get else self.post_re_routes
            for rt in re_routes:
                m = rt.route.match(path_info)
                if m:
                    r = rt
                    kw = m.groupdict()
                    _log('matched regex route: %s' % path_info)
                    break
        if not r:
            _log('no route matched: %s' % path_info)
            return self.error_handler(HttpError(404), start_response, self._debug)

        global ctx
        ctx.document_root = self.document_root or environ.get('DOCUMENT_ROOT', '')
        ctx.server_name = environ.get('SERVER_NAME', '')
        ctx.request = Request(environ)
        ctx.response = Response()
        _log('ctx.document_root: %s' % ctx.document_root)
        try:
            return self._filters(r, kw, start_response)
        finally:
            del ctx.document_root
            del ctx.server_name
            del ctx.request
            del ctx.response

if __name__=='__main__':
    sys.path.append('.')
    import doctest
    doctest.testmod()
 