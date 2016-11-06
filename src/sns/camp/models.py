from google.appengine.ext import db
from google.appengine.ext.db import polymodel

from common.utils import string as str_util
from common.utils import url as url_util
from common.content.trove import consts as trove_const
from sns.core.core import KeyName
from sns.core.base import BaseModel, ModifiedTimeBaseModel, SoftDeleteCreatedTimeNamedBaseModel, SoftDeleteModelPolySmall, ClickCounterNoIndex
from sns.camp import consts as camp_const


class CampaignPolySmall(polymodel.PolyModel, SoftDeleteModelPolySmall):
    name = db.StringProperty(required=True)
    uid = db.IntegerProperty(required=True)
    
    @classmethod
    def syncAttributes(cls):
        return ["name"]

    
class GACampaignIF(db.Model):
    gaOn = db.BooleanProperty(default=False, indexed=False)
    gaUseCampaignName = db.BooleanProperty(default=True, indexed=False)
    gaSource = db.StringProperty(indexed=False) 
    gaMedium = db.StringProperty(indexed=False) 
    gaTerm = db.StringProperty(indexed=False)
    gaContent = db.StringProperty(indexed=False)
    gaCampaign = db.StringProperty(indexed=False)

    @classmethod
    def ga_attrs(cls):
        return ('gaOn', 'gaUseCampaignName', 'gaSource', 'gaMedium', 'gaTerm', 'gaContent', 'gaCampaign')


class Campaign(SoftDeleteCreatedTimeNamedBaseModel, GACampaignIF):
    modifiedTime = db.DateTimeProperty(auto_now=True, indexed=False)
    uid = db.IntegerProperty(required=True)
    channels = db.ListProperty(db.Key)
    contents = db.ListProperty(db.Key)
    scheduleType = db.IntegerProperty(default=camp_const.SCHEDULE_TYPE_NOW, choices=camp_const.SCHEDULE_TYPES)
    scheduleNext = db.DateTimeProperty()
    scheduleStart = db.DateTimeProperty(indexed=False)
    scheduleEnd = db.DateTimeProperty(indexed=False)
    scheduleInterval = db.StringProperty(indexed=False)
    state = db.IntegerProperty(default=camp_const.CAMPAIGN_STATE_INIT, choices=camp_const.CAMPAIGN_STATES, required=True)
    smallModel = db.ReferenceProperty(CampaignPolySmall, indexed=False)
    
    @classmethod
    def uniqueness_properties(cls) :
        return []

    @classmethod
    def batchSize(cls):
        return camp_const.CAMPAIGN_PER_BATCH
    
    def getScheduleType(self):
        return self.scheduleType
    
    def className(self):
        return self.__class__.__name__
    
    def syncState(self):
        pass
    
    def finished(self):
        return self.state == camp_const.CAMPAIGN_STATE_EXPIRED

    def keyInfo(self):
        return str(self.key().id())+':'+str(self.parent().batch)
        
    def basic_info(self):
        return "%s uid(%d)" % (str_util.encode_utf8_if_ok(self.name), self.uid) 

class Execution(BaseModel, KeyName):
    campaign = db.ReferenceProperty(required=True)
    executionTime = db.DateTimeProperty(auto_now=True)
    state = db.IntegerProperty(default=camp_const.EXECUTION_STATE_INIT, choices=camp_const.EXECUTION_STATES, required=True)
    errorMsg = db.StringProperty(indexed=False)
    
    @classmethod
    def keyNamePrefix(cls):
        return "Execution:"        


class Post(ModifiedTimeBaseModel, KeyName):
    uid = db.IntegerProperty(required=True)
    urlHash = db.StringProperty()
    state = db.IntegerProperty(default=camp_const.EXECUTION_STATE_INIT, choices=camp_const.EXECUTION_STATES, required=True)
    url = db.StringProperty(indexed=False)
    errorMsg = db.StringProperty(indexed=False)
    execution = db.ReferenceProperty(Execution,required=True,collection_name='posts')
    campaign = db.ReferenceProperty(required=True)
    troveMentionType = db.IntegerProperty(choices=trove_const.MENTION_TYPES)
    extra = db.TextProperty()
    
    @classmethod
    def keyNamePrefix(cls):
        return "Post:"    
    
    def className(self):
        return self.__class__.__name__

    def domain(self):
        return url_util.root_domain(self.url) if self.url else None

    
class CampaignClickCounterKeyName(KeyName):
    @classmethod
    def keyNamePrefix(cls):
        return "CampaignCC:" 
        

class CampaignClickCounter(ClickCounterNoIndex, CampaignClickCounterKeyName):
    pass


class Retweet(ModifiedTimeBaseModel):
    cat = db.IntegerProperty(default=camp_const.RT_CAT_DUPLICATED_URL, choices=camp_const.RT_CATEGORIES, required=True)
    chid = db.IntegerProperty(indexed=False) 
    tweetId = db.IntegerProperty()
    rtChid = db.IntegerProperty() 
    rtId = db.IntegerProperty(indexed=False)
    urlHash = db.StringProperty(indexed=False)

                