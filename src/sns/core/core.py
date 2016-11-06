import datetime
import logging

from google.appengine.api import users
from google.appengine.ext import db

from common.utils import string as str_util
import context 
from sns.serverutils import memcache
from sns.api import errors as api_error
from sns.usr import consts as user_const
from sns.api.errors import ApiError
from search.core import SearchIndexProperty, porter_stemmer
        

def normalize_2_key(param):
    """
    A convenient function to get the db model key based on input param.
    param - either a db.Key, or a dict with the key 'id', or a string as key id
    """
    if isinstance(param, db.Key) :
        return param
    if isinstance(param, db.Model) :
        return param.key()
    if isinstance(param, str) or isinstance(param, unicode) :
        return db.Key(param)
    if isinstance(param, dict) :
        return normalize_2_key(param['id'])
    else :
        try :
            """ Possible cases include Django MergeDict and QueryDict, etc. """
            return normalize_2_key(param['id'])
        except :
            pass
    raise ApiError(api_error.API_ERROR_UNKNOWN, "Could not get db model key because of bad input param type: %s !" % type(param))


def normalize_2_id(param):
    dbKey = normalize_2_key(param)
    if dbKey is None :
        return None
    return str(dbKey)


def normalize_2_model(param):
    """
    A convenient function to get the model object based on input param.
    The function is different from getModelObject(). If input param is db.Model, the memory state of the model is returned. 
    While, getModelObject() always returns the data store state of the model.
    """
    if isinstance(param, db.Model) :
        return param
    else :
        return db.get(normalize_2_key(param))


class KeyName(object):
    @classmethod
    def keyNamePrefix(cls):
        return "Key:"

    @classmethod
    def normalizedName(cls, name):
        if not isinstance(name, basestring):
            name = str(name)
        return str_util.strip(name)
    
    @classmethod
    def keyName(cls, name):
        return "%s%s" % (cls.keyNamePrefix(), cls.normalizedName(name))
    
    @classmethod
    def key_name_strip(cls, keyOrStr):
        key = normalize_2_key(keyOrStr)
        return key.name().split(':', 1)[1]
    
    def keyNameStrip(self):
        return self.key().name().split(':', 1)[1]

    @classmethod
    def get_by_key_name_strip(cls, key_name_strip):
        return cls.get_by_key_name(cls.keyName(key_name_strip))


class ChidKey(object):
    @property
    def chid(self):
        return int(self.key().name())
    
    @classmethod
    def get_by_chid(cls, chid):
        return cls.get_by_key_name(str(chid))


class MemcachedIF(KeyName):
    NONE_OBJ = "DummyNoneObj"
    @classmethod
    def mem_key(cls, name):
        return "MemKey:%s" % cls.keyName(name)
    
    @classmethod
    def pull(cls, name, insert=False, **kwds):
        mem_key = cls.mem_key(name)  
        obj = memcache.get(mem_key)
        if insert and obj == cls.NONE_OBJ:
            obj = None
        if not obj:
            key_name = cls.keyName(name)
            obj = cls.get_or_insert(key_name, **kwds) if insert else cls.get_by_key_name(key_name)
            if not obj:
                obj = cls.NONE_OBJ
            memcache.set(mem_key, obj)
        return None if obj == cls.NONE_OBJ else obj
    
    def push(self):
        db.put(self)  
        name = self.keyNameStrip()
        mem_key = self.mem_key(name)
        memcache.set(mem_key, self)
        return self


class UserKeyName(KeyName):
    @classmethod
    def keyNamePrefix(cls):
        return "User:"

    @property
    def uid(self):
        return int(self.keyNameStrip())
    

class UserIdMap(db.Model):
    uid = db.IntegerProperty()
    proxyId = db.IntegerProperty()


class User(db.Model, UserKeyName):
    USER_HASH_SIZE = 10
    user = db.UserProperty(auto_current_user_add=True) 
    firstVisit = db.DateTimeProperty(auto_now_add=True)
    lastVisit = db.DateTimeProperty(auto_now=True)
    name = db.StringProperty()
    tags = db.StringProperty(default=None)
    timeZone  = db.StringProperty(indexed=False)
    mail = db.StringProperty()
    notifyEmail = db.StringProperty(indexed=False)
    state = db.IntegerProperty(required=True, default=user_const.USER_STATE_NOT_APPROVED, choices=user_const.USER_STATES)
    stateModifiedDate = db.DateTimeProperty() 
    acceptedTerms = db.BooleanProperty(default=False)
    subSystemNotification = db.BooleanProperty(default=False)
    subNewsletter = db.BooleanProperty(default=False)
    subWeeklyReport = db.BooleanProperty(default=False)
    isContent = db.BooleanProperty(default=False)
    searchIndex = SearchIndexProperty(('name', 'tags', 'timeZone', 'mail'), indexer=porter_stemmer,relation_index=False)
    
    @property
    def uid(self):
        return self.key().id()
    
    @classmethod
    def cu_exclude_properties(cls) :
        return ['user', 'firstVisit', 'lastVisit']
    
    @classmethod
    def create_exclude_properties(cls) :
        return cls.cu_exclude_properties()
    
    @classmethod
    def update_exclude_properties(cls) :
        return cls.cu_exclude_properties()
    
    @classmethod
    def uniqueness_properties(cls) :
        return []
    
    @classmethod
    def display_exclude_properties(cls) :
        return []
  
    @classmethod
    def keyNameById(cls, userId):
        return "%s%s" % (cls.keyNamePrefix(), str_util.strip(str(userId))) 

    @classmethod
    def keyNameByEmail(cls, email):
        return "%s%s" % (cls.keyNamePrefix(), str_util.normalizeEmail(email)) 

    @classmethod    
    def log_user(cls, login_required=True):
        user = users.get_current_user()
        if user is None :
            if not login_required : return None
            raise ApiError(api_error.API_ERROR_USER_NOT_LOGGED_IN)
        else :
            if users.is_current_user_admin() :
                init_state = user_const.USER_STATE_UNLIMITED
            else :
                init_state = user_const.USER_STATE_NOT_APPROVED
            
            userEmailKey = cls.keyNameByEmail(user.email())
            idMap = memcache.get(userEmailKey)
            if idMap is None:
                idMap = UserIdMap.get_by_key_name(userEmailKey)
                if idMap is not None:
                    pass
                else:
                    modelUser = User(state=init_state, mail=user.email())
                    db.put(modelUser)
                    idMap = UserIdMap(key_name=userEmailKey,uid=modelUser.key().id())
                    db.put(idMap)
                memcache.set(userEmailKey,idMap)
                
            userIdKey = cls.keyNameById(idMap.uid)
            modelUser = memcache.get(userIdKey)
            if modelUser is None:
                modelUser = User.get_by_id(idMap.uid)
                memcache.set(userIdKey,modelUser)
                    
            if not modelUser.isApproved() and context.get_context().manual_approval():
                raise ApiError(api_error.API_ERROR_USER_NOT_APPROVED)
            return modelUser
        
    @classmethod
    def is_admin(cls):
        if users.is_current_user_admin():
            return True
        else:
            return False
    
    @classmethod    
    def get_by_key(cls, userOrKey):
        if isinstance(userOrKey, User) :
            return userOrKey
        
        user = memcache.get(userOrKey.keyNameStrip())
        if user is None :
            user = db.get(userOrKey)
            memcache.set(userOrKey.keyNameStrip(), user)
        return user
    
    @classmethod    
    def hash_code(cls, uid):
        return uid % cls.USER_HASH_SIZE

    def hashCode(self):
        return User.hash_code(self.key().id())

    def uidHashCodeStr(self):
        return "%d:%d" % (self.key().id(), self.hashCode())

    def isApproved(self, check_login_user=True):
        if check_login_user and users.is_current_user_admin() or self.isContent:
            return True
        else:
            if self.state != user_const.USER_STATE_NOT_APPROVED:
                logging.info("Non CMP user %s is approved!" % self.mail)
            return self.state != user_const.USER_STATE_NOT_APPROVED
    
    def isUnlimited(self):
        """ 
        for now, let every user be unlimited. let's drive up traffic!
        return self.state == user_const.USER_STATE_UNLIMITED
        """
        return True

    def is_deal(self):    
        return self.tags in ['deals', 'catdeals']

    def id_email_str(self):
        return "%s(%d)" % (self.mail, self.key().id())

    
def get_user_idMap(mail):
    userEmailKey = User.keyNameByEmail(mail)
    idMap = memcache.get(userEmailKey)
    if not idMap:
        idMap = UserIdMap.get_by_key_name(userEmailKey)
    if idMap:
        memcache.set(userEmailKey, idMap)
    return idMap
    
        
def get_user_id_by_mail(mail, check_proxy=True):
    idMap = get_user_idMap(mail)
    if not idMap:
        return None
    if check_proxy and idMap.proxyId is not None:
        return idMap.proxyId
    else:
        return idMap.uid


def get_user_id(check_proxy=True):
    user = users.get_current_user()
    if user is None :
        if context.get_context().login_required(): 
            raise ApiError(api_error.API_ERROR_USER_NOT_LOGGED_IN)
        else :
            return None
    return get_user_id_by_mail(user.email(), check_proxy=check_proxy)


def get_user_id_str():
    uid = get_user_id()
    return str(uid) if uid is not None else None


def get_user_by_id(uid):
    if uid is None:
        return None
    user_key = User.keyNameById(uid)
    modelUser = memcache.get(user_key)
    if modelUser is None :
        modelUser = User.get_by_id(uid)
        if modelUser is None :
            raise ApiError(api_error.API_ERROR_UNKNOWN, "User '%s' is removed from database!" % user_key)
        else :
            memcache.set(user_key, modelUser)
    return modelUser
    

def get_user_by_mail(mail):
    return get_user_by_id(get_user_id_by_mail(mail, check_proxy=False))


def get_user(uid=None, check_proxy=True):
    """
    The assumption here is the current user should be always there, and will be cached if not yet.
    Exception should never throw except that the current user is removed from the datastore.
    """
    if uid is None: 
        uid = get_user_id(check_proxy) 
    return get_user_by_id(uid)
    

def get_logged_in_user_email():
    user = users.get_current_user()
    return user.email() if user else None


class UserEntityGroup(db.Model):
    uid = db.IntegerProperty(required=True)

    @property
    def user(self):
        return User.get_by_id(self.uid)
    
    
class UserBatchEntityGroup(UserEntityGroup):
    batch = db.IntegerProperty(required=True)
    
    
class ChannelParentKeyName(KeyName):
    @classmethod
    def keyNamePrefix(cls):
        return "ChannelParent:"

    
class ChannelParent(UserEntityGroup, ChannelParentKeyName):
    @classmethod
    def get_or_insert_parent(cls,uid=None):
        if uid is None:
            uid = get_user_id()
        keyname = cls.keyName(str(uid))
        parent = memcache.get(keyname)
        if parent is None:
            parent = cls.get_or_insert(key_name=keyname, uid=uid)
            memcache.set(keyname,parent)
        return parent


class ContentParentKeyName(KeyName):
    @classmethod
    def keyNamePrefix(cls):
        return "ContentParent:"

    
class ContentParent(UserEntityGroup, ContentParentKeyName):
    @classmethod
    def get_or_insert_parent(cls,uid=None):
        if uid is None:
            uid = get_user_id()
        keyname = cls.keyName(str(uid))
        parent = memcache.get(keyname)
        if parent is None:
            parent = cls.get_or_insert(key_name=keyname,uid=uid)
            memcache.set(keyname,parent)
        return parent


class CampaignParent(UserBatchEntityGroup):
    pass

    
class CampaignParentKeyName(KeyName):
    pass


class StandardCampaignParentKeyName(CampaignParentKeyName):
    @classmethod
    def keyNamePrefix(cls):
        return "StandardCampaignParent:"


class StandardCampaignParent(CampaignParent, StandardCampaignParentKeyName):
    userHashCode = db.IntegerProperty(required=True)
    
    @classmethod
    def get_or_insert_parent(cls,batch,uid=None):
        if uid is None:
            uid = get_user_id()
        keyname = cls.keyName(str(uid)+':'+str(batch))
        parent = memcache.get(keyname)
        if parent is None:
            userHashCode = User.hash_code(uid)
            parent = cls.get_or_insert(key_name=keyname,uid=uid,batch=batch,userHashCode=userHashCode)
            memcache.set(keyname,parent)
        return parent
    

class EmailCampaignParentKeyName(CampaignParentKeyName):
    @classmethod
    def keyNamePrefix(cls):
        return "EmailCampaignParent:"


class EmailCampaignParent(CampaignParent, EmailCampaignParentKeyName):
    @classmethod
    def get_or_insert_parent(cls,uid=None):
        if uid == None:
            uid = get_user_id()
        batch = 1
        keyname = cls.keyName(str(uid)+':'+str(batch))
        parent = memcache.get(keyname)
        if parent is None:
            parent = cls.get_or_insert(key_name=keyname, uid=uid, batch=batch)
            memcache.set(keyname, parent)
        return parent
    
class SoupCampaignParentKeyName(CampaignParentKeyName):
    @classmethod
    def keyNamePrefix(cls):
        return "SoupCampaignParent:"


class SoupCampaignParent(CampaignParent, SoupCampaignParentKeyName):
    @classmethod
    def get_or_insert_parent(cls,uid=None):
        if uid == None:
            uid = get_user_id()
        batch = 1
        keyname = cls.keyName(str(uid)+':'+str(batch))
        parent = memcache.get(keyname)
        if parent is None:
            parent = cls.get_or_insert(key_name=keyname, uid=uid, batch=batch)
            memcache.set(keyname, parent)
        return parent


class UserClickParentKeyName(KeyName):
    @classmethod
    def keyNamePrefix(cls):
        return "UserClick:"

    
class UserClickParent(UserEntityGroup, UserClickParentKeyName):
    @classmethod
    def get_or_insert_parent(cls,uid=None):
        if uid is None:
            uid = get_user_id()
        keyname = cls.keyName(str(uid))
        parent = memcache.get(keyname)
        if parent is None:
            parent = cls.get_or_insert(key_name=keyname,uid=uid)
            memcache.set(keyname,parent)
        return parent


class UserUrlClickParentKeyName(KeyName):
    @classmethod
    def keyNamePrefix(cls):
        return "UserUrlClickParent:"


class UserUrlClickParent(UserBatchEntityGroup, UserUrlClickParentKeyName):
    @classmethod
    def get_or_insert_parent(cls,batch,uid=None):
        if uid is None:
            uid = get_user_id()
        keyname = cls.keyName(str(uid)+':'+str(batch))
        parent = cls.get_or_insert(key_name=keyname,uid=uid,batch=batch)
        return parent

    

class RawClickCursor(db.Model, KeyName):
    lastUpdateMinute = db.IntegerProperty(default=0)

    @classmethod
    def keyNamePrefix(cls):
        return "RawClickCursor:"

    @classmethod
    def get_rawclick_cursor(cls, userHashCode):
        keyname = cls.keyName(str(userHashCode))
        cursor = cls.get_or_insert(keyname)
        return cursor


class GlobalCronKey(db.Model):
    offset = db.IntegerProperty(required = True, default = 0)
    filterTime = db.DateTimeProperty()
    locked = db.BooleanProperty(default=False)
    failKeys = db.StringListProperty()


class SystemStatusMonitor(db.Model):
    modifiedTime = db.DateTimeProperty(auto_now=True, indexed=False)
    work = db.BooleanProperty(default=True, indexed=False)
    count = db.IntegerProperty(default=100, indexed=False)
    info = db.TextProperty()
    
    def locked(self):
        return not self.work
    
    def logStatus(self, now=datetime.datetime.utcnow()) :
        if self.work:
            logging.info("System monitor '%s' is not locked." % self.key().name())
            return
        delta = now - self.modifiedTime
        msg = "System monitor '%s' is locked for %s." % (self.key().name(), delta)
        if delta > datetime.timedelta(minutes=10) :
            logging.error(msg)
        elif delta > datetime.timedelta(minutes=5) :
            logging.warn(msg)
        elif delta > datetime.timedelta(minutes=3) :
            logging.info(msg)
        else :
            logging.debug(msg)

    @classmethod
    def get_system_monitor(cls, keyname):
        monitor = memcache.get(keyname)
        if monitor is None:
            monitor = cls.get_or_insert(keyname) 
            memcache.set(keyname, monitor)
        return monitor
    
    @classmethod
    def set_system_monitor(cls, obj):
        keyname = obj.key().name()
        obj.modifiedTime = datetime.datetime.now() 
        obj.put()
        memcache.set(keyname, obj)
        return obj
    
    @classmethod
    def is_locked(cls, keyname):
        try:
            monitor = cls.get_system_monitor(keyname)
            return not monitor.work
        except:
            logging.exception("Error when checking lock status for monitor '%s'" % keyname)
            return True
    
    @classmethod
    def acquire_lock(cls, keyname, log=True, preempt=18000):
        """ Return false if lock is not available. Otherwise, lock the monitor and return true.
            log - log lock status
            preempt - if not zero, set the seconds when the existing lock is forced to be released.
        """
        try:
            monitor = cls.get_system_monitor(keyname)
            now = datetime.datetime.utcnow()
            if monitor.work or monitor.modifiedTime+datetime.timedelta(seconds=preempt)<now:
                monitor.work = False
                monitor.modifiedTime = now
                db.put(monitor)
                memcache.set(keyname, monitor)
                logging.info("Acquired lock for monitor '%s' at %s." % (keyname, monitor.modifiedTime))
                return True
            else:
                if log:
                    monitor.logStatus()
        except:
            logging.exception("Error when acquiring lock for monitor '%s'" % keyname)
        return False
    
    @classmethod
    def release_lock(cls, keyname):
        try:
            monitor = cls.get_system_monitor(keyname)
            monitor.work = True
            monitor.modifiedTime = datetime.datetime.utcnow()
            db.put(monitor)
            memcache.set(keyname, monitor)
            logging.info("Released lock for monitor '%s' at %s." % (keyname, monitor.modifiedTime))
        except:
            logging.exception("Error when releasing lock for monitor '%s'" % keyname)
    
