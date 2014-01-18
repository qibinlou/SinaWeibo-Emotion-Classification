#coding=utf-8

import random
import jieba
import nltk
import pickle
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
    global word_features 
    print "ssssss",len(all_words)
    word_features = all_words.keys()[:1500]
    wf = pickle.dumps(word_features)
    fout = open('word_features.dat','w')
    fout.write(wf)
    fout.close()

    
    
    # gender_features(content[0][1:],word_features)
    count = 0 
    for i in word_features:
        count = count + 1
        if count == 240:
            break
        try:
            print i
        except Exception, e:
            pass

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