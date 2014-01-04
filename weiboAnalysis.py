#!/usr/bin/env python
#coding=utf-8

import random
import jieba
import nltk
import pickle
from weibo import APIError, APIClient

APP_KEY = '3357173382'            # app key
APP_SECRET = '7429e1824d38c77b09258b3624345ad4'      # app secret
CALLBACK_URL = 'http://127.0.0.1:8080/callback'  # callback url
client = APIClient(app_key=APP_KEY, app_secret=APP_SECRET, redirect_uri=CALLBACK_URL)
client.set_access_token('2.00UHhZqBmJ3MfD38221bf624hl6oCE', '1546415658')
word_features = pickle.load(open('word_features.dat','r'))
classifier = pickle.load(open("classifierdata.dat","r"))

def gender_features(weibo):
    global word_features
    a = jieba.cut(weibo)
    fl = (" ".join(a)).split()
    fd = {}
    for word in word_features:
        fd[u'contains(%s)'%word] = (word in fl)
    return fd

def getWeiboPro(st):
    wb = []
    for s in st['statuses']:
        text = s['text']
        if 'retweeted_status' in s:
            text += s['retweeted_status']['text']
        wb.append(text)
    return wb

def getWeibo(st):
    wb = []
    for s in st['statuses']:
        text = s['text']
        wb.append(text)
    return wb

def transformTime(created_time):
    a = created_time.split()
    month_mapping = {'Jan' : '01', 'Feb' : '02', 'Mar' : '03', 'Apr' : '04', 'May' : '05', 'Jun' : '06', 'Jul' : '07', 'Aug' : '08', 'Sep' : '09', 'Oct' : '10', 'Nov' : '11', 'Dec' : '12'}
    t = a[-1] + month_mapping[a[1]] + a[2]
    return t


def getWeiboByTime(assigned_time = None, months = 12):
    import time
    t = time.strftime('%Y%m',time.localtime(time.time() - 2592000 * (months-1))) + '01'
    if assigned_time:
        t = assigned_time
    weibo = []
    page = 1
    while True:
        wbs = client.statuses.user_timeline.get( count = 100, page = page, trim_user = 1)
        flag = False
        for wb in wbs['statuses']:
            if transformTime(wb['created_at']) >= t:
                text = wb['text']
                if 'retweeted_status' in wb:
                    text += wb['retweeted_status']['text']
                weibo.append(text)
                print transformTime(wb['created_at'])
            else:
                flag = True
                break
        page += 1
        if flag:
            break
    print "Total weibos: %d" %(len(weibo))
    return weibo

def weiboAnalysis(weibo):
    """weibo analysis tool"""
    data = [0] * 3
    global classifier 
    for w in weibo:
        print w
        rank = int(classifier.classify(gender_features(w)))
        data[rank] += 1
        print rank, '\n\n'
    print u'Total analysis: %d' %(len(weibo))
    for i in range(3) :
        print i, ' ', data[i]
    return data


# Test Functions
def test_transformTime():
    print transformTime('Sun Jun 30 12:27:28 +0800 2013')
    print transformTime('Sun Jan 01 12:27:28 +0800 2011')




if __name__ == '__main__':
   
    

    weibo = getWeiboByTime(months = 1)
    weiboAnalysis(weibo)

    








