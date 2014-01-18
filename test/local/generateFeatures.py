#!/usr/bin/env python
# -*- coding: utf-8 -*-

import random
import jieba
import nltk
import pickle
jieba.load_userdict("userdict.txt")
def run():
    pass

def gender_features(weibo):
    global word_features
    a = jieba.cut(weibo)
    fl = (" ".join(a)).split()
    fd = {}
    for word in word_features:
        fd[u'contains(%s)'%word] = (word in fl)
    return fd

def readin(path):
    fin = open(path,"r")
    content = fin.readlines()
    fin.close()
    return content
    

if __name__ == '__main__':
    print "main function"
    content = readin("sentimentweibo.txt")
    # content = readin("finaldata2.txt")
    words = []
    stop_words = readin("stopwords.txt")
    stop_words = [w[:-1] for w in stop_words]
    # for i in stop_words:print i
    # for i in stop_words:print i.decode('utf8').encode('gbk')
    for line in content:
        a = jieba.cut(line[1:])
        fl = (" ".join(a)).split()
        # for w in fl:
        #     if w not in stop_words:
        #         try:
        #             print w
        #         except Exception, e:
        #             print e
        words += [w for w in fl if w not in stop_words]
        # print words[0],words[1]
    del content
    all_words = nltk.FreqDist(words)
    global word_features 
    print "ssssss",len(all_words)
    
    featuretpl = readin('features2.dat')
    featuretpl = [w[:-1] for w in featuretpl]
    # for i in featuretpl:print i

    all_words_keys = all_words.keys()
    # for i in range(1000):
    #     print all_words_keys[i], all_words[all_words_keys[i]]

    count = 0
    features = []

    print 'Teeeeeeeeee', '嘻嘻' in all_words_keys, '嘻嘻' in featuretpl

    for w in all_words_keys:
        if (not w.isalnum() and   len(w) > 3 and ('.' not in w) and ('_' not in w) ) or (w.encode('utf8') in featuretpl):
        # if 1: 
            print w, all_words[w]
            features.append(w)
            count += 1
            if count > 1500:
                break
    
    
    fout = open('features.dat','w')
    for w in features:
        try:

            fout.write(w.encode('utf8'))
            fout.write('\n')
            
        except Exception, e:
            print e
    fout.close()

    
    
   
   