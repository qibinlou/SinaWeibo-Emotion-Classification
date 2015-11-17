SinaWeibo-Emotion-Classification
================================

##新浪微博情感分析应用
> Update：本项目由于长久未更新以及新浪微博接口变动等问题已无法正常使用，仅作参考

####应用地址：http://tobeornottobe.sinaapp.com
####应用Github主页：http://qibinlou.github.io/SinaWeibo-Emotion-Classification/ 

###应用功能
* 简单版本的新浪微博功能，支持发微博，浏览关注的人的微博、自己的微博
* 微博情感分析，支持分析用户最近三个月、六个月、九个月、十二个月（转）发的微博，分析得出用户这段时间内“正能量”的、“负能量”的、“中性”的微博的条数，从而分析得出用户这段时间的情感总体状况，支持将分析结果发到微博。
* 用户微博关键词提取，通过分词以及一系列频率分析算法提取用户一段时间内的微博关键词，结果通过“标签云”形式展示，支持将这个“标签云”截图发到新浪微博上。
* 任意微博自动情感分类。支持用户自己的微博、好友的微博、关注人的微博，当鼠标悬浮在该微博上时，自动将该微博分类，分类结果为三类：i)正能量型，用绿色背景表示  ii)客观型，用蓝色背景表示 iii)负能量型，用红色背景表示


###如何使用
1. Python依赖包：`nltk`,`jieba`,`jinja2`,`transwarp`,`pickle`
2. 本地开发环境下，首先将init.sql中的数据库配置导入MySQL数据库中，修改devapp.py文件中的mysql配置数据
3. 申请Sina Weibo 应用，获取app id和app secret key，修改应用的回调地址为`http://127.0.0.1:8080/callback`
3. 在本项目根目录命令行下运行：`python devapp.py`，在浏览器中输入`127.0.0.1：8080`即可看到首页
4. 在`127.0.0.1:8080/admin`，密码是`admin`，中修改APP id 和APP secret key
5. 回到首页登陆即可使用
6. SAE环境下配置类似1~5步

###应用Demo图
!['website demo image'](http://tobeornottobe.sinaapp.com/static/i/home.jpg)

###反馈意见
* 邮件联系我：qibinlou#hotmail.com(#用@代替)
* 在Github本项目下发起issue讨论

###Licence
**MIT**
