from google.appengine.ext import db

from common.utils import string as str_util
from sns.core import core as db_core
from sns.core.core import ChidKey
from sns.core.base import DatedBaseModel, CreatedTimeIF, ModifiedTimeIF, DateNoIndexIF, BaseIF
from sns.chan import consts as channel_const
from sns.cont.models import Topic, TopicKeyName, TopicTargets
from sns.log.models import CmpTwitterAcctStats 
from sns.femaster import consts as femaster_const


class SourceTopicTargetKeyName(db_core.KeyName):
    pass


class SourceTopicTargetLock(DatedBaseModel, SourceTopicTargetKeyName):
    pass


class Source(ModifiedTimeIF, ChidKey):
    """ Use Twitter user_id string as key name.
        set parent to CmpTwitterAcctStats.
        tgtflwrs - available target followers in list text, e.g., "[123, 456, 789]".
        count - should be in sync with tgtflwrs.
        enough - True if count >= femaster_const.TARGET_FOLLOWERS_ALLOC_SIZE 
    """
    tgtflwrs = db.TextProperty(default="[]")
    count = db.IntegerProperty(default=0)
    enough = db.BooleanProperty(default=False)
    state = db.IntegerProperty(default=channel_const.CHANNEL_STATE_NORMAL, choices=channel_const.CHANNEL_STATES)
    
    @classmethod
    def get_or_insert_by_chid(cls, chid):
        parent = CmpTwitterAcctStats.get_by_chid(chid)
        if parent is None:
            raise Exception("CmpTwitterAcctStats doesn't exist for %s!" % chid)
        return cls.get_or_insert_by_cstats(parent)

    @classmethod
    def get_or_insert_by_cstats(cls, cstats):
        return cls.get_or_insert(key_name=cstats.key().name(), parent=cstats, state=cstats.chanState)

    @classmethod
    def get_by_chid(cls, chid):
        chid = str(chid)
        parent = CmpTwitterAcctStats.get_by_chid(chid)
        if parent is None:
            return None
        return cls.get_by_key_name(chid, parent=parent)

    def get_tgtflwrs(self):
        return eval(self.tgtflwrs)    

    def add_tgtflwrs(self, new_tgtflwrs):    
        tgtflwrs = eval(self.tgtflwrs)
        tgtflwrs.extend(new_tgtflwrs)
        self.tgtflwrs = str_util.int_list_2_list_str(tgtflwrs) 
        self.count = len(tgtflwrs)
        self.enough = self.count >= femaster_const.TARGET_FOLLOWERS_ALLOC_SIZE

    def actual_count(self):
        return len(eval(self.tgtflwrs))

    def reset(self, db_put=False):
        self.tgtflwrs = '[]'
        self.enough = False
        self.count = 0
        self.state = channel_const.CHANNEL_STATE_NORMAL
        if db_put: self.put()

    def __str__(self):
        return "%s(key_name=%s, state=%d, enough=%s, count=%s, tgtflwrs=%s)" % (self.__class__.__name__, self.key().name(), self.state, self.enough, self.count, self.tgtflwrs)
    

class Target(DateNoIndexIF):
    """ Use Twitter user_id string as key name. 
        cursor - Twitter API cursor.
        size - current page size.   
    """
    handle = db.StringProperty(required=True) 
    cursor = db.IntegerProperty(indexed=False, default=-1)
    offset = db.IntegerProperty(indexed=False, default=0)
    size = db.IntegerProperty(indexed=False, default=0)
    completed = db.BooleanProperty(default=False, required=True)
    state = db.IntegerProperty(default=femaster_const.TARGET_STATE_NORMAL, choices=femaster_const.TARGET_STATES)
    tgtflwrs = db.TextProperty(default="[]")

    @classmethod
    def get_or_insert_by_user_id(cls, user_id, handle):
        return cls.get_or_insert(str(int(user_id)), handle=handle) 

    @classmethod
    def get_by_user_id(cls, user_id):
        return cls.get_by_key_name(str(user_id)) 

    def user_id(self):
        return int(self.key().name())

    def is_active(self):
        return self.state == femaster_const.TARGET_STATE_NORMAL and not self.completed
        
    def add_tgtflwrs(self, more_followers):
        if not more_followers:
            return 
        self.offset += len(more_followers) 
        followers = eval(self.tgtflwrs) if self.tgtflwrs else []
        followers.extend(more_followers)
        self.size = len(followers)
        self.tgtflwrs = str_util.int_list_2_list_str(followers)

    def user_id_handle_str(self):
        return "%d@%s" % (self.user_id(), self.handle)


class TopicTarget(DateNoIndexIF, TopicKeyName):
    """ Use topic key as key name. """
    user_id = db.IntegerProperty(indexed=False, required=True)

    def get_topic(self):
        Topic.get_by_topic_key(self.keyNameStrip())

    def get_target(self):
        return Target.get_by_user_id(self.user_id) if self.user_id else None

    @classmethod
    def get_target_by_topic_key(cls, topic_key):
        topic_target = cls.get_by_key_name_strip(topic_key)
        target = topic_target.get_target() if topic_target else None
        current_user_id = topic_target.user_id if topic_target else None
        current_user_id_active = target.is_active() if target else False
        new_user_id, new_handle = TopicTargets.get_next_target(topic_key, current_user_id=current_user_id, current_user_id_active=current_user_id_active)
        if not new_user_id: return None
        if new_user_id == current_user_id: return target
        if topic_target:
            topic_target.user_id = new_user_id
            topic_target.put()
        else:
            topic_target = cls.get_or_insert_by_topic_key(topic_key, new_user_id)
        target = Target.get_or_insert_by_user_id(new_user_id, new_handle)
        return target

    @classmethod
    def get_or_insert_by_topic_key(cls, topic_key, user_id):
        return cls.get_or_insert(cls.keyName(topic_key), user_id=user_id)


class TopicTargetError(DateNoIndexIF, TopicKeyName):
    """ Use topic key as key name. """
    error_msg = db.StringProperty(indexed=False, required=True)

    def get_topic(self):
        Topic.get_by_topic_key(self.keyNameStrip())

    @classmethod
    def get_or_insert_by_topic_key(cls, topic_key, error_msg):
        return cls.get_or_insert(cls.keyName(topic_key), error_msg=error_msg)


class TgtflwrChangeLog(CreatedTimeIF):
    "Objects can be created, deleted, read, but not updated. "
    chid = db.IntegerProperty(indexed=False, required=True)
    tgtflwrs = db.TextProperty(default="[]")

    @classmethod
    def create(cls, chid, tgtflwrs):
        if not tgtflwrs:
            return None
        source = Source.get_by_chid(chid)
        if source is None:
            raise Exception("FE Master: Source not found for channel %d." % chid)
        obj = cls(parent=source, chid=chid, tgtflwrs=str_util.int_list_2_list_str(tgtflwrs))
        obj.put()
        return obj

    def get_tgtflwrs(self):
        return eval(self.tgtflwrs) if self.tgtflwrs else []
    

class TgtflwrAllocationLog(TgtflwrChangeLog):
    pass


class TgtflwrFollowLog(TgtflwrChangeLog):
    pass


class TwitterUserListIF(BaseIF):
    user_ids = db.TextProperty(default="[]")

    def get_user_ids(self):
        return eval(self.user_ids) if self.user_ids else []
    
    def set_user_ids(self, user_ids):
        self.user_ids = str_util.int_list_2_list_str(user_ids)
            
    def add_user_ids(self, more):
        if not more:
            return
        user_ids = self.get_user_ids()
        user_ids.extend(more)
        self.user_ids = str_util.int_list_2_list_str(user_ids)
 
