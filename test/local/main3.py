#coding=utf-8

import random
import jieba
import nltk
import pickle


def gender_features(weibo):
    global word_features
    a = jieba.cut(weibo)
    fl = (" ".join(a)).split()
    fd = {}
    for word in word_features:
        fd[u'contains(%s)'%word] = (word in fl)
    return fd

        
if __name__ == '__main__':
   
    word_features = pickle.load(open('word_features.dat','r'))
    classifier = pickle.load(open("classifierdata.dat","r"))
    
    print "Readed Classifier!"
    print classifier.classify(gender_features(u'[哈哈]我肚子痛死了'))
    # print nltk.classify.accuracy(classifier,test_set)
    # classifier.show_most_informative_features(15)
    while True:
        query = raw_input()
        print classifier.classify(gender_features(query))