from sets import Set
import datetime
import logging

from google.appengine.ext import db
from search import core as search
from twitter.api import TwitterApi
from twitter import errors as twitter_error
from twitter.oauth import TwitterOAuthAccessToken

from common.utils import string as str_util
from sns.core.core import KeyName, ChannelParent
from sns.core.base import SoftDeleteNamedBaseModel, ClickCounterNoIndex, DatedBaseModel
from sns.chan import consts as channel_const
from sns.mgmt.models import ContentCampaign


class ChannelKeyName(KeyName):
    @classmethod
    def keyNamePrefix(cls):
        return "Channel:"

    @classmethod
    def normalizedName(cls, name):
        return str_util.strip(name.lower())


class BaseChannel(SoftDeleteNamedBaseModel, ChannelKeyName):
    chid = db.StringProperty()
    avatarUrl = db.StringProperty(indexed=False)
    state = db.IntegerProperty(default=channel_const.CHANNEL_STATE_NORMAL, choices=channel_const.CHANNEL_STATES, required=True)
    errorCount = db.IntegerProperty(required=True, default=0)
    suspendedTime = db.DateTimeProperty()
    restoredTime = db.DateTimeProperty()
    isRestored = db.BooleanProperty(default=False)
    type = db.IntegerProperty(required=True, default=channel_const.CHANNEL_TYPE_TWITTER)
    
    def className(self):
        return self.__class__.__name__

    def oid(self):
        return self.key().name().split(':')[1]
    
    @classmethod
    def get_user_channels(cls, user, cmp_required=True, skip_suspended=True):
        if cmp_required and not user.isContent:
            return []
        channels = cls.all().ancestor(ChannelParent.get_or_insert_parent(uid=user.uid)).filter('deleted', False).fetch(limit=1000)
        if skip_suspended:
            return filter(lambda channel: channel.state == channel_const.CHANNEL_STATE_NORMAL, channels)
        else:
            return channels
    
    def mark_suspended(self, time=datetime.datetime.utcnow()):
        logging.error("Marking account %s as suspended after %d consecutive access errors." % (self.chid_handle_str(), self.errorCount))
        self.errorCount = 0
        self.state = channel_const.CHANNEL_STATE_SUSPENDED
        self.suspendedTime = time 
        return self

    def mark_restored(self, time=datetime.datetime.utcnow()):
        self.errorCount = 0
        self.state = channel_const.CHANNEL_STATE_NORMAL
        self.restoredTime = datetime.datetime.utcnow()
        self.isRestored = True
        logging.info("Marking account %s as restored." % self.chid_handle_str())

    def chid_int(self):
        return int(self.keyNameStrip())
    
    def chid_str(self):
        return self.keyNameStrip()

    def chid_handle_str(self):
        return "%s@%s" % (self.keyNameStrip(), self.name)
    
    def chid_handle_uid_str(self):
        return "%s@%s/%s" % (self.keyNameStrip(), self.name, self.uid())
    
    def uid(self):
        try:
            return self.parent().uid
        except:
            logging.exception("Channel %s has invalid parent!" % self.chid_handle_str())
            return None
        
        
class TAccountKeyName(ChannelKeyName):
    @classmethod
    def keyNamePrefix(cls):
        return "Twitter:"
    

class TAccount(BaseChannel, TAccountKeyName):
    isContent = db.BooleanProperty(default=False)
    topics = db.StringListProperty()
    keyword = db.StringProperty()
    contentCampaign = db.ReferenceProperty(ContentCampaign)
    cmpFeedCampaign = db.ReferenceProperty(collection_name='cmp_feed_camp_taccount_set', indexed=False)
    advancedDMCampaign = db.StringProperty(indexed=False)
    userEmail = db.StringProperty()
    oauthAccessToken = db.ReferenceProperty(TwitterOAuthAccessToken, indexed=False)
    accountName = db.TextProperty()
    accountUrl = db.TextProperty()
    acctCreatedTime = db.DateTimeProperty()
    location = db.TextProperty()
    description = db.TextProperty()
    backGround = db.TextProperty()
    searchIndex = search.SearchIndexProperty(('name',), indexer=search.porter_stemmer,relation_index=False)
    
    def login(self):
        return self.name
    
    def get_twitter_api(self):
        return TwitterApi(oauth_access_token=self.oauthAccessToken)

    @classmethod
    def getAccountType(cls):
        return 'Twitter'

    @classmethod
    def get_by_chid_uid(cls, chid, uid):
        key_name = TAccountKeyName.keyName(str(chid))
        parent = ChannelParent.get_or_insert_parent(uid=uid)
        return cls.get_by_key_name(key_name, parent=parent)
        
    def syncState(self, retry=1):
        try:
            tapi = self.get_twitter_api()
            profile = tapi.account.update_profile(skip_status=False)
            logging.debug("syncState() profile: %s" % profile)
            if self.state==channel_const.CHANNEL_STATE_SUSPENDED:
                try:
                    self.avatarUrl = profile["profile_image_url"]
                    self.name = profile['screen_name']
                    self.mark_restored()
                    self.put()
                except:
                    logging.exception("Unexpected exception when marking channel '%s' as restored:" % self.name)
        except Exception, ex:
            if twitter_error.isTemporaryError(ex):
                if retry<3:
                    return self.syncState(retry+1)
                else:
                    logging.exception("%d times temporary errors when syncing status for channel '%s':" % (retry, self.name))
                    return self.state
            if self.state==channel_const.CHANNEL_STATE_NORMAL:
                try:
                    if twitter_error.isSuspended(ex):
                        self.mark_suspended()
                        self.put()
                    elif twitter_error.isRateLimitExceeded(ex):
                        self.errorCount += 1
                        if self.errorCount>=5:
                            self.mark_suspended()
                        self.put()
                    else:
                        logging.exception("Unexpected exception when synchronizing state for channel '%s':" % self.name)
                except:
                    logging.exception("Unexpected exception when marking channel '%s' as suspended:" % self.name)
        return self.state


class FAccount(BaseChannel): 
    groups = db.StringListProperty(indexed=False)
    pages = db.StringListProperty(indexed=False)
    excludedGroups = db.StringListProperty(indexed=False)
    excludedPages = db.StringListProperty(indexed=False)
    profileUrl = db.StringProperty(required=True, indexed=False)
    managePages = db.BooleanProperty(required=True, default=False)
    oauthAccessToken = db.StringProperty(required=True, indexed=False)  
    searchIndex = search.SearchIndexProperty(('name',), indexer=search.porter_stemmer,relation_index=False)
    
    @classmethod
    def keyNamePrefix(cls):
        return "Facebook:"

    @classmethod
    def uniqueness_properties(cls) :
        return []
    
    @classmethod
    def getAccountType(cls):
        return 'Facebook'
    
    def getStripGroup(self):
        g = []
        for s in self.groups:
            index = s.find(':')
            g.append(s[index+1:])
        return g
    
    def getStripExcludedGroup(self):
        g = []
        for s in self.excludedGroups:
            index = s.find(':')
            g.append(s[index+1:])
        return g

    
    def getStripPage(self):
        g = []
        for s in self.pages:
            index = s.find(':')
            g.append(s[index+1:])
        return g

    def getStripExcludedPage(self):
        g = []
        for s in self.excludedPages:
            index = s.find(':')
            g.append(s[index+1:])
        return g


class FPage(BaseChannel):
    pageid = db.StringProperty(required=True)
    url = db.StringProperty(indexed=False)
    excluded = db.BooleanProperty(required=True,default=False)
    searchIndex = search.SearchIndexProperty(('name',), indexer=search.porter_stemmer,relation_index=False)
    
    @classmethod
    def keyNamePrefix(cls):
        return "FacebookPageFan:"
    
    @classmethod
    def uniqueness_properties(cls) :
        return []
    

class FGroup(BaseChannel):
    groupid = db.StringProperty(required=True, indexed=False)
    url = db.StringProperty(indexed=False)
    excluded = db.BooleanProperty(required=True,default=False)
    searchIndex = search.SearchIndexProperty(('name',), indexer=search.porter_stemmer,relation_index=False)
    
    @classmethod
    def keyNamePrefix(cls):
        return "FacebookGroupMember:"
    
    @classmethod
    def uniqueness_properties(cls) :
        return []

    
class FAdminPage(BaseChannel):
    pageid = db.StringProperty(required=True)
    url = db.StringProperty(indexed=False)
    oauthAccessToken = db.StringProperty(indexed=False)
    category = db.StringProperty(default='WebSites')
    searchIndex = search.SearchIndexProperty(('name',), indexer=search.porter_stemmer,relation_index=False)
    
    @classmethod
    def keyNamePrefix(cls):
        return "FacebookPageAdmin:"
    
    @classmethod
    def uniqueness_properties(cls) :
        return []
    
    @classmethod
    def getAccountType(cls):
        return 'Facebook Page'


class ChannelClickCounter(ClickCounterNoIndex):
    pass


class ChannelHourlyKeyName(KeyName):
    @classmethod
    def keyNamePrefix(cls):
        return "twitter_hourly:"

    @classmethod
    def normalizedName(cls, name, t=datetime.datetime.utcnow()):
        return str_util.strip("%s_%s_%s_%s_%s" % (name.lower(), t.year, t.month, t.day, t.hour))

    @classmethod
    def keyName(cls, name, t=datetime.datetime.utcnow()):
        return "%s%s" % (cls.keyNamePrefix(), cls.normalizedName(name, t))
    
class ChannelDailyKeyName(ChannelHourlyKeyName):
    @classmethod
    def keyNamePrefix(cls):
        return "twitter_daily:"

    @classmethod
    def normalizedName(cls, name, t=datetime.datetime.utcnow()):
        return str_util.strip("%s_%s_%s_%s" % (name.lower(), t.year, t.month, t.day))
    
class FriendList(DatedBaseModel):
    """ username - Twitter or other SN account user name """
    """ friends - value is like "Set(['login1','login2',...])" """
    username = db.StringProperty(required=True)
    friends = db.TextProperty() 

    def getFriends(self):
        if self.friends is None :
            return Set()
        else :
            return eval(self.friends)

    def addFriends(self, newFriends):
        """ newFriends - iterable of strings """
        existingFriends = self.getFriends()
        existingFriends.update(newFriends)
        self.friends = str(existingFriends)
        
    def replaceFriends(self, newFriends):
        self.friends = str(newFriends)
        
    def reverse(self):
        friendList = list(self.getFriends())
        friendList.reverse()
        self.friends = str(Set(friendList))
        
    def count(self):
        return len(self.getFriends())
    
class HourlySendList(FriendList, ChannelHourlyKeyName):
    overSendLimit = db.BooleanProperty(required=True, default=False,indexed=False)

class HourlySendStats(DatedBaseModel, ChannelHourlyKeyName):
    username = db.StringProperty()
    sendCount = db.IntegerProperty(required=True, default=0,indexed=False)
    failCount = db.IntegerProperty(required=True, default=0,indexed=False)
    
class DailySendStats(DatedBaseModel, ChannelDailyKeyName):
    username = db.StringProperty()
    sendCount = db.IntegerProperty(required=True, default=0,indexed=False)


