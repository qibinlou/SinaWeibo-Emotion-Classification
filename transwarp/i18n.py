#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__ = 'Michael Liao'

'''
I18N support.
'''

import os, re, logging, codecs, threading

_RE_EQUALS = re.compile(r'(?<!\\)\=')
_I18N_MAP = dict()

# thread local object for storing locale.
_locale = threading.local()

def _load(fpath):
    '''
    Load a i18n file.

    >>> _locale.locales = ['en']
    >>> d = _load('test/i18n-test.txt')
    >>> d['Hello, world!']
    u'\u4f60\u597d\uff0c\u4e16\u754c\uff01'
    >>> d['Hi, %s!']
    u'\u55e8\uff0c%s\uff01'
    >>> d['1 + 1 = 2']
    u'\u4e00\u52a0\u4e00\u7b49\u4e8e\u4e8c'
    >>> del _locale.locales
    '''
    d = dict()
    with codecs.open(fpath, 'r', 'utf-8') as f:
        for line in f.readlines():
            line = line.strip()
            if line.startswith(u'#'):
                continue
            m = _RE_EQUALS.search(line)
            if m:
                pos = m.start(0)
                key = line[:pos].strip().replace(ur'\=', u'=')
                value = line[pos+1:].strip()
                if key and value:
                    d[key] = value
    return d

class _Locale(object):
    '''
    Locale object that can set and cleanup locales.

    >>> with locale(): _locale.locales
    []
    >>> with locale('en', 'zh_cn', 'fr'): _locale.locales
    ['en', 'zh_cn', 'fr']
    '''
    def __init__(self, *locales):
        logging.info('set locale: %s' % str(locales))
        self._locales = [str(l).replace('-', '_') for l in locales]

    def __enter__(self):
        global _locale
        _locale.locales = self._locales

    def __exit__(self, exctype, excvalue, traceback):
        global _locale
        del _locale.locales

def current_locales():
    global _locale
    return _locale.locales

def first_locale():
    '''
    >>> with locale(): first_locale()
    'en'
    >>> with locale('zh'): first_locale()
    'zh'
    '''
    global _locale
    return _locale.locales[0] if _locale.locales else 'en'

def locale(*locales):
    '''
    Run code within a locale definition:

    with locale('en', 'zh_cn'):
        pass
    '''
    return _Locale(*locales)

def i18n(text):
    '''
    >>> _locale.locales = ['zh_cn']
    >>> _I18N_MAP['zh_cn'] = _load('test/i18n-test.txt')
    >>> i18n('Hello, world!')
    u'\u4f60\u597d\uff0c\u4e16\u754c\uff01'
    >>> del _locale.locales
    '''
    locale = first_locale()
    translate = _I18N_MAP.get(locale)
    if translate:
        return translate.get(text, text)
    return text

def install_i18n():
    import __builtin__
    __builtin__.__dict__['_'] = i18n

_RE_LOCALE_FILE = re.compile(r'^[a-zA-Z]{2}(\_[a-zA-Z]{2})?\.txt$')

def load_i18n(*fpaths):
    for fpath in fpaths:
        fname = os.path.split(fpath)[1]
        m = _RE_LOCALE_FILE.match(fname)
        if m:
            logging.info('load i18n file: %s' % fpath)
            d = _load(fpath)
            if d:
                locale = fname[:-4].lower()
                ll = _I18N_MAP.get(locale)
                if ll is None:
                    ll = dict()
                    _I18N_MAP[locale] = ll
                ll.update(d)
        else:
            logging.warning('Invalid file name for i18n: %s' % fpath)

def _match(fname, patterns):
    for p in patterns:
        r = '^%s$' % p.replace('.', r'\.').replace('*', r'.*').replace('?', r'.')
        if re.match(r, fname):
            return True
    return False

def _extract_msg(root_path, locale, includes=('*.py', '*.html'), excludes=()):
    root_path = os.path.abspath(root_path)
    print 'scan path %s...' % root_path
    RE_MSG = re.compile(r'\_\s*\(\s*(u?r?)\'(.*?)\'\s*\)')
    d = dict()
    L = [f for f in os.listdir(root_path) if not f.startswith('.')]
    fs = [os.path.join(root_path, f) for f in L if os.path.isfile(os.path.join(root_path, f)) and _match(f, includes) and not _match(f, excludes)]
    ds = [os.path.join(root_path, f) for f in L if os.path.isdir(os.path.join(root_path, f)) and not os.path.isdir(os.path.join(root_path, f, 'i18n'))]
    for fpath in fs:
        print 'scan file %s...' % fpath
        with open(fpath, 'r') as f:
            n = 0
            for line in f.readlines():
                start = 0
                while True:
                    m = RE_MSG.search(line, start)
                    if m:
                        s = m.group(2).strip()
                        if not 'r' in m.group(1):
                            s = s.replace('\\', '')
                        if not s in d:
                            d[s] = ''
                        start = m.end(2)
                    else:
                        break
                n = n + 1
    for dpath in ds:
        d.update(_extract_msg(dpath, locale, includes, excludes))
    return d

if __name__=='__main__':
    install_i18n()
    import doctest
    doctest.testmod()
