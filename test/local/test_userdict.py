#encoding=utf-8
import sys
sys.path.append("../")
import jieba
jieba.load_userdict("userdict.txt")
import jieba.posseg as pseg

#test_sent = "李小福是创新办主任也是云计算方面的专家;"
#test_sent += "例如我输入一个带“韩玉赏鉴”的标题，在自定义词库中也增加了此词为N类型"
test_sent = '[黑线][奥特曼]不知道大家在干嘛呢，bm哈bm挖鼻孔[懒得理你]群体围观hold住吗？你红包让红包飞moc转发Orz和。。你好吗天安门=。=TATTTdin阿赞招财猫狗大战'
words = jieba.cut(test_sent)
print '\n'.join([w for w in words])

# result = pseg.cut(test_sent)

# for w in result:
#     print w.word, "/", w.flag, ", ",  

# print "\n========"

# terms = jieba.cut('easy_install is great')
# for t in terms:
#     print t
# print '-------------------------'
# terms = jieba.cut('python 的正则表达式是好用的')
# for t in terms:
#     print t