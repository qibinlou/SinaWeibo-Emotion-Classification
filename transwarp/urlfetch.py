#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''
A simple url fetch service.
'''

__author__ = 'Michael Liao'

import re, base64, json, time, hashlib, datetime, mimetypes, logging, urllib, urllib2, urlparse

_USER_AGENTS = dict(
        ipad = 'Mozilla/5.0 (iPad; CPU OS 6_0 like Mac OS X) AppleWebKit/536.26 (KHTML, like Gecko) Version/6.0 Mobile/10A5355d Safari/8536.25',
        iphone = 'Mozilla/5.0 (iPhone; CPU OS 6_0 like Mac OS X) AppleWebKit/536.26 (KHTML, like Gecko) Version/6.0 Mobile/10A5355d Safari/8536.25',
        android = 'Mozilla/5.0 (Linux; Android 4.1.1; Nexus 7) AppleWebKit/535.19 (KHTML, like Gecko) Chrome/18.0 Safari/535.19',
        ie6 = 'Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.1)',
        ie7 = 'Mozilla/5.0 (compatible; MSIE 7.0; Windows NT 6.0)',
        ie8 = 'Mozilla/5.0 (compatible; MSIE 8.0; Windows NT 6.1)',
        ie9 = 'Mozilla/5.0 (compatible; MSIE 9.0; Windows NT 6.1)',
        ie10 = 'Mozilla/5.0 (compatible; MSIE 10.0; Windows NT 6.1)',
        firefox = 'Mozilla/5.0 (Windows NT 6.1) Gecko/20121011 Firefox/16.0',
        chrome = 'Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.4 (KHTML, like Gecko) Chrome/22.0 Safari/537.4',
        safari = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_8) AppleWebKit/537.4 (KHTML, like Gecko) Version/5.2 Safari/537.4')

class UrlFetchError(StandardError):
    pass

class FetchResponse(object):

    def __init__(self, headers, body):
        pass

def encode(html, content_type=None, default_encoding='utf-8'):
    '''
    Auto detect encoding and return unicode.
    '''
    encoding = default_encoding
    if content_type:
        ct = content_type.lower()
        r = ct.find('charset=')
        if r!=(-1):
            encoding = content_type[r+8:].strip()
    return html.decode(encoding)

def fetch(url, method='GET', payload=None, referer=None, user_agent=None, accept_language=None):
    '''
    Fetch url and return its response.

    Args:
        url: the url for fetch.
        method: http method, default to 'GET'.
        payload: a single str as payload for 'POST'. default to None.
        referer: the http Referer header, default to None.
        user_agent: the http user agent, default to None.
        accept_language: the http accept language header, default to None.
    Returns:
        content_type, response str as tuple.

    >>> content_type, html = fetch('http://weibo.com/', user_agent='ie8')
    >>> content_type
    'text/html; charset=utf-8'
    >>> html.find('<html')!=(-1)
    True
    >>> u = encode(html, content_type)
    >>> u.find(u'\u65b0\u6d6a\u5fae\u535a')!=(-1)
    True
    '''
    if isinstance(url, unicode):
        url = url.encode('utf-8')
    r = urlparse.urlparse(url)
    if r.scheme!='http' and r.scheme!='https':
        raise UrlFetchError('Scheme must be http or https')
    if method=='GET' and payload:
        raise UrlFetchError('Cannot set payload for GET')
    logging.info('%s %s' % (method, url))
    opener = urllib2.build_opener(urllib2.HTTPHandler)
    request = urllib2.Request(url, data=payload)
    request.get_method = lambda: method
    if payload:
        request.add_header('Content-Length', len(payload))
    if referer:
        request.add_header('Referer', referer)
    if user_agent:
        request.add_header('User-Agent', _USER_AGENTS.get(user_agent.lower(), user_agent))
    if accept_language:
        request.add_header('Accept-Language', accept_language)
    try:
        response = opener.open(request)
        return _get_content_type(response.headers), response.read()
    except urllib2.URLError, e:
        logging.warn('URLError: %s, reason: %s' % (url, e.reason))
        raise UrlFetchError(e)
    except urllib2.HTTPError, e:
        logging.warn('HTTPError: %s, body: %s' % (e.code, e.read))
        raise UrlFetchError(e)

def _get_content_type(headers):
    for k in headers:
        if k.lower()=='content-type':
            return headers[k]
    return None

if __name__=='__main__':
    import doctest
    doctest.testmod()
