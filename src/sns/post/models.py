import urllib

from google.appengine.ext import db
from search import core as search

import context
from common.utils import consts as common_const
from common.content import feedfetcher
from sns import channels as prod_channels
from sns.core import core as db_core
from sns.core.base import SoftDeleteNamedBaseModelPoly
from sns.camp import consts as camp_const
from sns.camp.models import CampaignPolySmall, Execution, Post, Campaign
from sns.cont.models import ContentPoly, FeedFetchLog
from sns.chan import consts as channel_const
from sns.chan.models import BaseChannel, TAccount

class SCampaign(Campaign):
    number = db.IntegerProperty()
    revision = db.IntegerProperty(default=0)
    userHashCode = db.IntegerProperty()
    keywords = db.StringListProperty() 
    msgPrefix = db.StringProperty(default=None, indexed=False)
    msgSuffix = db.StringProperty(default=None, indexed=False)
    titleOnly = db.BooleanProperty(default=False)
    skipKeywordMatch = db.BooleanProperty(default=False)
    fbDestinations = db.StringListProperty(indexed=False)
    fbPostStyle = db.IntegerProperty(default=common_const.FACEBOOK_POST_TYPE_STANDARD, choices=common_const.FACEBOOK_POST_TYPE) 
    randomize = db.BooleanProperty(default=False)
    randomizeTimeWindow = db.IntegerProperty(default=0) 
    
    @classmethod
    def display_exclude_properties(cls) :
        return SoftDeleteNamedBaseModelPoly.display_exclude_properties() + ['skipKeywordMatch']


class StandardCampaignSmall(CampaignPolySmall):
    pass


class BMCampaign(SCampaign):
    fbName = db.StringProperty(indexed=False)
    fbLink = db.StringProperty(indexed=False)
    fbCaption = db.StringProperty(indexed=False)
    fbPicture = db.StringProperty(indexed=False)
    fbDescription = db.TextProperty()

    
class BaseMessageCampaignSmall(StandardCampaignSmall):
    pass

    
class MCampaign(BMCampaign):
    searchIndex = search.SearchIndexProperty(('name',), indexer=search.porter_stemmer,relation_index=False)
  

class MessageCampaignSmall(BaseMessageCampaignSmall):
    pass

    
class QMCampaign(BMCampaign):
    def getScheduleType(self):
        return camp_const.SCHEDULE_TYPE_NOW 


class DirectMessageCampaignSmall(BaseMessageCampaignSmall):
    pass

    
class FCampaign(SCampaign):
    """ 
    The feed posting rule always check for updates by publishing date
    The last_checked list maintains a list of last checked timestamp for each feed in the feed posting rule. 
    If last_checked is None, the program will assume datetime(1900,1,1)
    """
    maxMessagePerFeed = db.IntegerProperty(default=1, choices=[1, 2, 3, 4, 5])    
    prefixTitle = db.BooleanProperty(default=False)
    prefixDelimter = db.StringProperty(indexed=False)
    suffixTitle = db.BooleanProperty(default=False)
    suffixDelimter = db.StringProperty(indexed=False)
    searchIndex = search.SearchIndexProperty(('name',), indexer=search.porter_stemmer,relation_index=False)
        
    def getScheduleType(self):
        return camp_const.SCHEDULE_TYPE_RECURRING 
    
    def normalizedLastChecked(self):
        posting = SExecution.all().order('-executionTime').ancestor(self).fetch(limit=1)
        if len(posting) > 0:
            return posting[0].executionTime
        else:
            return None
        
    def truncateMsg(self, msg):
        if self.prefixTitle:
            prefixes=self.prefixDelimter
            if prefixes:
                prefixes = prefixes.split('SubstituteSymbol')
                for prefix in prefixes:
                    msg = feedfetcher.feed_message_prefix_strip(msg, prefix)
        if self.suffixTitle:
            suffixes=self.suffixDelimter
            if suffixes:
                suffixes = suffixes.split('SubstituteSymbol')
                for suffix in suffixes:
                    msg = feedfetcher.feed_message_suffix_strip(msg, suffix)
        return msg

    def has_valid_channel(self, user=None):
        if user and not user.isContent:
            return False
        if len(self.channels)!=1:
            return False
        channel = db_core.normalize_2_model(self.channels[0])
        if not isinstance(channel, TAccount):
            return False
        if context.get_context().is_primary_app() and not prod_channels.is_prod_channel(channel.chid):
            return False
        if len(channel.topics)==0 or channel.cmpFeedCampaign is None:
            return False
        return db_core.normalize_2_id(channel.cmpFeedCampaign)==self.id
 
 
class FeedCampaignSmall(StandardCampaignSmall):
    pass

    
class SExecution(Execution):
    """
    total - total number of posts in this execution
    failure - number of failures
    """
    total = db.IntegerProperty(indexed=False)
    failure = db.IntegerProperty(indexed=False)
    revision = db.IntegerProperty()
    
    @classmethod
    def keyNamePrefix(cls):
        return "SExecution:"
         

class SPost(Post):
    userHashCode = db.IntegerProperty()
    type = db.IntegerProperty(indexed=False)
    revision = db.IntegerProperty()
    channel = db.ReferenceProperty(BaseChannel)
    content = db.ReferenceProperty(ContentPoly, collection_name='posts')
    wallId = db.StringProperty(indexed=False)
    tweetId = db.StringProperty(indexed=False)
    feedId = db.StringProperty(indexed=False)
    msg = db.TextProperty()
    origMsg = db.TextProperty()
    scheduleNext = db.DateTimeProperty()
    
    @classmethod
    def keyNamePrefix(cls):
        return "SPost:"
   
    def count_hashtags(self):
        if self.msg is None:
            return 0
        words = self.msg.split(' ')
        return len(filter(lambda word: word.startswith('#'), words))
        
    def get_channel(self):
        try:
            return self.channel
        except:
            return None
    
    @property    
    def chid(self):
        try:
            return self.channel.chid_int()
        except:
            return None

    def content_str(self):
        return "%s %s %s %s" % (self.key().id_or_name(), self.urlHash, self.msg, self.url,)
        
    def getTweetUrl(self):
        if self.tweetId:
            if self.channel.type == channel_const.CHANNEL_TYPE_TWITTER:
                return "/".join(("http://twitter.com",self.channel.login(),"status",self.tweetId))
            elif self.channel.type == channel_const.CHANNEL_TYPE_FACEBOOK_ACCOUNT:
                if self.wallId == 'me':
                    url = self.channel.profileUrl
                else:
                    url = 'http://www.facebook.com/group.php?gid='+self.wallId
                    pages=self.channel.pages
                    for page in pages:
                        if page.find(self.wallId)!=-1:
                            page_name=page.split(":")[0]
                            page_name=urllib.unquote(page_name)
                            url = 'http://www.facebook.com/pages/'+page_name.replace(' ','-')+'/'+self.wallId
                            break
                if url.find('?') == -1:
                    return url+'?v=wall&story_fbid='+self.tweetId
                else:
                    return url+'&v=wall&story_fbid='+self.tweetId
            elif self.channel.type == channel_const.CHANNEL_TYPE_FACEBOOK_PAGE or self.channel.type == channel_const.CHANNEL_TYPE_FACEBOOK_APP:
                url = self.channel.url
                if url.find('?') == -1:
                    return url+'?v=wall&story_fbid='+self.tweetId
                else:
                    return url+'&v=wall&story_fbid='+self.tweetId


class FeedPostLog(FeedFetchLog):
    failEntries=db.StringListProperty(indexed=False)
    
    @classmethod
    def keyNamePrefix(cls):
        return "FeedPostLog:"

    @classmethod
    def key_name_by_feed_id(cls, fid):
        return cls.keyName("Feed:%s" % fid)

    @classmethod
    def key_name_by_feed_source_topic(cls, topic, feedSource):
        return cls.keyName("Topic:%s:FeedSource:%s" % (topic, feedSource))

    @classmethod
    def get_or_insert_by_feed_campaign(cls, feed, rule):
        logKeyName = cls.key_name_by_feed_id(feed.key().id())
        return cls.get_or_insert(logKeyName, parent=rule)

    @classmethod
    def get_or_insert_by_feed_source(cls, topic, feedSource):
        logKeyName = cls.key_name_by_feed_source_topic(topic.keyNameStrip(), str(feedSource))
        return cls.get_or_insert(logKeyName)



        
                