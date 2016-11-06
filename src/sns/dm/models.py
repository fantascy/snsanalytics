import logging
from datetime import datetime

from google.appengine.ext import db
from search.core import SearchIndexProperty, porter_stemmer
from twitter import errors as twitter_error
from twitter.api import TwitterApi

from common import consts as common_const
from common.utils import string as str_util
from common.utils import datetimeparser
from sns.serverutils import url as server_url_util, memcache
from sns.chan.models import TAccount
from sns.core.core import KeyName, CampaignParentKeyName, CampaignParent, User, get_user_id
from sns.core.base import DatedBaseModel, ClickCounter
from sns.url.api import ShortUrlProcessor
from sns.url.models import ShortUrlReserve, ShortUrlClickCounter
from sns.camp import consts as camp_const
from sns.camp.models import Campaign, CampaignPolySmall
from sns.camp.api import SCHEDULE_EXPEDITE_FACTOR
from sns.dm import consts as dm_const


class DMCampaignParentKeyName(CampaignParentKeyName):
    @classmethod
    def keyNamePrefix(cls):
        return "DMCampaignParentKeyName:"


class DMCampaignParent(CampaignParent, DMCampaignParentKeyName):
    userHashCode = db.IntegerProperty(required=True)
    
    @classmethod
    def get_or_insert_parent(cls,batch,uid=None):
        if uid is None:
            uid = get_user_id()
        keyname = cls.keyName(str(uid)+':'+str(batch))
        parent = memcache.get(keyname)
        if parent is None:
            userHashCode = User.hash_code(uid)
            mail = User.get_by_id(uid).mail
            parent = cls.get_or_insert(key_name=keyname,uid=uid,batch=batch,userHashCode=userHashCode,mail=mail)
            memcache.set(keyname,parent)
        return parent


class DMChannelLock(DatedBaseModel, KeyName):
    username = db.StringProperty(required=True,indexed=False)
    locked = db.BooleanProperty(required=True, default=False,indexed=False)
    ruleId = db.StringProperty(indexed=False)
    
    @classmethod
    def keyNamePrefix(cls):
        return "DMChannelLock:"


class DMCampaignSmall(CampaignPolySmall):
    pass


class DMCampaign(Campaign):
    sourceChannel = db.ReferenceProperty(TAccount, required=False)
    sendOrder = db.IntegerProperty(required=True, default=dm_const.DM_LATEST_TO_OLDEST, choices=dm_const.DM_ORDER_TYPES, indexed=False)
    number = db.IntegerProperty()
    dailyTarget = db.IntegerProperty(indexed=False)
    totalTarget = db.IntegerProperty(indexed=False)
    runTurn = db.IntegerProperty(default=0, indexed=False)
    sendTurn = db.ListProperty(int, indexed=False)
    errorMsg = db.StringProperty(indexed=False)
    totalSendCount = db.IntegerProperty(required=True, default=0, indexed=False)
    totalFailCount = db.IntegerProperty(required=True, default=0, indexed=False)
    followerNumber = db.IntegerProperty(indexed=False)
    targetSendCursor = db.IntegerProperty(required=True, default=-1, indexed=False)
    locations = db.StringListProperty()
    topics = db.StringListProperty()    
    advancedCampaign = db.StringProperty()
    promoteType = db.IntegerProperty()
    accountPromoteType = db.IntegerProperty()
    search_index = SearchIndexProperty(('name',), indexer=porter_stemmer, relation_index=False)

    def getTwitterApi(self):
        return TwitterApi(oauth_access_token=self.sourceChannel.oauthAccessToken)
    
    def getMsg(self):
        length = len(self.contents)
        now = datetime.utcnow()
        timeDelta = now - datetime(year=2000,month=1,day=1)
        hourDiff = timeDelta.days *24 + timeDelta.seconds/3600
        if length == 0:
            return None
        index = hourDiff%length
        return self.getText(self.contents[index])
        
    def getText(self, msgId):
        article = db.get(msgId)
        if article.url is None:
            text = article.msg
            text = text.replace('\n', ' ')
        else:
            dmMapKeyName = DMMapping.keyName(msgId)
            dmMapping = DMMapping.get_by_key_name(dmMapKeyName, self)
            if dmMapping is None:
                put_obj = []
                parent = self.parent()
                shortUrlResv = ShortUrlReserve.get_by_key_name(parent.key().name(),parent=parent)
                if shortUrlResv is None:
                    shortUrlResv = ShortUrlReserve(key_name=parent.key().name(),firstCharacter=ShortUrlProcessor.randomFirstCharacter(),parent=parent)
                    shortUrlResv.put()
                urlMappingIdBlocks = ShortUrlProcessor.consumeShortUrlReserve(shortUrlResv.id, 1)
                urlHash = shortUrlResv.firstCharacter + ShortUrlProcessor.extractShortUrlFromResv(urlMappingIdBlocks)
                shortUrlClickCounter = ShortUrlClickCounter(key_name=ShortUrlClickCounter.keyName(urlHash), urlHash=urlHash, parent=parent, url=article.url, msg=article.msg)
                dmMapping = DMMapping(key_name=dmMapKeyName,parent=self,urlHash=urlHash,url=article.url,
                                      shortUrlClickCounter=shortUrlClickCounter)
                hashMapping = HashDMMapping(key_name=HashDMMapping.keyName(urlHash),parent=parent,mapping=dmMapping)
                put_obj.append(shortUrlClickCounter)
                put_obj.append(dmMapping)
                put_obj.append(hashMapping)
                db.put(put_obj)
            if len(self.sendTurn) <= self.runTurn:
                self.sendTurn.append(0)
                db.put(self)
            if dmMapping.url != article.url:
                dmMapping.url = article.url
                parent = self.parent()
                shortUrlResv = ShortUrlReserve.get_by_key_name(parent.key().name(),parent=parent)
                if shortUrlResv is None:
                    shortUrlResv = ShortUrlReserve(key_name=parent.key().name(),firstCharacter=ShortUrlProcessor.randomFirstCharacter(),parent=parent)
                    shortUrlResv.put()
                urlMappingIdBlocks = ShortUrlProcessor.consumeShortUrlReserve(shortUrlResv.id, 1)
                urlHash = shortUrlResv.firstCharacter + ShortUrlProcessor.extractShortUrlFromResv(urlMappingIdBlocks)
                dmMapping.urlHash = urlHash
                dmMapping.put()
                hashMapping = HashDMMapping(key_name=HashDMMapping.keyName(urlHash),parent=parent,mapping=dmMapping)
                hashMapping.put()
            shortURL = ' %s' % server_url_util.short_url(dmMapping.urlHash)
            left = 140 - len(shortURL)
            tmsg = str_util.slice(article.msg, "0:%s" % left)
            text = tmsg + shortURL
        return text

    def loadNextTargetPage(self,targetList):
        """ 
        This function assumes the rule is in a good status to call. 
        Return False if there is exception.
        Set the current target acct to finish status if the target acct is detected to be invalid.
        Retry 3 times to avoid interim Twitter API failures.
        """
        logging.info("Refresh target list: cursor='%s'" % (self.targetSendCursor))
        if self.targetSendCursor==0 :
            targetList.ids = []
            return True,targetList
        retry = 3
        for i in range(0, retry) :
            try :
                response = self.getTwitterApi().followers.ids(screen_name=self.sourceChannel.login(),cursor=self.targetSendCursor)
                logging.info("Refresh follower list: previous_cursor=%s, next_cursor=%s, users=%s" % (response['previous_cursor'], response['next_cursor'], len(response['ids'])))
                self.targetSendCursor = response["next_cursor"]
                targetList.ids = [str(x) for x in response["ids"]]
                return True,targetList
            except twitter_error.TwitterError, tex:
                logging.error("Error when refresh follower list: %s " % (str(tex)))
                self.targetSendCursor = 0
                targetList.ids = []
                self.errorMsg = str(tex)
            except Exception, ex:
                logging.error("Refresh follower list: cursor='%s' error: %s. Hopefully, next time it will be fine. Continue." % (self.targetSendCursor, ex))
        return False,targetList
    
    def syncState(self) :
        targetList = get_target_list(self)
        if self.targetSendCursor==0 and len(targetList.ids)==0:
            if self.scheduleInterval == 'onetime':
                self.state = camp_const.CAMPAIGN_STATE_EXPIRED
            else:
                self.targetSendCursor = -1
                self.runTurn += 1
                self.sendTurn.append(0)
                targetList.ids = []
                targetList.put()
                if self.scheduleNext == common_const.EARLIEST_TIME:
                    self.scheduleNext = self.createdTime + datetimeparser.parseInterval(self.scheduleInterval, memcache.get(SCHEDULE_EXPEDITE_FACTOR))
                else:
                    self.scheduleNext = self.scheduleNext + datetimeparser.parseInterval(self.scheduleInterval, memcache.get(SCHEDULE_EXPEDITE_FACTOR))
                if self.scheduleNext < datetime.utcnow():
                    self.scheduleNext = datetime.utcnow()
        elif self.overTotalTarget():
            self.state = camp_const.CAMPAIGN_STATE_EXPIRED
    
    def finished(self):
        return self.state == camp_const.CAMPAIGN_STATE_EXPIRED
    
    def overTotalTarget(self):
        if self.totalTarget is None:
            return False
        else:
            return self.totalSendCount >= self.totalTarget
    
    def exceedMaxHourlySend(self,count):
        maxCount = 40
        if count >= maxCount:
            logging.info("DM rule '%s' exceeds max hourly message count of %s!" % (self.name, maxCount))
            return True
        else:
            return False
        

class BasicDMCampaign(DMCampaign):
    pass


class AdvancedDMCampaignChild(DMCampaign):
    pass


class AdvancedDMCampaign(DMCampaign):
    categoryType = db.IntegerProperty()


class DMMessageKeyName(KeyName):
    @classmethod
    def keyNamePrefix(cls):
        return "dmmsg:"
    

class DMCampaignKeyName(KeyName):
    @classmethod
    def keyNamePrefix(cls):
        return "dmrule:"
    
    
class DMCampaignClickCounter(ClickCounter, DMCampaignKeyName):   
    pass 
            

class DMMappingKeyName(KeyName):
    @classmethod
    def keyNamePrefix(cls):
        return "dmmapping:"
    

class DMMapping(db.Model,DMMappingKeyName):
    urlHash = db.StringProperty()
    url = db.StringProperty()
    shortUrlClickCounter = db.ReferenceProperty(ShortUrlClickCounter)
    

class HashDMMapping(db.Model,DMMappingKeyName):
    mapping = db.ReferenceProperty(DMMapping)    
    

class TargetListKeyName(KeyName):
    @classmethod
    def keyNamePrefix(cls):
        return "targetlist:"

        
class TargetList(db.Model,TargetListKeyName):
    ids = db.StringListProperty()

    
def get_target_list(rule):
    modelUser = rule.parent()
    keyName = TargetList.keyName(rule.id)
    targetList = TargetList.get_or_insert(keyName,parent=modelUser)
    return targetList


class SourceAccountKeyName(KeyName):
    @classmethod
    def keyNamePrefix(cls):
        return "sourceaccount:"
    

class SourceAccount(db.Model, SourceAccountKeyName):
    name = db.StringProperty(required=True)
    hashLevel = db.IntegerProperty(required=True,default=0)
    

def get_source_account(name):
    key_name = SourceAccount.keyName(name)
    modelAccount = SourceAccount.get_or_insert(key_name,name=name)        
    return modelAccount

