from sets import Set

from google.appengine.ext import db
from twitter.oauth import TwitterOAuthAccessToken

import context
from sns.core.core import KeyName
from sns.cont.models import Topic
from sns.core.base import DatedBaseModel, SoftDeleteNamedBaseModelPoly, SoftDeleteNamedBaseModel
from sns.chan.models import TAccount, FAccount, FAdminPage
from sns.url.models import UrlKeyName
from soup import consts as soup_const


class BaseChannel(SoftDeleteNamedBaseModelPoly, KeyName):
    """
    uid - soup user id; self.oid() returns channel id
    """
    uid = db.IntegerProperty()
    username = db.StringProperty()
    firstName = db.StringProperty()
    lastName = db.StringProperty()
    bio = db.TextProperty()
    avatarUrl = db.StringProperty(indexed=False)
    timeZone  = db.StringProperty(indexed=False)
    
    def className(self):
        return self.__class__.__name__
    
    def oid(self):
        return int(self.key().name().split(':')[1])
    
    @classmethod
    def keyNamePrefix(cls):
        return "%s:" % cls.type()
    
    def url(self):
        pass
    
    @classmethod
    def get_or_insert_channel_by_id(cls, chid):
        channel = cls.get_by_key_name(cls.keyName(chid))
        if channel is None:
            if cls.type() == soup_const.USER_TYPE_TWITTER :
                ch = TAccount.all().filter('chid', str(chid)).fetch(limit=1)[0]
                channel = TChannel(key_name=cls.keyName(chid),avatarUrl=ch.avatarUrl,name=ch.name,nameLower=ch.nameLower,url="http://www.twitter.com/"+ch.name)
            elif cls.type() == soup_const.USER_TYPE_FACEBOOK:
                ch = FAccount.all().filter('chid', chid).fetch(limit=1)[0]
                channel = FChannel(key_name=cls.keyName(chid),avatarUrl=ch.avatarUrl,name=ch.name,nameLower=ch.nameLower,url=ch.profileUrl)
            elif cls.type() == soup_const.USER_TYPE_FACEBOOK_PAGE:
                ch = FAdminPage.all().filter('pageid', chid).fetch(limit=1)[0]
                channel = FPageChannel(key_name=cls.keyName(chid),avatarUrl=ch.avatarUrl,name=ch.name,nameLower=ch.nameLower,url=ch.url)
            channel.put()
        return channel
    

class TChannel(BaseChannel):
    oauthAccessToken = db.ReferenceProperty(TwitterOAuthAccessToken)
    
    @classmethod
    def type(cls):
        return soup_const.USER_TYPE_TWITTER

    def url(self):
        if self.username is not None:
            login = self.username
        else:
            login = self.name
        return "http://twitter.com/%s" % login
    

class FChannel(BaseChannel): 
    allFriends = db.TextProperty()
    invitedFriends = db.TextProperty()
    soupFriends = db.TextProperty()
    oauthAccessToken = db.StringProperty(indexed=False)  
    location = db.StringProperty()
    email = db.StringProperty()
    
    @classmethod
    def type(cls):
        return soup_const.USER_TYPE_FACEBOOK

    def url(self):
        return "http://facebook.com/profile.php?id=%s" % self.oid()
    
    def getFriends(self):
        if self.allFriends is None :
            return Set()
        else :
            return eval(self.allFriends)
        
    def getSoupFriends(self):
        if self.soupFriends is None :
            return Set()
        else :
            return eval(self.soupFriends)
        
    def getInvitedFriends(self):
        if self.invitedFriends is None :
            return Set()
        else :
            return eval(self.invitedFriends)
    

class FPageChannel(BaseChannel):
    pageUrl = db.StringProperty(indexed=False)
    oauthAccessToken = db.StringProperty(indexed=False)  
    
    @classmethod
    def type(cls):
        return soup_const.USER_TYPE_FACEBOOK_PAGE
    
    def url(self):
        return self.pageUrl


SOUP_CHANNEL_CLASS_MAP = {
    TAccount : TChannel,
    FAccount : FChannel,
    FAdminPage : FPageChannel,
    }


CHANNEL_ATTR_MAP = {
    TAccount : 'tChannel',
    FAccount : 'fChannel',
    FAdminPage : 'fpChannel',
    }
    
    
class SoupUser(SoftDeleteNamedBaseModel):
    email = db.StringProperty(required=True)
    username = db.StringProperty()
    firstName = db.StringProperty()
    lastName = db.StringProperty()
    bio = db.TextProperty()
    timeZone  = db.StringProperty(indexed=False)
    country = db.StringProperty()
    city = db.StringProperty()
    avatarUrl = db.StringProperty(indexed=False)
    tChannel = db.ReferenceProperty(TChannel)
    fChannel = db.ReferenceProperty(FChannel)
    fpChannel = db.ReferenceProperty(FPageChannel)
    
    @classmethod
    def get_or_insert_by_sns_channel(cls,channel):
        soup_cls = SOUP_CHANNEL_CLASS_MAP[channel.__class__]
        if soup_cls == FPageChannel:
            soup_channel = soup_cls.get_or_insert(soup_cls.keyName(channel.pageid),name=channel.name,nameLower=channel.nameLower,pageUrl=channel.url)
        else:
            soup_channel = soup_cls.get_or_insert(soup_cls.keyName(channel.chid),name=channel.name,nameLower=channel.nameLower)
        attr = CHANNEL_ATTR_MAP[channel.__class__]
        user = SoupUser.all().filter(attr, soup_channel).fetch(limit=1)
        if len(user) == 0:
            params = {}
            params[attr] = soup_channel
            params['name'] = channel.name
            params['nameLower'] = channel.nameLower
            params['avatarUrl'] = channel.avatarUrl
            params['email'] = channel.key().name()
            soupUser = SoupUser(**params)
            soupUser.put()
            return soupUser
        else:
            return user[0]
            
    def url(self):
        return "http://%s/profile/%s" % (context.get_context().long_domain(), self.oid())
        
    def fbChannel(self):
        """ For now, we assume one soup user cannot have both fChannel and fpChannel."""
        if self.fChannel is not None :
            return self.fChannel
        else :
            return self.fpChannel
        
    def getCountryTopic(self):
        topics = Topic.all().filter('name', self.country).fetch(limit=1)
        if len(topics) > 0:
            return topics[0]
        else:
            return None
        
    def getCounter(self):
        return SoupUserCounter.get_or_insert(SoupUserCounter.keyName(self.key().id()))
    
    def fbFriends(self):
        if self.fChannel is None:
            return Set()
        else:
            return self.fChannel.getFriends()
        
    def friends(self):
        if self.fChannel is None:
            return Set()
        else:
            return self.fChannel.getSoupFriends()

    def fbInvitedFriends(self):
        if self.fChannel is None:
            return Set()
        else :
            return self.fChannel.getInvitedFriends()
    
        
class SoupUserCounter(db.Model,KeyName):
    @classmethod
    def keyNamePrefix(cls):
        return "SoupUserCounter:" 
    
    ratingCount = db.IntegerProperty(default=0)
    postCount = db.IntegerProperty(default=0)
    commentCount = db.IntegerProperty(default=0)


class UserArticleRating(DatedBaseModel, UrlKeyName):
    """
    Each article rating object has the same keyname as corresponding global URL.
    All article rating objects of the same user share the same parent - the user object.
    urlKeyName - same as key name
    """
    urlKeyName = db.StringProperty(required=True)
    rating = db.IntegerProperty(choices=[1,2,3,4,5])



class UserArticleFollowing(DatedBaseModel, UrlKeyName):
    """
    Each article object has the same keyname as corresponding global URL.
    All article objects of the same user share the same parent - the user object.
    urlKeyName - same as key name
    """
    urlKeyName = db.StringProperty(required=True)


class UserComment(DatedBaseModel, KeyName):
    message = db.TextProperty()
    articleUrl = db.StringProperty()
    fid = db.IntegerProperty()
    
    @classmethod
    def keyNamePrefix(cls):
        return "UserComment:" 
    

class Friendship(DatedBaseModel, KeyName):
    userId = db.IntegerProperty()
    friendId = db.IntegerProperty()
    
    @classmethod
    def keyNamePrefix(cls):
        return "Friendship:" 
