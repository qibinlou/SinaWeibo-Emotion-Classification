#!/usr/bin/env python
#coding=utf-8

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
    for i in fl:print i
    # print '嘻嘻' in fl
    fd = {}
    for word in word_features:

        fd['contains(%s)'%word] = (word in fl)
        #print word.decode('utf8').encode('utf8')
        # print isinstance(fl[0],unicode)
        # if isinstance(word,unicode):
        #     print word
        # else:
        #     print type(word).__name__
        #print word, word.decode('utf8').encode('utf8') in fl
    return fd

def readin(path):
    fin = open(path,"r")
    content = fin.readlines()
    fin.close()
    return content
    

if __name__ == '__main__':
    
    global word_features 
    word_features = open('features.dat', 'r').readlines()
    word_features = [w[:-1].decode('utf8') for w in word_features]
    wf = pickle.dumps(word_features)
    fout = open('word_features.dat','w')
    fout.write(wf)
    fout.close()

    
    fd = gender_features(u'嘻嘻嘿嘿爱感谢话筒我爱你么么哒')
    # print fd
    
    # gender_features(content[0][1:],word_features)
    # count = 0 
    # for i in word_features:
    #     count = count + 1
    #     if count == 400:
    #         break
    #     try:
    #         print i
    #     except Exception, e:
    #         pass

    content = readin("sentimentweibo.txt")
    features = [(gender_features(line[1:]),line[0]) for line in content]    
    random.shuffle(features)

    rate = 0.8
    features_len = len(features)
    train_set = features[:int(rate*features_len)]
    test_set = features[int(rate*features_len):]
    classifier = nltk.NaiveBayesClassifier.train(train_set)
    # classifier = nltk.DecisionTreeClassifier.train(train_set)
    
    # classifier = nltk.MaxentClassifier.train(train_set)
    print "Training Done!"
    classifierdata = pickle.dumps(classifier)
    fout = open("classifierdata.dat","w")
    fout.write(classifierdata)
    fout.close()
    print "Save Classifier!"
    print classifier.classify(gender_features(u'[哈哈]我肚子痛死了'))
    print nltk.classify.accuracy(classifier,test_set)
    classifier.show_most_informative_features(45)
    # while True:
    #     query = raw_input()
    #     print classifier.classify(gender_features(query))