#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__ = 'Michael Liao'

import time, json, base64, logging, hashlib
from datetime import datetime, tzinfo, timedelta

from transwarp.web import ctx, get, post, route, seeother, forbidden, jsonresult, Template
from transwarp import db

from weibo import APIError, APIClient
import pickle, random, jieba,jieba.analyse
import StringIO
try:
  	import pylibmc
except Exception,e:
    pass
try:
   import nltk
except Exception, e:
   print e
   try:
       from nltk import FreqDist
       import nltk.NaiveBayesClassifier
   except Exception, e:
       pass 
   

#import nltk

_TD_ZERO = timedelta(0)
_TD_8 = timedelta(hours=8)

#using memcache
#mc = pylibmc.Client()

#mc.set('test','testyourmoathaf')
#mc.incr('test')
#word_features = mc.get('word_features')
#classifier = mc.get('classifier')
#if not mc.get('word_features'):
 #   word_features = pickle.load(open('word_features.dat','r'))
  #  mc.set("word_features", str(word_features) )

word_features = pickle.load(open('word_features.dat','r'))
classifier = pickle.load(open("classifierdata.dat","r"))

class UTC8(tzinfo):
    def utcoffset(self, dt):
        return _TD_8

    def tzname(self, dt):
        return "UTC+8:00"

    def dst(self, dt):
        return _TD_ZERO

_UTC8 = UTC8()

def _format_datetime(dt):
    t = datetime.strptime(dt, '%a %b %d %H:%M:%S +0800 %Y').replace(tzinfo=_UTC8)
    return time.mktime(t.timetuple())

def _format_user(u):
    return dict(id=str(u.id), screen_name=u.screen_name, profile_url=u.profile_url, verified=u.verified, verified_type=u.verified_type, profile_image_url=u.profile_image_url)



def _format_weibo(st):
    # user = st.user
    # print "type", type(st),st['rank']
    r = dict(
        text = st.text,
        created_at = _format_datetime(st.created_at)
    )
    try:
        r['user'] = _format_user(st.user)
    except Exception, e:
        print e 
        r['user'] = dict(id='123456',screen_name='weibo',profile_url='',verified='0',verified_type='0',profile_image_url='')
    
    try:
        r['reposts_count'] = st.reposts_count
    except Exception, e:
        r['reposts_count'] = 0
    try:
        r['comments_count'] = st.comments_count
    except Exception, e:
        r['comments_count'] = 0
    else:
        pass


    try:
        r['type'] = st.rank
    except Exception, e:
        print e
    
    if 'original_pic' in st:
        r['original_pic'] = st.original_pic
    if 'thumbnail_pic' in st:
        r['thumbnail_pic'] = st.thumbnail_pic
    if 'retweeted_status' in st:
        r['retweeted_status'] = _format_weibo(st.retweeted_status)
    return r

@get('/')
def index():
    u = _check_cookie()
    #return Template('./static/signin.html')
    if u is None:
        return Template('./static/signin.html')
    return Template('static/myweibo.html', user=u)


@get('/go')
def app():
    u = _check_cookie()
    if u is None:
        return Template('static/signin.html')
    return Template('static/index.html', user=u)


@post('/update')
@jsonresult
def update():
    u = _check_cookie()
    if u is None:
        return dict(error='failed', redirect='/signin')
    client = _create_client()
    client.set_access_token(u.auth_token, u.expired_time)
    try:
        
        r = client.statuses.update.post(status=ctx.request['status'])
        # r = client.statuses.update.post(status=ctx.request['status'], pic = StringIO.StringIO(ctx.request['dataurl'].encode('utf8')))
        if 'error' in r:
            return r
        return dict(result='success')
    except APIError, e:
        return dict(error='failed')

@route('/friends')
@jsonresult
def friends():
    u = _check_cookie()
    if u is None:
        return dict(error='failed', redirect='/signin')
    client = _create_client()
    client.set_access_token(u.auth_token, u.expired_time)
    try:
        r = client.friendships.friends.get(uid=u.id, count=99)
        return [_format_user(u) for u in r.users]
    except APIError, e:
        return dict(error='failed')

@route('/bifriends')
@jsonresult
def bifriends():

    u = _check_cookie()
    if u is None:
        return dict(error='failed', redirect='/signin')
    # return
    client = _create_client()
    client.set_access_token(u.auth_token, u.expired_time)
    try:
        r = client.friendships.friends.bilateral.get(uid=u.id, count=99)
        return [_format_user(u) for u in r.users]
    except APIError, e:
        return dict(error='failed')

@route('/analysis')
@jsonresult
def analysis():
    u = _check_cookie()
    if u is None:
        return dict(error='failed', redirect='/signin')
    month = int(ctx.request.get('month'))
    weibo = getWeiboByTime(months = month)
    analysis_result, weibo, keywords= weiboAnalysis(weibo)
    # for w in weibo:
    #     print "analysis", w['rank']
    weibo = [_format_weibo(wb) for wb in weibo]
    remark = ''
    if analysis_result[0] > analysis_result[2]:
        remark = u'经检测我这段时间内的负能量过高，需要补充正能量!'
    else:
        remark = u'经检测我这段时间内正能量爆棚啦哇咔咔！'

    return json.dumps({'total':len(weibo), 'pos' : analysis_result[2], 'neu' : analysis_result[1], 'neg' : analysis_result[0], 'weibo' : weibo, 'keywords' : keywords, 'remark' : remark})

@route('/load')
@jsonresult
def load():
    u = _check_cookie()
    if u is None:
        return dict(error='failed', redirect='/signin')
    client = _create_client()
    client.set_access_token(u.auth_token, u.expired_time)
    try:
        r = client.statuses.home_timeline.get()
        return [_format_weibo(s) for s in r.statuses]
    except APIError, e:
        return dict(error='failed')

@route('/myweibo')
@jsonresult
def myweibo():
    u = _check_cookie()
    if u is None:
        return dict(error='failed', redirect='/signin')
    # return
    client = _create_client()
    client.set_access_token(u.auth_token, u.expired_time)
    try:
        r = client.statuses.user_timeline.get()
        return [_format_weibo(s) for s in r.statuses]
    except APIError, e:
        return dict(error='failed')


@post('/hint')
@jsonresult
def hint():
    u = _check_cookie()
    if u is None:
        return dict(error='failed', redirect='/signin')
    client = _create_client()
    client.set_access_token(u.auth_token, u.expired_time)
    try:
        return client.remind.unread_count.get()
    except APIError, e:
        return dict(error='failed')

@get('/signin')
def signin():
    client = _create_client()
    raise seeother(client.get_authorize_url())

@get('/signout')
def signout():
    ctx.response.set_cookie(_COOKIE, 'deleted', max_age=0)
    raise seeother('/')

@get('/callback')
def callback():
    i = ctx.request.input(code='')
    code = i.code
    client = _create_client()
    r = client.request_access_token(code)
    logging.info('access token: %s' % json.dumps(r))
    access_token, expires_in, uid = r.access_token, r.expires_in, r.uid
    client.set_access_token(access_token, expires_in)
    u = client.users.show.get(uid=uid)
    logging.info('got user: %s' % uid)
    users = db.select('select * from users where id=?', uid)
    user = dict(name=u.screen_name, \
            image_url=u.avatar_large or u.profile_image_url, \
            statuses_count=u.statuses_count, \
            friends_count=u.friends_count, \
            followers_count=u.followers_count, \
            verified=u.verified, \
            verified_type=u.verified_type, \
            auth_token=access_token, \
            expired_time=expires_in)
    if users:
        db.update_kw('users', 'id=?', uid, **user)
    else:
        user['id'] = uid
        db.insert('users', **user)
    _make_cookie(uid, access_token, expires_in)
    raise seeother('/')

_COOKIE = 'authuser'
_SALT = 'A random string'

def _make_cookie(uid, token, expires_in):
    expires = str(int(expires_in))
    s = '%s:%s:%s:%s' % (str(uid), str(token), expires, _SALT)
    md5 = hashlib.md5(s).hexdigest()
    cookie = '%s:%s:%s' % (str(uid), expires, md5)
    ctx.response.set_cookie(_COOKIE, base64.b64encode(cookie).replace('=', '_'), expires=expires_in)

def _check_cookie():
    try:
        b64cookie = ctx.request.cookies[_COOKIE]
        cookie = base64.b64decode(b64cookie.replace('_', '='))
        uid, expires, md5 = cookie.split(':', 2)
        if int(expires) < time.time():
            return
        L = db.select('select * from users where id=?', uid)
        if not L:
            return
        u = L[0]
        s = '%s:%s:%s:%s' % (uid, str(u.auth_token), expires, _SALT)
        if md5 != hashlib.md5(s).hexdigest():
            return
        return u
    except BaseException:
        pass

_APP_ID = ''
_APP_SECRET = ''
_ADMIN_PASS = 'admin'

@get('/admin')
def show_admin():
    return '''<html>
<body>
<form action="/admin" method="post">
<p>Input password:</p>
<p><input type="password" name="passwd" /></p>
</form>
</body>
</html>
'''

@post('/admin')
def do_admin():
    global _APP_ID, _APP_SECRET, _ADMIN_PASS

    i = ctx.request.input()
    if i.passwd != _ADMIN_PASS:
        raise forbidden()
    admin_pass = i.get('new_passwd', '')
    app_id = i.get('app_id', '')
    app_secret = i.get('app_secret', '')
    msg = ''
    if admin_pass and app_id and app_secret:
        db.update('delete from settings')
        db.update('insert into settings (id, value) values (?, ?)', 'app_id', app_id)
        db.update('insert into settings (id, value) values (?, ?)', 'app_secret', app_secret)
        db.update('insert into settings (id, value) values (?, ?)', 'admin_pass', admin_pass)
        msg = 'Updated!'
        _APP_ID = app_id
        _APP_SECRET = app_secret
        _ADMIN_PASS = admin_pass
    return '''<html>
<body>
<p>%s</p>
<form action="/admin" method="post">
<p>App ID:</p>
<p><input type="text" name="app_id" value="%s" /></p>
<p>App Secret:</p>
<p><input type="text" name="app_secret" value="%s" /></p>
<p>Old Password:</p>
<p><input type="text" name="passwd" readonly="readonly" value="%s" /></p>
<p>New Password:</p>
<p><input type="text" name="new_passwd" value="%s" /></p>
<p>WARNING: click submit will update app_id, app_secret and admin password!</p>
<p><input type="submit" name="submit" value="Submit" /></p>
</form>
</body>
</html>
''' % (msg, _APP_ID, _APP_SECRET, _ADMIN_PASS, _ADMIN_PASS)

def _load_app_info():
    global _APP_ID, _APP_SECRET, _ADMIN_PASS
    for s in db.select('select * from settings'):
        if s.id == 'app_id':
            _APP_ID = s.value
        if s.id == 'app_secret':
            _APP_SECRET = s.value
        if s.id == 'admin_pass':
            _ADMIN_PASS = s.value

def _create_client():
    global _APP_ID, _APP_SECRET
    try:
        import sae
    except Exception, e:
        return APIClient(_APP_ID, _APP_SECRET, 'http://127.0.0.1:8080/callback')    
    else:
        return APIClient(_APP_ID, _APP_SECRET, 'http://tobeornottobe.sinaapp.com/callback')
    

def transformTime(created_time):
    a = created_time.split()
    month_mapping = {'Jan' : '01', 'Feb' : '02', 'Mar' : '03', 'Apr' : '04', 'May' : '05', 'Jun' : '06', 'Jul' : '07', 'Aug' : '08', 'Sep' : '09', 'Oct' : '10', 'Nov' : '11', 'Dec' : '12'}
    t = a[-1] + month_mapping[a[1]] + a[2]
    return t


def getWeiboByTime(assigned_time = None, months = 3):
    import time
    t = time.strftime('%Y%m',time.localtime(time.time() - 2592000 * (months-1))) + '01'
    if assigned_time:
        t = assigned_time
    weibo = []
    page = 1
    u = _check_cookie()
    if u is None:
        return dict(error='failed', redirect='/signin')
    client = _create_client()
    client.set_access_token(u.auth_token, u.expired_time)
    while True:
        wbs = client.statuses.user_timeline.get( count = 100, page = page)
        flag = False
        for wb in wbs['statuses']:
            if transformTime(wb['created_at']) >= t:
                # text = wb['text']
                # if 'retweeted_status' in wb:
                #     text += wb['retweeted_status']['text']
                weibo.append(wb)
                # print transformTime(wb['created_at'])
            else:
                flag = True
                break
        page += 1
        if flag:
            break
    print "Total weibos: %d" %(len(weibo))
    return weibo

def gender_features(weibo):
    global word_features
    a = jieba.cut(weibo)
    fl = (" ".join(a)).split()
    fd = {}
    for word in word_features:
        fd[u'contains(%s)'%word] = (word in fl)
    return fd

def weiboAnalysis(weibo):
    """weibo analysis tool"""
    data = [0] * 3
    keywords = []
    global classifier 
    for i in range(len(weibo)):
        w = weibo[i]
        text = w['text']
        if 'retweeted_status' in w:
            text += w['retweeted_status']['text']
            keywords += jieba.analyse.extract_tags(text, topK=10)    
        rank = int(classifier.classify(gender_features(text)))
        weibo[i]['rank'] = rank
        data[rank] += 1
        # print rank, '\n\n'
    # for w in weibo:
    #     print "rank", w['rank']
    print u'Total analysis: %d' %(len(weibo))
    for i in range(3) :
        print i, ' ', data[i]
    keywords = nltk.FreqDist(keywords).keys()[:300]
    # for i in keywords:
    #     print i
    return data, weibo,keywords

_load_app_info()
