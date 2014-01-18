#coding=utf-8

import random
import jieba
import nltk
def run():
    pass
def gender_features(weibo):
    a = jieba.cut(weibo[1:])
    fl = (" ".join(a)).split()
    fd = {}
    count = 1
    for i in fl:
        fd[str(count)] = i
        count += 1
    # print fd
    return fd

def readin(path):
    fin = open(path,"r")
    content = fin.readlines()
    fin.close()
    return content
    # for line in content:
    #     try:
    #         print line.decode('utf8').encode('gbk')
    #     except Exception, e:
    #         print e
    #         print line
        
    

if __name__ == '__main__':
    print "main function"
    run()
    content = readin("sentimentweibo.txt")
    features = [(gender_features(line),line[0]) for line in content]
    random.shuffle(features)
    words = []
    stop_words = readin("stopwords.txt")
    stop_words = [w[:-1].decode('utf8') for w in stop_words]
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
        words = words + [w for w in fl if w not in stop_words]
        # print words[0],words[1]
    all_words = nltk.FreqDist(words)
    word_features = all_words.keys()[:1000]
    for i in all_words:
        try:
            print i,all_words[i]
        except Exception, e:
            pass
        
    
    # rate = 0.75
    # features_len = len(features)
    # train_set = features[:int(rate*features_len)]
    # test_set = features[int(rate*features_len):]
    # classifier = nltk.NaiveBayesClassifier.train(train_set)
    # print nltk.classify.accuracy(classifier,test_set)
    # classifier.show_most_informative_features(5)