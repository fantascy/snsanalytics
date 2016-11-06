from google.appengine.ext import db
from search import core as search

from twitter import oauth

from common import consts as common_const
from common.utils import string as str_util, url as url_util
from sns.core import consts as core_const
from sns.core.base import BaseModel, DateIF, NameIF, DateNoIndexIF, StatsCounterIF, HourlyStatsCounterIF, HourlyStatsIF, DailyStatsCounterIF, DailyStatsIF
from sns.core.core import KeyName, ChidKey
from sns.chan import consts as channel_const
from sns.cont.models import Topic


class ChannelTopicStatsCounterCommonIF(DailyStatsCounterIF):
    """
    Each text attr is in this format: "((year,month,day),[count1,count2,count3,...])", using US/Pacific time zone.
    """
    postCounts = db.TextProperty()  
    clickCounts = db.TextProperty()  
    followerCounts = db.TextProperty()
    retweetCounts = db.TextProperty()
    mentionCounts = db.TextProperty()
    hashtagCounts = db.TextProperty()

    def setPostCount(self, count, date):
        self.setCount('postCounts', count, date, padding=DailyStatsCounterIF.PADDING_ZERO)
    
    def setClickCount(self, count, date):
        self.setCount('clickCounts', count, date, padding=DailyStatsCounterIF.PADDING_ZERO)
    
    def setFollowerCount(self, count, date):
        self.setCount('followerCounts', count, date, padding=DailyStatsCounterIF.PADDING_OLD_VALUE)
    
    def setRetweetCount(self, count, date):
        self.setCount('retweetCounts', count, date, padding=DailyStatsCounterIF.PADDING_ZERO)
    
    def setMentionCount(self, count, date):
        self.setCount('mentionCounts', count, date, padding=DailyStatsCounterIF.PADDING_ZERO)
    
    def setHashtagCount(self, count, date):
        self.setCount('hashtagCounts', count, date, padding=DailyStatsCounterIF.PADDING_ZERO)
    
    def getPostCounts(self):
        return self.getCounts('postCounts')
    
    def getClickCounts(self):
        return self.getCounts('clickCounts')
    
    def getFollowCounts(self):
        return self.getCounts('followCounts')
    
    def getRetweetCounts(self):
        return self.getCounts('retweetCounts')
    
    def getMentionCounts(self):
        return self.getCounts('mentionCounts')
    
    def getHashtagCounts(self):
        return self.getCounts('hashtagCounts')
    
    def totalPosts(self, days=30):
        return self.totalCounts('postCounts', days)
    
    def totalClicks(self, days=30):
        return self.totalCounts('clickCounts', days)
    
    def totalRetweets(self, days=30):
        return self.totalCounts('retweetCounts', days)
    
    def totalMentions(self, days=30):
        return self.totalCounts('mentionCounts', days)
    
    def totalHashtags(self, days=30):
        return self.totalCounts('hashtagCounts', days)
            

class CmpTwitterAcctStatsCounter(ChannelTopicStatsCounterCommonIF):
    kloutScores = db.TextProperty()
    searchRanks = db.TextProperty()

    @property
    def chid(self):
        return int(self.key().name())
    
    def setKloutScore(self, count, date):
        self.setCount('kloutScores', count, date, padding=DailyStatsCounterIF.PADDING_OLD_VALUE)
    
    def setSearchRank(self, count, date):
        self.setCount('searchRanks', count, date, padding=DailyStatsCounterIF.PADDING_OLD_VALUE)
    
    def getKloutScores(self):
        return self.getCounts('kloutScores')
    
    def getSearchRanks(self):
        return self.getCounts('searchRanks')

    @classmethod
    def real_klout_scores(cls, intScores):
        if intScores is None:
            return None
        return [1.0*score/100 for score in intScores] 
    

class TopicStatsCounter(ChannelTopicStatsCounterCommonIF):
    channelCounts = db.TextProperty()  

    @classmethod
    def keyNamePrefix(cls):
        return "TopicStatsCounter:"
    
    @classmethod
    def get_or_insert_by_topic_key(cls, topic_key):
        return cls.get_or_insert(cls.keyName(topic_key))
    
    def reset(self):
        pass
    
    def setChannelCount(self, count, date):
        self.setCount('channelCounts', count, date, padding=DailyStatsCounterIF.PADDING_ZERO)
    
    def getChannelCounts(self):
        return self.getCounts('channelCounts')


class ChannelTopicStatsCommonIF(DailyStatsIF):
    latelyPost = db.IntegerProperty(default=0)
    latelyClick = db.IntegerProperty(default=0)
    latelyFollower = db.IntegerProperty(default=0)
    retweets = db.IntegerProperty(default=0)
    mentions = db.IntegerProperty(default=0)
    hashtags = db.IntegerProperty(default=0)
    totalPost = db.IntegerProperty(default=0)
    totalClick = db.IntegerProperty(default=0)
    totalRetweets = db.IntegerProperty(default=0)
    totalMentions = db.IntegerProperty(default=0)
    totalHashtags = db.IntegerProperty(default=0)

    def reset(self):
        DailyStatsIF.reset(self)
        self.latelyPost = 0
        self.latelyClick = 0
#        self.latelyFollower = self.latelyFollower
        self.retweets = 0
        self.mentions = 0
        self.hashtags = 0
        self.totalPost = 0
        self.totalClick = 0
        self.totalRetweets = 0
        self.totalMentions = 0
        self.totalHashtags = 0
        
    @classmethod
    def counter_model(cls):
        pass
    
    def get_or_insert_counter(self):
        return self.counter_model().get_or_insert(self.key().name(), parent=self)
    

class CmpTwitterAcctStats(ChannelTopicStatsCommonIF, NameIF, ChidKey):
    ERROR_FE_CAMPAIGN_STATE_INCORRECT = 1
    ERROR_CHANNEL_NO_CMP_FEED_CAMPAIGN = 2
    ERROR_CHANNEL_FEED_CAMPAIGN_STATE_INCORRECT = 3
    ERROR_CHANNEL_TOPIC_NOT_EXIST = 4
    latestKloutScore = db.IntegerProperty(default=0)  
    topicInfo = db.StringProperty(indexed=False)
    ancestorTopics = db.StringListProperty()
    acctCreatedTime = db.DateTimeProperty()
    searchTerm = db.StringProperty(indexed=False)
    searchRank = db.IntegerProperty()
    searchRankModifiedTime = db.DateTimeProperty(default=common_const.EARLIEST_TIME)
    uid = db.IntegerProperty(indexed=False)
    userEmail = db.StringProperty(indexed=False)
    oauthAccessToken = db.ReferenceProperty(oauth.TwitterOAuthAccessToken, indexed=False)
    server = db.StringProperty()
    state = db.IntegerProperty(default=core_const.FOLLOW_STATS_INACTIVATED)
    chanState = db.IntegerProperty(default=channel_const.CHANNEL_STATE_NORMAL)
    errors = db.ListProperty(int)
    priority = db.IntegerProperty(default=0)
    feUserEmail = db.StringProperty(indexed=False)
    feCampaign = db.StringProperty(indexed=False)
    feCampaignId = db.IntegerProperty(indexed=False)
    feModifiedTime = db.DateTimeProperty(default=common_const.EARLIEST_TIME)
    searchIndex = search.SearchIndexProperty(('name',), indexer=search.porter_stemmer, relation_index=False)

    @classmethod
    def counter_model(cls):
        return CmpTwitterAcctStatsCounter
    
    @classmethod
    def get_by_name(cls, name):
        results = cls.all().filter('nameLower', str_util.lower(name)).fetch(limit=1)
        return results[0] if results else None

    @classmethod
    def get_or_insert_by_channel(cls, channel):
        return cls.get_or_insert(key_name=channel.chid_str(), name=channel.name, nameLower=str_util.lower(channel.name))

    def reset(self):
        ChannelTopicStatsCommonIF.reset(self)
#        self.latestKloutScore = self.latestKloutScore
#        self.searchRank = self.searchRank
        
    def syncFeStateError(self):
        if self.state==core_const.FOLLOW_RULE_STATE_SUSPEND and self.chanState==channel_const.CHANNEL_STATE_NORMAL:
            return self.addError(CmpTwitterAcctStats.ERROR_FE_CAMPAIGN_STATE_INCORRECT)
        elif self.state!=core_const.FOLLOW_RULE_STATE_SUSPEND and self.chanState==channel_const.CHANNEL_STATE_SUSPENDED:
            return self.addError(CmpTwitterAcctStats.ERROR_CHANNEL_FEED_CAMPAIGN_STATE_INCORRECT)
        else:
            return self.removeError(CmpTwitterAcctStats.ERROR_CHANNEL_FEED_CAMPAIGN_STATE_INCORRECT)
        
    def addError(self, error):
        if error not in self.errors:
            self.errors.append(error)
            return True
        return False

    def removeError(self, error):
        if CmpTwitterAcctStats.ERROR_CHANNEL_FEED_CAMPAIGN_STATE_INCORRECT in self.errors:
            self.errors.remove(error)
            return True
        return False

    def realKloutScores(self):
        return [1.0*score/100 for score in self.kloutScores] 
    
    def realLatestKloutScore(self):
        if self.latestKloutScore is None:
            return None
        else:
            return 1.0*self.latestKloutScore/100 

    def topic_ancestors_changed(self, new_ancestors):
        if not self.ancestorTopics and not new_ancestors:
            return False
        if not self.ancestorTopics or not new_ancestors:
            return True
        new_ancestors.sort()
        if len(self.ancestorTopics) != len(new_ancestors):
            return True
        for i in xrange(len(new_ancestors)):
            if self.ancestorTopics[i] != new_ancestors[i]:
                return True
        return False
        
    def related_topic_keys(self):
        topic_info = eval(self.topicInfo) if self.topicInfo else []
        topic_keys = set([item[0] for item in topic_info])
        topic_keys.update(self.ancestorTopics)
        return topic_keys

    def first_topic_info(self):
        topic_info = eval(self.topicInfo) if self.topicInfo else []
        return topic_info[0] if topic_info else None
        
    def first_topic_key(self):
        topic_info = self.first_topic_info()
        return topic_info[0] if topic_info else None 

    def first_topic_name(self):
        topic_info = self.first_topic_info()
        return topic_info[1] if topic_info else None 

    def sync_search_term(self):
        topic_name = self.first_topic_name()
        new_search_term = Topic.canonical_name(topic_name) if topic_name else None
        if self.searchTerm == new_search_term:
            return False
        else:
            self.searchTerm = new_search_term
            return True

    def chid_handle_str(self):
        return "%d@%s" % (self.chid, self.name)


class TopicStats(ChannelTopicStatsCommonIF, KeyName):
    channels = db.IntegerProperty(default=0)  

    @classmethod
    def keyNamePrefix(cls):
        return "TopicStats:"
    
    @classmethod
    def get_or_insert_by_topic_key(cls, topic_key):
        return cls.get_or_insert(cls.keyName(topic_key))
    
    @classmethod
    def counter_model(cls):
        return TopicStatsCounter
    
    def reset(self):
        ChannelTopicStatsCommonIF.reset(self)
        self.channels = 0
        self.latelyFollower = 0

    def aggregate_one_cstats(self, cstats):
        self.channels += 1
        self.latelyFollower += cstats.latelyFollower
        self.latelyPost += cstats.latelyPost
        self.latelyClick += cstats.latelyClick
        self.retweets += cstats.retweets
        self.mentions += cstats.mentions
        self.hashtags += cstats.hashtags 
        self.totalPost += cstats.totalPost
        self.totalClick += cstats.totalClick
        self.totalRetweets += cstats.totalRetweets
        self.totalMentions += cstats.totalMentions
        self.totalHashtags += cstats.totalHashtags


class DomainStats(BaseModel, KeyName):
    @classmethod
    def keyNamePrefix(cls):
        return "DomainStats:"

    domain = db.StringProperty(required=True)
    clicks = db.IntegerProperty(default=0)  
    totalClicks = db.IntegerProperty(default=0)  
    searchIndex = search.SearchIndexProperty(('domain',), indexer=search.porter_stemmer, relation_index=False)

    def reset(self):
        self.clicks = 0
        self.totalClicks = 0
        
    @classmethod
    def get_or_insert_by_domain(cls, domain):
        domain = str_util.lower_strip(domain)
        return cls.get_or_insert(cls.keyName(domain), domain=domain)
    

class BaseContentSourceStatsCounter(db.Model):
    postCounts = db.TextProperty()  
    clickCounts = db.TextProperty()  

    def setPostCount(self, count, date):
        self.setCount('postCounts', count, date, padding=StatsCounterIF.PADDING_ZERO)
    
    def setClickCount(self, count, date):
        self.setCount('clickCounts', count, date, padding=StatsCounterIF.PADDING_ZERO)
    
    def getPostCounts(self):
        return self.getCounts('postCounts')
    
    def getClickCounts(self):
        return self.getCounts('clickCounts')
    
    def totalPosts(self, periods=None):
        if periods is None: periods = self.default_periods()
        return self.totalCounts('postCounts', periods)
    
    def totalClicks(self, periods=None):
        if periods is None: periods = self.default_periods()
        return self.totalCounts('clickCounts', periods)
    
    @classmethod
    def default_periods(cls):
        return cls.DEFAULT_PERIODS
    

class ContentSourceHourlyStatsCounter(BaseContentSourceStatsCounter, HourlyStatsCounterIF):
    pass
    

class ContentSourceDailyStatsCounter(BaseContentSourceStatsCounter, DailyStatsCounterIF):
    pass
    

class BaseContentSourceStats(db.Model, KeyName):
    posts = db.IntegerProperty(default=0)  
    clicks = db.IntegerProperty(default=0)  
    totalPosts = db.IntegerProperty(default=0)  
    totalClicks = db.IntegerProperty(default=0)  

    @classmethod
    def get_or_insert_by_name(cls, name):
        """ cs_name is typically a domain name, e.g., 'examiner.com'. It could be a publisher name as well."""
        return cls.get_or_insert(cls.keyName(str_util.lower_strip(name)))
    
    @classmethod
    def get_by_name(cls, name):
        return cls.get_by_key_name(cls.keyName(str_util.lower_strip(name)))
    
    @classmethod
    def get_or_insert_by_url(cls, url):
        return cls.get_or_insert_by_name(url_util.root_domain(url))
    
    @classmethod
    def counter_model(cls):
        pass
    
    def reset(self):
        self.posts = 0
        self.clicks = 0
        self.totalPosts = 0
        self.totalClicks = 0


class ContentSourceHourlyStats(BaseContentSourceStats, HourlyStatsIF):
    @classmethod
    def keyNamePrefix(cls):
        return "CSHStats:"
    
    @classmethod
    def counter_model(cls):
        return ContentSourceHourlyStatsCounter
    
    def reset(self):
        HourlyStatsIF.reset(self)
        BaseContentSourceStats.reset(self)


class ContentSourceDailyStats(BaseContentSourceStats, DailyStatsIF):
    @classmethod
    def keyNamePrefix(cls):
        return "CSDStats:"
    
    @classmethod
    def counter_model(cls):
        return ContentSourceDailyStatsCounter
    
    def reset(self):
        DailyStatsIF.reset(self)
        BaseContentSourceStats.reset(self)


class CmpTwitterAcctFollowers(DateNoIndexIF):
    followers = db.TextProperty()

    @classmethod
    def get_or_insert_by_chid(cls, chid):
        return cls.get_or_insert(str(chid))
            
    def getFollowers(self):
        if self.followers:
            return list(eval(self.followers))
        else:
            return []
    
    def setFollowers(self, followerList):
        self.followers = str(followerList)

    def size(self):
        return len(self.getFollowers())


class CmpTwitterAcctUniqueFollowerCount(DateIF):
    uniqueCount = db.IntegerProperty(required=True, indexed=False)
    totalCount = db.IntegerProperty(required=True, indexed=False)
    accountCounted = db.IntegerProperty(required=True, indexed=False)
    accountTotal = db.IntegerProperty(required=True, indexed=False)


class CmpDealTwitterAcctUniqueFollowerCount(CmpTwitterAcctUniqueFollowerCount):
    pass


class NoneCmpTwitterAcctFeStats(db.Model):
    modifiedTime = db.DateTimeProperty(auto_now=True)
    server = db.StringProperty()
    state = db.IntegerProperty()
    feCampaign = db.StringProperty()
    feUserEmail = db.StringProperty()
    feModifiedTime = db.DateTimeProperty()
    

class HourlyStats(HourlyStatsCounterIF, KeyName):
    info = db.TextProperty()  

    @classmethod
    def keyNamePrefix(cls):
        return "HourlyStats:"

    @classmethod
    def get_or_insert_by_id(cls, statsId):
        return cls.get_or_insert(cls.keyName(statsId))

    def set_counter_info(self, count, date):
        self.setCount('info', count, date, padding=StatsCounterIF.PADDING_ZERO)
    
    def get_counter_info(self):
        return self.getCounts('info')
    
    def set_non_counter_info(self, date, info=None):
        if info is None:
            info = []
        self.info = HourlyStats.text(date, info)


class GlobalStats(DailyStatsCounterIF, KeyName):
    info = db.TextProperty()  

    @classmethod
    def keyNamePrefix(cls):
        return "GlobalStats:"

    @classmethod
    def get_or_insert_by_id(cls, statsId):
        return cls.get_or_insert(cls.keyName(statsId))

    def set_counter_info(self, count, date):
        self.setCount('info', count, date, padding=StatsCounterIF.PADDING_ZERO)
    
    def get_counter_info(self):
        return self.getCounts('info')
    
    def set_non_counter_info(self, date, info=None):
        if info is None:
            info = []
        self.info = GlobalStats.text(date, info)


class BlackList(DateIF, KeyName):
    patternValue = db.TextProperty()

    @classmethod
    def keyNamePrefix(cls):
        return "BlackList:"
    

class Agent(DateIF, KeyName):
    ip = db.StringProperty()

    @classmethod
    def keyNamePrefix(cls):
        return "Agent:"
    
        
