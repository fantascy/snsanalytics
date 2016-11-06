import copy
import datetime


from sns.camp import consts as camp_const
from sns.chan import consts as channel_const
from client import conf, apiclient


USERS = [{'name':'Bryan Springer',
          'timeZone':'US/Central'
          },
         {'name':'Qa07 SA',
          'timeZone':'US/Eastern'
          }
         ]

CHANNELS = [
     
     {'name':'bryanspringer13',
      'descr':'a channel for Google Analytics, Google App Engine, and Search',
      'type':channel_const.CHANNEL_TYPE_TWITTER, 
      'login':'bryanspringer13', 
      'passwd':conf.DEFAULT_PASSWD, 
      'keywords':['Google Analytics','GA', 'Google App Engine', 'Search'],
      'chid':'Frank Parker Twitter',
      'avatarUrl':"http://a3.twimg.com/profile_images/405562529/www3-touch-icon_normal_normal.png",
      'errorOnExisting':False
     },
     {'name':'bryanspringer14',
      'descr':'a channel for Google Analytics, Google App Engine, and Search',
      'type':channel_const.CHANNEL_TYPE_TWITTER, 
      'login':'bryanspringer14', 
      'passwd':conf.DEFAULT_PASSWD, 
      'keywords':['Google Analytics','GA', 'Google App Engine', 'Search'],
      'chid':'Grocery Salmon Twitter',
      'avatarUrl':"http://a3.twimg.com/profile_images/405562529/www3-touch-icon_normal_normal.png",
      'errorOnExisting':False
     },
     {'name':'bryanspringer15',
      'descr':'a channel for Google Analytics, Google App Engine, and Search',
      'type':channel_const.CHANNEL_TYPE_TWITTER, 
      'login':'bryanspringer15', 
      'passwd':conf.DEFAULT_PASSWD, 
      'keywords':['Google Analytics','GA', 'Google App Engine', 'Search'],
      'chid':'Heather Adams Twitter',
      'avatarUrl':"http://a3.twimg.com/profile_images/405562529/www3-touch-icon_normal_normal.png",
      'errorOnExisting':False
     },
     {'name':'bryanspringer16',
      'descr':'a channel for Google Analytics, Google App Engine, and Search',
      'type':channel_const.CHANNEL_TYPE_TWITTER, 
      'login':'bryanspringer16', 
      'passwd':conf.DEFAULT_PASSWD, 
      'keywords':['Google Analytics','GA', 'Google App Engine', 'Search'],
      'chid':'Bryan Springer Twitter',
      'avatarUrl':"http://a3.twimg.com/profile_images/405562529/www3-touch-icon_normal_normal.png",
      'errorOnExisting':False
     },
     {'name':'bryanspringer17',
      'descr':'a channel for Google Analytics, Google App Engine, and Search',
      'type':channel_const.CHANNEL_TYPE_TWITTER, 
      'login':'bryanspringer17', 
      'passwd':conf.DEFAULT_PASSWD, 
      'keywords':['Google Analytics','GA', 'Google App Engine', 'Search'],
      'chid':'Chris Helleman Twitter',
      'avatarUrl':"http://a3.twimg.com/profile_images/405562529/www3-touch-icon_normal_normal.png",
      'errorOnExisting':False
     },
     {'name':'bryanspringer18',
      'descr':'a channel for Google Analytics, Google App Engine, and Search',
      'type':channel_const.CHANNEL_TYPE_TWITTER, 
      'login':'bryanspringer18', 
      'passwd':conf.DEFAULT_PASSWD, 
      'keywords':['Google Analytics','GA', 'Google App Engine', 'Search'],
      'chid':'Darren Barefoot Twitter',
      'avatarUrl':"http://a3.twimg.com/profile_images/405562529/www3-touch-icon_normal_normal.png",
      'errorOnExisting':False
     },    
    ]

CHANNEL_MAP = {}
for item in CHANNELS :
    CHANNEL_MAP[item['chid']] = item 

ARTICLES = [
     {'name':'Twitter Trends', 
      'msg':'Latest Twitter trends.', 
      'url':'http://search.twitter.com/trends.json', 
      'keywords':['trend', 'twitter']
     },
     {'name':'Yao Ming Wikipedia', 
      'msg':'Updated wikipedia page about Yao Ming', 
      'url':'http://en.wikipedia.org/wiki/Yao_Ming', 
      'keywords':['Yao Ming', 'NBA', 'NBA All-star']
     },
     {'name':'Google App Engine Doc', 
      'msg':'Getting started with Google App Engine using Python', 
      'url':'http://code.google.com/appengine/docs/python/gettingstarted/', 
      'keywords':['Google App Engine','Python']
     },
    ]

ARTICLE_MAP = {}
for item in ARTICLES :
    ARTICLE_MAP[item['name']] = item 

FEEDS = [
     {'name':'SNS Analytics', 
      'descr':'Official blog of SNS Analytics, Inc', 
      'url':'http://blog.snsanalytics.com', 
      'feedurl':'http://everyonedeserves.me/?feed=rss2', 
      'keywords':['SNS', 'SNS Analytics', 'Social Marketing', 'Twitter Marketing'],
      'errorOnExisting':False
     },
     {'name':'TechCrunch', 
      'descr':'high tech news from TechCrunch', 
      'url':'http://feeds.feedburner.com/Techcrunch', 
      'feedurl':'http://feeds.feedburner.com/Techcrunch', 
      'keywords':['SNS', 'feedburner'],
      'errorOnExisting':False
     },
     {'name':'Mashable!', 
      'descr':'high tech news from Mashable!', 
      'url':'http://feeds2.feedburner.com/Mashable', 
      'feedurl':'http://feeds2.feedburner.com/Mashable', 
      'keywords':['SNS','Mashable'],
      'errorOnExisting':False
     },
     {'name':'Google Analytics Blog', 
      'url':'http://analytics.blogspot.com/feeds/posts/default', 
      'feedurl':'http://analytics.blogspot.com/feeds/posts/default', 
      'keywords':['Google Analytics','GA', 'Web Analytics'],
      'errorOnExisting':False
     },
     {'name':'Google App Engine Blog', 
      'url':'http://googleappengine.blogspot.com/feeds/posts/default', 
      'feedurl':'http://googleappengine.blogspot.com/feeds/posts/default', 
      'keywords':['Google App Engine','GAE', 'Cloud Computing', 'Python'],
      'errorOnExisting':False
     },
    ]

FEED_MAP = {}
for item in FEEDS :
    FEED_MAP[item['name']] = item 

ARTICLE_POSTING_RULES = [
     {'name':'Twitter Trends One Time', 
      'descr':'good to test trend words, and also keywords',
      'channels':['Bryan Springer Twitter', 'Chris Helleman Twitter', 'Darren Barefoot Twitter'],
      'subchannels':[0,0,0],
      'contents':['Twitter Trends'],
      'keywords':['Twitter', 'Twitter.com'],
     },
     {'name':'Google App Engine Doc One Time Scheduled', 
      'channels':['Frank Parker Twitter', 'Grocery Salmon Twitter', 'Heather Adams Twitter'],
      'subchannels':[0, 0, 0],
      'scheduleType':camp_const.SCHEDULE_TYPE_ONE_TIME,
      'scheduleStart':str(datetime.datetime.utcnow() + datetime.timedelta(minutes=1)),
      'contents':['Google App Engine Doc'],
      'keywords':['Google App Engine','GAE'],
      'rt':False,
      'followTrend':False,
     },
     {'name':'Yao Ming Recurring 1 Hour', 
      'descr':'one-time, multiple static article URLs',
      'channels':['Bryan Springer Twitter', 'Chris Helleman Twitter', 'Darren Barefoot Twitter'],
      'subchannels':[0, 0, 0],
      'scheduleType':camp_const.SCHEDULE_TYPE_RECURRING,
      'scheduleInterval':camp_const.SCHEDULE_ARTICLE_POSTING_INTERVALS[0],
      'contents':['Yao Ming Wikipedia'],
      'keywords':['Yao Ming','Analytics'],
      'rt':False,
      'followTrend':False,
     },
     {'name':'Google App Engine Doc 15 min recurring', 
      'descr':'recurring multiple static article URLs',
      'channels':['Frank Parker Twitter', 'Grocery Salmon Twitter', 'Heather Adams Twitter'],
      'subchannels':[0, 0, 0],
      'scheduleType':camp_const.SCHEDULE_TYPE_RECURRING,
      'scheduleStart':str(datetime.datetime.utcnow() + datetime.timedelta(minutes=1)), # 1 minutes later
      'scheduleEnd':str(datetime.datetime.utcnow() + datetime.timedelta(1)), # 1 day later
      'scheduleInterval':camp_const.SCHEDULE_ARTICLE_POSTING_INTERVALS[0],
      'contents':['Google App Engine Doc'],
      'keywords':['Google','Python'],
     },
    ]

ARTICLE_POSTING_RULE_MAP = {}
for item in ARTICLE_POSTING_RULES :
    ARTICLE_POSTING_RULE_MAP[item['name']] = item 

FEED_POSTING_RULES = [
     {'name':'High Tech News',
      'descr':'Publish contents aggregated through TechCrunch, Mashable, ans SNS Analytics!',
      'channels':['Frank Parker Twitter', 'Grocery Salmon Twitter', 'Heather Adams Twitter'],
      'subchannels':[0, 0, 0],
      'scheduleType':camp_const.SCHEDULE_TYPE_RECURRING,
      'scheduleInterval':camp_const.SCHEDULE_FEED_POSTING_INTERVALS[0],
      'contents':['TechCrunch', 'Mashable!', 'SNS Analytics'],
      'keywords':['SNS','Social Network', 'Android', 'Twitter'],
      'msgPrefix':'#technews',
      'maxMessagePerFeed':5,
     },
     {'name':'Official Blogs of Google Analytics and Google App Engine', 
      'descr':'Timely publishing of Googla Analytics and Google App Engine blogs, to snsanalytics.com test channels',
      'channels':['Bryan Springer Twitter', 'Chris Helleman Twitter', 'Darren Barefoot Twitter'],
      'subchannels':[0, 0, 0],
      'scheduleType':camp_const.SCHEDULE_TYPE_RECURRING,
      'scheduleInterval':camp_const.SCHEDULE_FEED_POSTING_INTERVALS[0],
      'contents':['Google Analytics Blog', 'Google App Engine Blog'],
      'keywords':['Google Analytics','GA', 'Web Analytics', 'Google App Engine','GAE', 'Cloud Computing', 'Python'],
      'rt':False,
      'followTrend':False,
     },
    ]

FEED_POSTING_RULE_MAP = {}
for item in FEED_POSTING_RULES :
    FEED_POSTING_RULE_MAP[item['name']] = item 

def getHost() :
    return 'http://%s' % apiclient.server_domain()

def getChan(name=None):
    if name is not None :
        return copy.deepcopy(CHANNEL_MAP[name])    

    return copy.deepcopy(CHANNELS[0])

def getChans():
    return copy.deepcopy(CHANNELS)

def getMessage(name=None):
    if name is not None :
        return copy.deepcopy(ARTICLE_MAP[name])    

    return copy.deepcopy(ARTICLES[0])

def getMessages():
    return copy.deepcopy(ARTICLES)

def getRssfeed(name=None):
    if name is not None :
        return copy.deepcopy(FEED_MAP[name])    

    return copy.deepcopy(FEEDS[0])

def getRssfeeds():
    return copy.deepcopy(FEEDS)

def getPostRuleArticle(name=None):
    if name is not None :
        return copy.deepcopy(ARTICLE_POSTING_RULE_MAP[name])    

    return copy.deepcopy(ARTICLE_POSTING_RULES[0])

def getPostRuleArticles():
    return copy.deepcopy(ARTICLE_POSTING_RULES)    

def getPostRuleFeed(name=None):
    if name is not None :
        return copy.deepcopy(FEED_POSTING_RULE_MAP[name])    

    return copy.deepcopy(FEED_POSTING_RULES[0])

def getPostRuleFeeds():
    return copy.deepcopy(FEED_POSTING_RULES)    

def getObject(moduleName, name=None):
    get_func = eval('get' + getModuleName(moduleName))
    return get_func(name)

def getObjects(moduleName, name=None):
    get_func = eval('get' + getModuleName(moduleName) + 's')
    return get_func()

def getModuleName(api_module_name):
    return ''.join([token[0].upper() + token[1:] for token in api_module_name.split('/')])
    