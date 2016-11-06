from sets import Set
from datetime import datetime

from google.appengine.ext import db

from common.utils import datetimeparser
from sns.core.core import ChidKey
from sns.core.base import BaseModel, DatedNoIndexBaseModel


class FeParentChannel(db.Model, ChidKey):
    """ Serve as the parent object for each source channel. """
    @classmethod
    def get_or_insert_by_chid(cls, chid):
        return FeParentChannel.get_or_insert(str(chid))        


class FriendSetIF(db.Model):
    """ friends - value is like "Set([12345,67890,...])" """
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
    
    
class DatedFriendSet(BaseModel, FriendSetIF):
    createdTime = db.DateTimeProperty(auto_now_add=True)
    modifiedTime = db.DateTimeProperty(auto_now=True, indexed=False)

class ChannelStatsIF():
    @classmethod
    def get_or_insert_by_chid(cls, chid, **kwargs):
        parent = FeParentChannel.get_or_insert_by_chid(chid)
        return cls.get_or_insert_by_parent(parent)

    @classmethod
    def get_by_parent(cls, parent):
        return cls.get_by_key_name(parent.key().name(), parent=parent)
    
    @classmethod
    def get_or_insert_by_parent(cls, parent, **kwargs):
        return cls.get_or_insert(parent.key().name(), parent=parent, **kwargs)
    

class ChannelHourlyStatsIF():
    @classmethod
    def get_or_insert_by_datetime_chid(cls, chid, t=datetime.utcnow(), **kwargs):
        parent = FeParentChannel.get_or_insert_by_chid(chid)
        return cls.get_or_insert_by_parent_and_datetime(parent, t)

    @classmethod
    def get_or_insert_by_parent_and_datetime(cls, parent, t=datetime.utcnow(), **kwargs):
        return cls.get_or_insert(str(cls.datetime_2_int_func()(t)), parent=parent, **kwargs)
    
    @classmethod
    def datetime_2_int_func(cls):
        return datetimeparser.intHour
    

class ChannelDailyStatsIF(ChannelHourlyStatsIF):
    @classmethod
    def datetime_2_int_func(cls):
        return datetimeparser.intDay


class FollowedHourlyCount(DatedNoIndexBaseModel, ChannelHourlyStatsIF):
    hourlyCount = db.IntegerProperty(required=True, default=0, indexed=False)
    hourlyUnfollow = db.IntegerProperty(required=True, default=0, indexed=False)
    finished = db.BooleanProperty(required=True, default=False, indexed=False)    


class ChannelHourlyStats(DatedNoIndexBaseModel, ChannelHourlyStatsIF):
    """
    unfollowCount - Number of unfollows in this hour
    """
    unfollowCount = db.IntegerProperty(required=True, default=0,indexed=False)
    followCount = db.IntegerProperty(required=True, default=0,indexed=False)
    newFollowerCount = db.IntegerProperty(required=True, default=0,indexed=False)
    totalFollowerCount = db.IntegerProperty(required=True, default=0,indexed=False)
    totalFriendCount = db.IntegerProperty(required=True, default=0,indexed=False)
    

class ChannelDailyStats(DatedNoIndexBaseModel, ChannelDailyStatsIF):
    """
    unfollowCount - Number of unfollows in this day
    """
    unfollowCount = db.IntegerProperty(required=True, default=0,indexed=False)
    followCount = db.IntegerProperty(required=True, default=0,indexed=False)
    newFollowerCount = db.IntegerProperty(required=True, default=0,indexed=False)
    totalFollowerCount = db.IntegerProperty(required=True, default=0,indexed=False)
    totalFriendCount = db.IntegerProperty(required=True, default=0,indexed=False)


class HourlyFriendList(DatedFriendSet, ChannelHourlyStatsIF):
    """ 
    An hourly entry of friend list. Hour is in UTC time, sync to createdDate. 
    overFollowLimit - This channel is over new friends limit in this hour.
    """ 
    overFollowLimit = db.BooleanProperty(required=True, default=False,indexed=False)


class HourlyFriendPendingList(DatedFriendSet, ChannelHourlyStatsIF):
    """ An hourly entry of pending friend list. Hour is in UTC time, sync to createdDate. """ 
    pass


class ChannelFriendList(DatedFriendSet, ChannelStatsIF):
    def initialized(self) :
        return False


class UnfollowFriendList(db.Model, ChannelStatsIF):
    createdTime = db.DateTimeProperty(indexed=False)
    friends = db.TextProperty("[]") 

    def initialized(self):
        return self.createdTime is not None 
    
    def reset(self, db_put=False):
        self.createdTime = None
        self.friends = str([])
        if db_put:
            db.put(self)
    
    def getFriends(self):
        if self.friends is None :
            return []
        else :
            return eval(self.friends)

    def addFriends(self, newFriends):
        existingFriends = self.getFriends()
        existingFriends += list(newFriends)
        self.friends = str(existingFriends)
        
    def replaceFriends(self, newFriends):
        self.friends = str(list(newFriends))
        
    def reverse(self):
        friendList = self.getFriends()
        friendList.reverse()
        self.friends = str(friendList)
        
    def count(self):
        return len(self.getFriends())


class CompleteFriendList(ChannelFriendList):
    """ 
    List of all friend history available.
    The friend history includes safe list, black list, pending list, and normal friends
    """ 
    lastRefreshTime = db.DateTimeProperty(indexed=False)
    isInitialized = db.BooleanProperty(required=True, default=False,indexed=False)

    def initialized(self) :
        return self.isInitialized


class FriendBlackList(ChannelFriendList):
    """ 
    List of accounts that can not be followed by this Twitter acct.
    Use the channel key as key.
    """ 
    def initialized(self) :
        return True


class SafeFriendSet(ChannelFriendList):
    """ 
    List of accounts that should never be un-followed by this Twitter acct.
    All friends that are not followed using the follower tool go to safelist.
    Use the channel key as key.
    """ 
    listIds = db.StringListProperty(indexed=False)
    lastRefreshTime = db.DateTimeProperty(indexed=False)

    def initialized(self) :
        return self.friends is not None


