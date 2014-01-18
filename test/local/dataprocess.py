#coding=utf-8

import random
import jieba
import nltk

def processA():
    fin = open("data.txt","r")
    content = fin.readlines()
    fin.close()
    fout = open("data_new.txt","w")
    rank = ''
    for line in content:
        if line[0] == 'd':
            rank = '0'
        elif line[0] == 's':
            rank = '1'
        else:
            rank = '2'
        fout.write(rank + line[1:])
    fout.close()

def processAA():
    fin = open("data2_new.txt","r")
    content = fin.readlines()
    fin.close()
    fout = open("data2_new.txt","w")
    rank = ''
    for line in content:
        if line[0] == '0' or line[0] == '1':
            rank = '0'
        elif line[0] == '2':
            rank = '2'
        else:
            rank = '1'
        fout.write(rank + line[1:])
    fout.close()
    
def processB():
    fin = open("data3.txt","r")
    content = fin.readlines()
    fin.close()
    fout = open("data3_new.txt","w")
    for line in content:
        ll = line.split('|**|')
        fout.write(ll[2][0] + " " +  ll[1] + "\n")
    fout.close()

def processC():
    fin = open("data2.txt","r")
    content = fin.readlines()
    fin.close()
    fout = open("data2_new.txt","w")
    for line in content:
        ll = line.split('|**|')
        try:
            fout.write(ll[2][0] + " " +  ll[1] + "\n")
        except Exception, e:
            print e
        
    fout.close()
        
    

if __name__ == '__main__':
    # processA()
    # processB()
    # processC()
    processAA()
   