import logging
import datetime
from sets import ImmutableSet

from google.appengine.ext import db
from google.appengine.api import users

from django.http import HttpResponse

import context, deploysns
from common.utils import string as str_util
from sns.serverutils import memcache, deferred
from sns import limits as limit_const
from sns.core.core import User, get_user, UserKeyName, get_user_idMap, UserIdMap, get_user_id, get_user_by_mail
from sns.core import base as db_base
from sns.api import errors as api_error
from sns.api import consts as api_const
from sns.api.base import BaseProcessor
import consts as user_const
from models import UserCounters, UserClickCounter, UserPostCounter, UserFailureCounter, GlobalUserCounter


class UserProcessor(BaseProcessor):
    """
    The user processor.
    """
    def getModel(self):
        return User

    def init(self, modelUser):
        keyName = UserKeyName.keyName(str(modelUser.key().id()))
        userPostCounter = UserPostCounter.get_by_key_name(keyName, parent=modelUser)
        if userPostCounter is not None :
            return
        
        def _txn(modelUser):
            userPostCounter = UserPostCounter(key_name=keyName, parent=modelUser)
            userFailureCounter = UserFailureCounter(key_name=keyName, parent=modelUser)
            userCounters = UserCounters(key_name = keyName, 
                                        parent = modelUser,
                                        postCounter=userPostCounter,
                                        failureCounter=userFailureCounter)
            db.put([userCounters, userPostCounter, userFailureCounter])

        db.run_in_transaction(_txn, modelUser)
    
    def update(self, params):
        modelUser = BaseProcessor.update(self, params)
        self._memcache_refresh(modelUser)

    def getUserDailyPostLimit(self, params):
        modelUser = params.get('user')
        if modelUser.isUnlimited() :
            return limit_const.LIMIT_POST_DAILY_ADMIN
        else:       
            return limit_const.LIMIT_POST_DAILY_PER_USER
        
    def getUserDailyExecutionLimit(self,params):
        return limit_const.LIMIT_EXECUTION_DAILY_PER_USER
    
    def incrementStats(self, newStats, modelUser):
        if newStats is None or newStats.isZero() :
            return
        keyName = UserKeyName.keyName(str(modelUser.key().id()))
        userCC = UserCounters.get_by_key_name(keyName, modelUser)
        
        userCC.postCounter.increment(modelUser,newStats.post_count)
        userCC.failureCounter.increment(modelUser,newStats.failure_count)
        
        db.put([userCC.postCounter,userCC.failureCounter])
    
    def getUserCounters(self, params={}):
        modelUser = db_base.parseKeyOrModel(params.get('parent', get_user()))
        keyName = UserKeyName.keyName(str(modelUser.key().id()))
        userCC = UserCounters.get_by_key_name(keyName, modelUser)
        return userCC

    @classmethod
    def supportedOperations(cls):
        return ImmutableSet([
                           # api_const.API_O_CREATE, 
                           api_const.API_O_GET, 
                           api_const.API_O_UPDATE, 
                           api_const.API_O_DELETE, 
                           api_const.API_O_QUERY, 
                           api_const.API_O_APPROVE, 
                           api_const.API_O_UPGRADE, 
                           api_const.API_O_DEGRADE,
                           api_const.API_O_GETALLSTATS,
                           api_const.API_O_EXECUTE,
                           api_const.API_O_QUERY_ALL,
                           api_const.API_O_REFRESH,
                           api_const.API_O_ADMIN,
                           api_const.API_O_CHANGE_USER])

    def approve(self, params):
        return self._setState(params, user_const.USER_STATE_STANDARD)

    def upgrade(self, params):
        mail = params.get('mail',None)
        value = params.get('value',None)
        idMap = get_user_idMap(mail)
        uid = idMap.uid
        modelUser = User.get_by_id(uid)
        if modelUser is None :
            raise api_error.ApiError(api_error.API_ERROR_UNKNOWN, "Could not instantiate user '%s'" % mail)
        else :
            if value is None:
                new_state=modelUser.state+1
            else:
                new_state = int(value)
            if new_state in user_const.USER_STATES:
                modelUser.state=new_state
                self._save(modelUser)
            else:
                pass 
            return modelUser.state
            
    def degrade(self, params):
        mail = params.get('mail',None)
        idMap = get_user_idMap(mail)
        uid = idMap.uid
        modelUser = User.get_by_id(uid)
        if modelUser is None :
            raise api_error.ApiError(api_error.API_ERROR_UNKNOWN, "Could not instantiate user '%s'" % mail)
        else :
            new_state=modelUser.state-1
            if new_state in user_const.USER_STATES:
                modelUser.state=new_state
                self._save(modelUser)
            else:
                pass 
            return modelUser.state

    def _setState(self, params, state):
        userEmail = params['email']
        modelUser = User.get_or_insert(User.keyNameByEmail(userEmail), state=state)
        if modelUser is None :
            raise api_error.ApiError(api_error.API_ERROR_UNKNOWN, "Could not instantiate user '%s'" % userEmail)
        else :
            if modelUser.state!=state :
                modelUser.state = state
                self._save(modelUser)
        return True
    
    def _save(self, modelUser):
        db.put(modelUser)
        return self._memcache_refresh(modelUser)
        
    def _memcache_refresh(self, modelUser):
        userMemcacheKey = User.keyNameById(modelUser.key().id())
        memcache.set(userMemcacheKey, modelUser)
        
    def execute_admin(self, params):
        op = params.get('op', None)
        if op:
            if op=='create_user':
                email = params.get('email', '').lower()
                return self.get_or_insert_user(email, email) if str_util.is_valid_email(email) else "Invalid email!"
            if op=='create_cmp_users':
                start = int(params.get('start', 0))
                size = int(params.get('size', 100))
                deferred.defer(self.__class__.create_cmp_users, start=start, size=size)
                return "Creating %d users..." % size
            if op=='toggle_cmp_status':
                mail = params.get('mail', None) 
                return self._toggleCmpStatus(mail)
            if op=='cleanup_cmp_tags':
                deferred.defer(self.__class__.cleanup_cmp_tags)
                return "Cleaning up CMP user tags..."
            if op=='normalize_user_emails':
                deferred.defer(self.__class__.normalize_user_emails)
                return "Normalizing CMP user emails..."
            if op=='mark_known_cmp_users':
                deferred.defer(self.__class__.mark_known_cmp_users)
                return "Marking known CMP users..."
        return BaseProcessor.execute_admin(self, params)

    def create_one_user(self, email):
        return self.get_or_insert_user(email, email)

    @classmethod
    def cleanup_cmp_tags(cls):
        cmp_users = User.all().filter('isContent', True).fetch(limit=1000)
        updated_count = 0
        for user in cmp_users:
            if user.tags is None or user.tags in user_const.CMP_TAGS:
                continue
            logging.error("User %s has a wrong tag %s." % (user.mail, user.tags))
            user.tags = None
            db.put(user)
            updated_count += 1
        logging.info("Cleaned up tags for %d CMP users." % updated_count)
        return updated_count

    @classmethod
    def normalize_user_emails(cls):
        cmp_users = User.all().filter('isContent', True).fetch(limit=1000)
        updated_count = 0
        for user in cmp_users:
            old_email = user.mail
            if old_email.startswith('cohort+'):
                sn = int(old_email.split('+')[1].split('@')[0])
                new_email = user_const.USER_EMAIL_PATTERN % sn
            else:
                new_email = user_const.OLD_USER_EMAIL_MAP.get(old_email, None)
            if not new_email:
                continue
            uid = user.uid
            new_user_email_key = User.keyNameByEmail(new_email)
            new_user_id_map = UserIdMap.get_or_insert(key_name=new_user_email_key, uid=uid)
            if new_user_id_map is None or new_user_id_map.uid != uid:
                logging.error("Error creating user id map for %d %s!" % (uid, new_email))
                continue
            user.mail = new_email
            db.put(user)
            updated_count += 1
        logging.info("Normalized emails for %d CMP users." % updated_count)
        return updated_count

    @classmethod
    def mark_known_cmp_users(cls):
        users = User.all().fetch(limit=1000)
        updated_count = 0
        for user in users:
            if user.isContent: continue
            if user.mail not in user_const.OLD_USER_EMAILS and not user.mail.startswith('cohort+'):
                continue
            user.isContent = True
            db.put(user)
            logging.info("Marked user %s as CMP!" % user.id_email_str())
            updated_count += 1
        logging.info("Marked %d users as CMP!" % updated_count)
        return updated_count

    @classmethod
    def create_cmp_users(cls, start=0, size=100):
        for i in range(start, start+size):
            name = user_const.USER_NAME_PATTERN % i
            email = user_const.USER_EMAIL_PATTERN % i
            cls.get_or_insert_user(name, email)
        logging.info("Finished creating up to %d CMP users!" % size)

    @classmethod
    def get_or_insert_user(cls, name, email, timeZone='US/Pacific', isContent=True):
        try:
            modelUser = get_user_by_mail(email)
            if modelUser:
                return modelUser
            userEmailKey = User.keyNameByEmail(email)
            modelUser = User(name=name, mail=email, timeZone=timeZone, acceptedTerms=True, isContent=isContent, user=None)
            db.put(modelUser)
            idMap = UserIdMap(key_name=userEmailKey, uid=modelUser.key().id())
            db.put(idMap)
            UserProcessor().init(modelUser)
            logging.info("Created user %d '%s' %s." % (modelUser.key().id(), name, email))
            return modelUser
        except Exception:
            logging.exception("Error creating user '%s' %s!" % (name, email))
            return None

    def _toggleCmpStatus(self, mail):
        idMap = get_user_idMap(mail) 
        uid = idMap.uid 
        modelUser = User.get_by_id(uid) 
        if modelUser.isContent: 
            modelUser.isContent = False 
        else: 
            modelUser.isContent = True 
        modelUser.put() 
        user_key = User.keyNameById(uid)            
        memcache.delete(user_key) 
        return modelUser.isContent 
    
    def refresh(self, params):
        return db.run_in_transaction(self._trans_refresh,params)
    
    def _trans_refresh(self, params):
        pass
    
    def changeuser(self,params):
        mail = params.get('mail', None)
        loginMail = users.get_current_user().email()
        idMap = get_user_idMap(loginMail)
        userEmailKey = User.keyNameByEmail(loginMail)
        if mail is None:
            idMap.proxyId = None
            db.put(idMap)
            memcache.delete(userEmailKey)
            user = User.get_by_id(idMap.uid)
            useProxy = (get_user_id(check_proxy=True) != get_user_id(check_proxy=False))
            return user.name + "|" + str(useProxy)
        else:
            mail = mail.replace(' ', '+')
            proxyIdMap = get_user_idMap(mail)
            idMap.proxyId = proxyIdMap.uid
            db.put(idMap)
            memcache.delete(userEmailKey)
            user = User.get_by_id(proxyIdMap.uid)
            useProxy = (get_user_id(check_proxy=True) != get_user_id(check_proxy=False))
            return user.name + "|" + str(useProxy)
        

class UserClickCounterProcessor(BaseProcessor):
    def getModel(self):
        return UserClickCounter
        

def syncUser(request):
    if not users.is_current_user_admin():  
        return HttpResponse(status=404)
    userCounter = GlobalUserCounter.get_or_insert_counter()
    deferred.defer(_deferredCalculateUser,userCounter.id)
    return HttpResponse('Running', mimetype='application/javascript')    
    
    
def _deferredCalculateUser(oid):
    context.set_deferred_context(deploy=deploysns)
    initial = datetime.datetime.utcnow()
    userCounter = db.get(oid)
    if userCounter.lastUpdateTime is None:
        firstOne = User.all().order('firstVisit').fetch(limit=1)[0].firstVisit
        userCounter.lastUpdateTime = datetime.datetime(year=firstOne.year,month=firstOne.month,day=firstOne.day)
    if userCounter.dailyNumber is None:
        userCounter.dailyNumber = '[0]'
    if userCounter.dailyIncrease is None:
        userCounter.dailyIncrease = '[]'
    num = eval(userCounter.dailyNumber)
    incease = eval(userCounter.dailyIncrease)
    timeout = False
    while True:
        if initial + datetime.timedelta(seconds=20) < datetime.datetime.utcnow():
            timeout = True
            break
        if userCounter.lastUpdateTime + datetime.timedelta(days=1) > initial:
            break
        userCounter.lastUpdateTime += datetime.timedelta(days=1)
        logging.info('User counter updated at %s.' % str(userCounter.lastUpdateTime))
        users = User.all().filter('firstVisit >=', userCounter.lastUpdateTime- datetime.timedelta(days=1)).filter('firstVisit <', userCounter.lastUpdateTime).order('firstVisit')
        incease.append(users.count())
        num.append(num[-1]+users.count())
    userCounter.dailyIncrease = str(incease)
    userCounter.dailyNumber = str(num)
    userCounter.put()
    if timeout:
        deferred.defer(_deferredCalculateUser, oid)
                    
def clearProxyUser(request):
    currentUser = get_user(check_proxy=False)
    db.run_in_transaction(_clearProxyUser,currentUser)
    data = currentUser.name
    return HttpResponse(data, mimetype='application/javascript')    
    
def _clearProxyUser(currentUser): 
    currentUser.proxyUser = None
    currentUser.readOnly = False
    db.put(currentUser)
      
