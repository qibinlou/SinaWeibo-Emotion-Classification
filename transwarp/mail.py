#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__ = 'Michael Liao'

'''
Mail module for sending mail.
'''

import os, sys, time, uuid, random, datetime, functools, smtplib, logging, collections, mimetypes

from email import encoders
from email.header import Header
from email.utils import parseaddr, formataddr
from email.message import Message
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart

def smtp(host, port=None, username=None, passwd=None, use_tls=False):
    '''
    Generate a tuple that contains smtp info:
    (host, port, username, passwd, use_tls).
    e.g.:
    ('smtp.example.com', 25, 'user', 'passw0rd', False)
    '''
    if port is None:
        port = 465 if use_tls else 25
    return (host, port, username, passwd, use_tls)

def _encode_header(s):
    return Header(s, 'utf-8').encode()

def _format_addr(s):
    '''
    Format email address with utf-8 encoding.

    >>> _format_addr('test@email.com')
    'test@email.com'
    >>> _format_addr(u'Hello \u263A <hello@example.com>')
    '=?utf-8?b?SGVsbG8g4pi6?= <hello@example.com>'
    '''
    name, addr = parseaddr(s)
    return formataddr((_encode_header(name), _ensure_utf8(addr)))

def _ensure_addr_list(addrs):
    L = addrs
    if isinstance(addrs, basestring):
        L = [addrs]
    return [_format_addr(addr) for addr in L]

def _ensure_utf8(s):
    if isinstance(s, unicode):
        return s.encode('utf-8')
    return s

def _get_content_type(filename):
    '''
    Guess mime type.

    >>> _get_content_type('a.gif')
    ('image', 'gif')
    >>> _get_content_type('a.unknown')
    ('application', 'octet-stream')
    '''
    s = filename.lower()
    pos = s.rfind('.')
    if pos==(-1):
        return 'application', 'octet-stream'
    ext = s[pos:]
    mime = mimetypes.types_map.get(ext, 'application/octet-stream')
    pos = mime.find('/')
    if pos==(-1):
        return mime, ''
    return mime[:pos], mime[pos+1:]

def send_mail(smtp_cfg, from_addr, to_addrs, subject='', body='', cc_addrs=None, bcc_addrs=None, attaches=None):
    '''
    Send email.

    Args:
        smtp_cfg: SmtpConfig instance.
        from_addr: a valid email address like 'someone@example.com', or 'Name <someone@example.com>'.
        to_addrs: a single str email address, or list.
        subject: email subject, default to ''.
        body: email body, default to ''.
        cc_addrs: a single str or list, default to None.
        bcc_addrs: a single str or list, default to None.
        attaches: Mail attachments as list, each element contains ('filename', 'file content or file-like object'), default to None.

    >>> import base64
    >>> from StringIO import StringIO
    >>> import datetime
    >>> giffile = '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'
    >>> zipfile = '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'
    >>> yahoo = smtp('smtp.mail.yahoo.com', 25, 'itranswarp@yahoo.com', 'plz-do-not-change')
    >>> body = u'<html><body><h1>\\u263A</h1><p>Hello!!!</p><p><img src="cid:0" /></p><p>\\u263A Good day, isn\\'t it?</p></body></html>'
    >>> send_mail(yahoo, u'Hello \\u263A <itranswarp@yahoo.com>',
    ...     [u'\\u263A <itranswarptest@yahoo.com>', 'itranswarptest@gmail.com'],
    ...     u'A test mail from \\u263A@yahoo @%s' % datetime.datetime.now().ctime(),
    ...     body, attaches=(
    ...         ('goodday.gif', base64.b64decode(giffile)),
    ...         ('goodday.zip', base64.b64decode(zipfile))))
    >>> gmail = smtp('smtp.gmail.com', 587, 'itranswarptest@gmail.com', 'plz-do-not-change', True)
    >>> send_mail(gmail, u'Hi \\u263A <itranswarptest@gmail.com>',
    ...    [u'\\u263A <itranswarp@yahoo.com>', u'\\u263A <itranswarptest@yahoo.com>'],
    ...    u'A test mail from \\u263A@gmail @%s' % datetime.datetime.now().ctime(),
    ...    body, attaches=(
    ...        ('goodday.gif', StringIO(base64.b64decode(giffile))),
    ...        ('goodday.zip', StringIO(base64.b64decode(zipfile)))))
    '''
    from_addr = _format_addr(from_addr)
    to_addrs = _ensure_addr_list(to_addrs)

    subject = _ensure_utf8(subject)
    body = _ensure_utf8(body)
    content_type = 'html' if body.startswith('<html>') else 'plain'

    msg = MIMEMultipart() if attaches else MIMEText(body, content_type, 'utf-8')
    msg['From'] = from_addr
    msg['To'] = ', '.join(to_addrs)
    msg['Subject'] = _encode_header(subject)

    if attaches:
        msg.attach(MIMEText(body, content_type, 'utf-8'))
        cid = 0
        for filename, payload in attaches:
            filename = _ensure_utf8(filename)
            main_type, sub_type = _get_content_type(filename)
            if hasattr(payload, 'read'):
                payload = payload.read()
            fname = _encode_header(filename)
            mime = MIMEBase(main_type, sub_type, filename=fname)
            mime.add_header('Content-Disposition', 'attachment', filename=fname)
            mime.add_header('Content-ID', '<%s>' % cid)
            mime.add_header('X-Attachment-Id', '%s' % cid)
            mime.set_payload(payload)
            encoders.encode_base64(mime)
            msg.attach(mime)
            cid = cid + 1

    host, port, u, p, use_tls = smtp_cfg

    server = smtplib.SMTP('%s:%s' % (host, port))
    if use_tls:
        server.starttls()
    if u and p:
        server.login(u, p)
    server.sendmail(from_addr, to_addrs, msg.as_string())
    server.quit()

if __name__=='__main__':
    import doctest
    doctest.testmod()
