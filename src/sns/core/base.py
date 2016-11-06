import logging
import datetime
import urlparse
import re
from exceptions import Exception

from google.appengine.api import  datastore_types
from google.appengine.ext import db
from google.appengine.ext.db import polymodel

from common import consts as common_const
from common.utils import timezone as ctz_util
from common.utils import iplocation
from sns.api import errors as api_error
from common.utils import datetimeparser
from sns.core import consts as core_const
from sns.api.errors import ApiError
from core import User, get_user


REFERRER_MAX_NUMBER=100


class BaseIF(db.Model):
    @classmethod
    def display_exclude_properties(cls) :
        return []

    @classmethod
    def cu_exclude_properties(cls) :
        return []
    
    @classmethod
    def create_exclude_properties(cls) :
        return cls.cu_exclude_properties()
    
    @classmethod
    def update_exclude_properties(cls) :
        return cls.cu_exclude_properties()
    
    @classmethod
    def uniqueness_properties(cls) :
        return []
   

class CreatedTimeIF(BaseIF):
    createdTime = db.DateTimeProperty(auto_now_add=True)
   

class ModifiedTimeIF(BaseIF):
    modifiedTime = db.DateTimeProperty(auto_now=True)
   

class DateIF(BaseIF):
    createdTime = db.DateTimeProperty(auto_now_add=True)
    modifiedTime = db.DateTimeProperty(auto_now=True)
   

class DateNoIndexIF(BaseIF):
    createdTime = db.DateTimeProperty(auto_now_add=True, indexed=False)
    modifiedTime = db.DateTimeProperty(auto_now=True, indexed=False)
   

class NameIF(BaseIF):
    name = db.StringProperty(required=True, indexed=False)
    nameLower = db.StringProperty(required=True)

    @classmethod
    def uniqueness_properties(cls) :
        return ['nameLower']
    
class ReferrerCounterIF(BaseIF):
    """
    HTTP referrer counter. If the referrer is twitter.com, we count it as twitter; otherwise we count it as direct
    """
    referrerBracket = db.TextProperty(default="{}",required=True)
    
    twitter = db.IntegerProperty(default=0,required=True, indexed=False)
    facebook = db.IntegerProperty(default=0,required=True, indexed=False)
    direct = db.IntegerProperty(default=0,required=True, indexed=False)
    
    def incrementReferer(self,referrer=None):
        referrerMap=eval(self.referrerBracket)
        if referrer is None:
            referrerMap['direct']=referrerMap.setdefault('direct',0)+1
            self.direct+=1    
            self.referrerBracket=str(referrerMap) 
            return
        referrer = urlparse.urlparse(referrer)[1]
        cut_port_re = re.compile(r":\d+$")
        referrer = cut_port_re.sub("", referrer, 1)
        referrer=referrer.lower()
        if referrer.find("www.")!=-1:
            referrer=referrer.replace('www.','')
        
        if referrer:
            if referrer not in referrerMap:
                referrer_max=REFERRER_MAX_NUMBER
                if "Others" in referrerMap:
                    referrer_max+=1
                if len(referrerMap)==referrer_max:
                    sorted_referrer=sorted(referrerMap.items(),key=lambda d:d[1])
                    i=0
                    while True:
                        if sorted_referrer[i][0]=="Others" or sorted_referrer[i][0]=="direct":
                            i+=1
                        else:
                            break
                    referrerMap["Others"]=referrerMap.setdefault("Others",0)+sorted_referrer[i][1]
                    del referrerMap[sorted_referrer[i][0]]
            referrerMap[referrer]=referrerMap.setdefault(referrer,0)+1
            now=datetime.datetime.utcnow()
            month=str(now.month)
            if len(month)<2:
                month="0"+month
            day=str(now.day)
            if len(day)<2:
                day="0"+day
            hour=str(now.hour)
            if len(hour)<2:
                hour="0"+hour
            number_str=str(int(referrerMap[referrer]))+'.'+str(now.year)+month+day+hour

            referrerMap[referrer]=float(number_str)
            
            if referrer.find("twitter.com")!=-1:            
                self.twitter+=1
            elif referrer.find("facebook.com")!=-1:
                self.facebook+=1                
            
            '''delete dirty data which do not have '.com' except direct,twitter,facebook'''
            to_be_deleted=['cotweet','google','tweetdeck','yahoo','tweetie','seesmic']
            for delete in to_be_deleted:
                if referrer.find(delete):
                    if delete in referrerMap.keys():
                        referrerMap[referrer]=referrerMap.setdefault(referrer,0)+referrerMap[delete]
                        del referrerMap[delete]         
        else:
            referrerMap['direct']=referrerMap.setdefault('direct',0)+1
            self.direct+=1    
        self.referrerBracket=str(referrerMap) 

class GeoCounterIF(BaseIF):
    """
    location (country) based counter
    """
    countryBracket = db.TextProperty(default="{}",required=True)
    
    def incrementGeoByCode(self,country_code):
        """
        increment geo, country_code is two char country code 
        """
        if not iplocation.isValidCountryCode(country_code) :
            return
        code=country_code.lower()
        counterMap=eval(self.countryBracket)
        counterMap[code]=counterMap.setdefault(code,0)+1
        self.countryBracket=str(counterMap)
        
    def getAllAsMap(self):
        return eval(self.countryBracket)
    
    def getSortedTopLocation(self,size=3,others=True):
        """
        return sorted top location and their counter
        size: number of records to return
        others: whether to count remaining records as one "others" category 
        """
        counterMap=eval(self.countryBracket)
        result=[]
        otherTotal=0
        for k,v in sorted(counterMap.items(), lambda x, y: cmp(x[1], y[1]),reverse=True):
            if size>0:
                result.append((k,v))
                size=size-1
            elif others:
                otherTotal=otherTotal+v
            else:
                break
        
        if others:
            result.append(("others",otherTotal))
        return result
                    
    
class SoftDeleteIF(BaseIF):
    deleted = db.BooleanProperty(required=True, default=False) 

    @classmethod
    def display_exclude_properties(cls) :
        return ['deleted']

    @classmethod
    def cu_exclude_properties(cls) :
        return []

    @classmethod
    def query_undeleted(cls):
        return cls.all().filter('deleted', False)


class BaseModel(db.Model):
    def ancestor(self):
        parent = self.parent()
        while parent is not None and not isinstance(parent, User) :
            parent = parent.parent()
        return parent
        
    def oid(self):
        return self.key().id()
    
    def refKey(self, attr):
        return getattr(self, "_"+attr)

    def refObj(self, attr, errorOnDataMissing=False):
        try :
            return getattr(self, attr)
        except Exception, e :
            errMsg = e.message
            msg = "Model '%s' attribute '%s' cannot be resolved. %s: %s" % (self.kind(), attr, type(e).__name__, errMsg) 
            dataMissingError = api_error.ApiError(api_error.API_ERROR_DATA_MISSING, msg)
            logging.error(dataMissingError)
            if errorOnDataMissing :
                raise dataMissingError
        
    @classmethod
    def dbModel(cls):
        """
        This function returns db.Model by default. A sub class can override it to polyModel.
        """
        return db.Model
    
    @classmethod
    def cu_exclude_properties(cls) :
        return ['key']
   
    @classmethod
    def display_exclude_properties(cls) :
        return []

    @classmethod
    def uniqueness_properties(cls) :
        return []


class DatedBaseModel(BaseModel, DateIF):
    pass


class DatedNoIndexBaseModel(BaseModel, DateNoIndexIF):
    pass


class CreatedTimeBaseModel(BaseModel, CreatedTimeIF):
    pass


class ModifiedTimeBaseModel(BaseModel, ModifiedTimeIF):
    pass


class NamedBaseModel(DatedBaseModel, NameIF):
    @classmethod
    def uniqueness_properties(cls) :
        return DatedBaseModel.uniqueness_properties() + NameIF.uniqueness_properties()
    

class SoftDeleteBaseModel(DatedBaseModel, SoftDeleteIF):
    @classmethod
    def display_exclude_properties(cls) :
        return DatedBaseModel.display_exclude_properties() + SoftDeleteIF.display_exclude_properties()

    @classmethod
    def cu_exclude_properties(cls) :
        return DatedBaseModel.cu_exclude_properties() + SoftDeleteIF.cu_exclude_properties()


class SoftDeleteNamedBaseModel(SoftDeleteBaseModel, NameIF):
    @classmethod
    def uniqueness_properties(cls) :
        return SoftDeleteBaseModel.uniqueness_properties() + NameIF.uniqueness_properties()


class SoftDeleteNoIndexBaseModel(DatedNoIndexBaseModel, SoftDeleteIF):
    @classmethod
    def display_exclude_properties(cls) :
        return DatedNoIndexBaseModel.display_exclude_properties() + SoftDeleteIF.display_exclude_properties()

    @classmethod
    def cu_exclude_properties(cls) :
        return DatedNoIndexBaseModel.cu_exclude_properties() + SoftDeleteIF.cu_exclude_properties()


class SoftDeleteNoIndexNamedBaseModel(SoftDeleteNoIndexBaseModel, NameIF):
    @classmethod
    def uniqueness_properties(cls) :
        return SoftDeleteNoIndexBaseModel.uniqueness_properties() + NameIF.uniqueness_properties()


class SoftDeleteCreatedTimeBaseModel(CreatedTimeBaseModel, SoftDeleteIF):
    @classmethod
    def display_exclude_properties(cls) :
        return CreatedTimeBaseModel.display_exclude_properties() + SoftDeleteIF.display_exclude_properties()

    @classmethod
    def cu_exclude_properties(cls) :
        return CreatedTimeBaseModel.cu_exclude_properties() + SoftDeleteIF.cu_exclude_properties()


class SoftDeleteCreatedTimeNamedBaseModel(SoftDeleteCreatedTimeBaseModel, NameIF):
    @classmethod
    def uniqueness_properties(cls) :
        return SoftDeleteCreatedTimeBaseModel.uniqueness_properties() + NameIF.uniqueness_properties()


class BaseModelPoly(DatedBaseModel):
    @classmethod
    def dbModel(cls):
        return polymodel.PolyModel
    
    @classmethod
    def display_exclude_properties(cls) :
        return DatedBaseModel.display_exclude_properties() + ['_class']

    @classmethod
    def cu_exclude_properties(cls) :
        return DatedBaseModel.cu_exclude_properties() + ['_class']
    

class NamedBaseModelPoly(BaseModelPoly, NameIF):
    @classmethod
    def uniqueness_properties(cls) :
        return BaseModelPoly.uniqueness_properties() + NameIF.uniqueness_properties()


class SoftDeleteBaseModelPoly(BaseModelPoly, SoftDeleteIF):
    @classmethod
    def display_exclude_properties(cls) :
        return BaseModelPoly.display_exclude_properties() + SoftDeleteIF.display_exclude_properties()

    @classmethod
    def cu_exclude_properties(cls) :
        return BaseModelPoly.cu_exclude_properties() + SoftDeleteIF.cu_exclude_properties()


class SoftDeleteNamedBaseModelPoly(SoftDeleteBaseModelPoly, NameIF):
    @classmethod
    def uniqueness_properties(cls) :
        return SoftDeleteBaseModelPoly.uniqueness_properties() + NameIF.uniqueness_properties()


class SoftDeleteModelPolySmall(SoftDeleteIF):
    model = db.ReferenceProperty(indexed=False)
    
    @classmethod
    def syncAttributes(cls):
        return []
    
    def modelKey(self):
        if self.model is None :
            return None
        if isinstance(self.model, db.Key) :
            return self.model
        else :
            return self.model.key()
        
    def modelKeyStr(self):
        key = self.modelKey()
        if key is None :
            return None
        return str(key)


MAX_MINUTE_BRACKET = 60
MAX_HOUR_BRACKET = 168
MAX_DAY_BRACKET = 90


class BaseCounterIF(db.Model):
    """
    hourBracket: '((year,month,day,hour),[count1,count2,count3,..., up to MAX_HOUR_BRACKET])', assuming UTC
    dayBracket: '((year,month,day),[count1,count2,count3,..., up to MAX_DAY_BRACKET])', assuming user time zone
    """
    minuteBracket = db.TextProperty()
    hourBracket = db.TextProperty()
    dayBracket = db.TextProperty()
        
    """
    lastUpdateHour and lastUpdateMinute correspond to each time unit values in utc time. 
    Other lastUpdateTimeFrame properties correspond to each time unit values in user local time. 
    """
    lastUpdateMinute = db.IntegerProperty(indexed=False)
    lastUpdateHour = db.IntegerProperty()
    lastUpdateDay = db.IntegerProperty()
    lastUpdateWeek = db.IntegerProperty()
    lastUpdateMonth = db.IntegerProperty()
    lastUpdateYear = db.IntegerProperty(indexed=False)

    minute = db.IntegerProperty(default=0,required=True, indexed=False)
    hour = db.IntegerProperty(default=0, required=True)
    day = db.IntegerProperty(default=0, required=True)    
    week = db.IntegerProperty(default=0, required=True)    
    month = db.IntegerProperty(default=0, required=True)    
    year = db.IntegerProperty(default=0, required=True)    
    life = db.IntegerProperty(default=0, required=True)    

    def yesterday_count(self, now=None):
        if self.dayBracket is None:
            return 0
        last_count_day_info, counts = eval(self.dayBracket)
        last_count_day = datetime.date(year=last_count_day_info[0], month=last_count_day_info[1], day=last_count_day_info[2])
        if now is None:
            now = ctz_util.uspacificnow()
        today = datetime.date(year=now.year, month=now.month, day=now.day)
        day_diff = (today - last_count_day).days
        if day_diff == 0 and len(counts) > 1:
            return counts[-2]
        elif day_diff == 1 and len(counts) > 0:
            return counts[-1]
        else:
            return 0
        

class BaseCounterNoIndexIF(db.Model):
    minuteBracket = db.TextProperty()
    hourBracket = db.TextProperty()
    dayBracket = db.TextProperty()
        
    lastUpdateMinute = db.IntegerProperty(indexed=False)
    lastUpdateHour = db.IntegerProperty(indexed=False)
    lastUpdateDay = db.IntegerProperty(indexed=False)
    lastUpdateWeek = db.IntegerProperty(indexed=False)
    lastUpdateMonth = db.IntegerProperty(indexed=False)
    lastUpdateYear = db.IntegerProperty(indexed=False)

    minute = db.IntegerProperty(default=0,required=True, indexed=False)
    hour = db.IntegerProperty(default=0, required=True, indexed=False)
    day = db.IntegerProperty(default=0, required=True, indexed=False)    
    week = db.IntegerProperty(default=0, required=True, indexed=False)    
    month = db.IntegerProperty(default=0, required=True, indexed=False)    
    year = db.IntegerProperty(default=0, required=True, indexed=False)    
    life = db.IntegerProperty(default=0, required=True, indexed=False)    


class BaseCounterImpl():
    @classmethod
    def get_or_insert_update(cls, key_names, parent=None):
        """
        overriding the standard Model.get_by_key_name() with an extra update call.
        """
        counter = cls.get_or_insert(key_names, parent=parent)
        if counter is None :
            return None
        else :
            return counter.update()
        
    def update(self, modelUser=None):
        """
        This function updates counter values based on last updated time. 
        Save one memcache.get() or db.get() by passing in the modelUser. 
        If user is not passed in, the current user is used, and validate against the counter parent.
        """
        return self.increment(modelUser,size=0)
        
    def minuteCounters(self):
        if self.minuteBracket is None:
            return []
        else:
            return eval(self.minuteBracket)[1]
        
    def hourCounters(self):
        if self.hourBracket is None:
            return []
        else :
            return eval(self.hourBracket)[1]

    def dayCounters(self):
        if self.dayBracket is None:
            return []
        else :
            return eval(self.dayBracket)[1]

    def normalizedCounters(self, time_unit, units=None):
        clickTime = datetime.datetime.utcnow()
        if time_unit==core_const.TIME_UNIT_MINUTE :
            if units is None:
                return self.normalizedMinuteCounters(clickTime)
            else:
                return self.normalizedMinuteCounters(clickTime,units)
        if time_unit==core_const.TIME_UNIT_HOUR :
            if units is None:
                return self.normalizedHourCounters(clickTime)
            else :
                return self.normalizedHourCounters(clickTime,units)
        else : 
            if units is None:
                return self.normalizedDayCounters(clickTime,user=None)
            else :
                return self.normalizedDayCounters(clickTime,user=None,units=units)

    def normalizedMinuteCounters(self, clickTime, units=MAX_MINUTE_BRACKET):
        return self._normalizedCounters(self.minuteCounters(), self._minuteDiff(clickTime), units)
    
    def normalizedHourCounters(self, clickTime, units=MAX_HOUR_BRACKET):
        return self._normalizedCounters(self.hourCounters(), self._hourDiff(clickTime), units)
    
    def normalizedDayCounters(self, clickTime, user, units=MAX_DAY_BRACKET):
        if user is None:
            user = get_user()
        return self._normalizedCounters(self.dayCounters(), self._dayDiff(clickTime,user), units)

    def stripCounters(self, counterList):
        """
        Trim all leading 0 counters.
        """
        if counterList is None :
            return []
        
        index = 0
        for i in range(0, len(counterList)) :
            if counterList[i]!=0 :
                index = i
                break
        return counterList[index:]
    
    def stripCountersAt(self, counterList):
        """
        Trim all leading 0 counters.
        """
        if counterList is None :
            return []
        
        index = 0
        for i in range(0, len(counterList)) :
            if counterList[i][0]!=0 :
                index = i
                break
        return counterList[index:]

    def increment(self, user=None, size=1,clickTime=None):
        if clickTime is None :
            clickTime = datetime.datetime.utcnow() 
        if user is None:
            user = get_user()
        utcthen = self._utcThen() 
        usernow = ctz_util.to_tz(clickTime, user.timeZone)
        userthen = ctz_util.to_tz(utcthen, user.timeZone)
        
        self.lastUpdateMinute = datetimeparser.intMinute(clickTime)
        self.lastUpdateHour = datetimeparser.intHour(clickTime)
        self.lastUpdateDay = datetimeparser.intDay(usernow)
        self.lastUpdateWeek = datetimeparser.intWeek(usernow)
        self.lastUpdateMonth = datetimeparser.intMonth(usernow)
        self.lastUpdateYear = datetimeparser.intYear(usernow)
        
        #update minute bracket
        newMinuteInfo = (clickTime.year, clickTime.month, clickTime.day, clickTime.hour,clickTime.minute)
        newMinuteCounters = self.normalizedMinuteCounters(clickTime,MAX_MINUTE_BRACKET)
        newMinuteCounters[-1] += size
        self.minuteBracket = str((newMinuteInfo,self.stripCounters(newMinuteCounters)))
        
        # update hour bracket
        newHourInfo = (clickTime.year, clickTime.month, clickTime.day, clickTime.hour)
        newHourCounters = self.normalizedHourCounters(clickTime,MAX_HOUR_BRACKET)
        newHourCounters[-1] += size
        self.hourBracket = str((newHourInfo,self.stripCounters(newHourCounters)))

            
        # update day bracket
        newDayInfo = (usernow.year, usernow.month, usernow.day)
        newDayCounters = self.normalizedDayCounters(clickTime,user,MAX_DAY_BRACKET)
        newDayCounters[-1] += size
        self.dayBracket = str((newDayInfo,self.stripCounters(newDayCounters)))
        
        if datetimeparser.isMinuteDiff(userthen, usernow) :
            self.minute = size
        else :
            self.minute += size
            
        if datetimeparser.isHourDiff(userthen, usernow) :
            self.hour = size
        else :
            self.hour += size

        if datetimeparser.isDayDiff(userthen, usernow) :
            self.day = size
        else :
            self.day += size

        if datetimeparser.isWeekDiff(userthen, usernow) :
            self.week = size
        else :
            self.week += size
        
        if datetimeparser.isMonthDiff(userthen, usernow) :
            self.month = size
        else :
            self.month += size
        
        if datetimeparser.isYearDiff(userthen, usernow) :
            self.year = size
        else :
            self.year += size
        
        self.life += size
        
        return self
    
    def _utcThen(self):
        if self.minuteBracket is None :
            return common_const.EARLIEST_TIME
        minuteInfo, counters = eval(self.minuteBracket)
        logging.debug("Minute counters: %s", str(counters))
        return datetime.datetime(year=minuteInfo[0], month=minuteInfo[1], day=minuteInfo[2], hour=minuteInfo[3],minute=minuteInfo[4])

    def _minuteDiff(self,clickTime):
        utcthen = self._utcThen()
        dayDiff = (clickTime-utcthen).days
        secondDiff = (clickTime-utcthen).seconds
        return dayDiff*24*60 + secondDiff/60
            
    def _hourDiff(self,clickTime):
        if self.hourBracket is None :
            return MAX_HOUR_BRACKET
        lastCounterHourInfo, counters = eval(self.hourBracket)
        logging.debug("Hourly counters: %s", str(counters))
        lastCounterHour = datetime.datetime(year=lastCounterHourInfo[0], month=lastCounterHourInfo[1], day=lastCounterHourInfo[2],hour=lastCounterHourInfo[3]) 
        dayDiff = (clickTime-lastCounterHour).days
        secondDiff = (clickTime-lastCounterHour).seconds
        hourDiff = dayDiff*24 + secondDiff/3600        
        return hourDiff
    
    def _dayDiff(self,clickTime,user):
        if self.dayBracket is None :
            return MAX_DAY_BRACKET
        lastCounterDayInfo, counters = eval(self.dayBracket)
        logging.debug("Daily counters: %s", str(counters))
        lastCounterDay = datetime.date(year=lastCounterDayInfo[0], month=lastCounterDayInfo[1], day=lastCounterDayInfo[2])
        usernow = ctz_util.to_tz(clickTime, user.timeZone)
        today = datetime.date(year=usernow.year, month=usernow.month, day=usernow.day)
        return (today - lastCounterDay).days
    
    def _normalizedCounters(self, counters, unitDiff, units):
        if unitDiff < 0 :
            """
            This could happen when user changed his/her time zone setting.
            """
            unitDiff = 0
            
        if unitDiff>=units:
            counters = []
        else :
            cutOffIndex = len(counters) - (units - unitDiff)
            if cutOffIndex >= 0 :
                counters = counters[cutOffIndex:]
            counters.extend([0] * unitDiff)
        if len(counters) < units :
            paddingLeft = [0] * (units - len(counters))
            counters = paddingLeft + counters
        return counters


class BaseCounter(DatedBaseModel, BaseCounterImpl, BaseCounterIF):
    pass

    
class BaseCounterNoIndex(DatedNoIndexBaseModel, BaseCounterImpl, BaseCounterNoIndexIF):
    pass

    
class ClickCounterImpl():
    def incrementByReferrerAndCountry(self,user,referrer,country,clickTime=None):        
        self.checkCountersDataAndModify()
        
        self.increment(user,size=1,clickTime=clickTime)        
        self.incrementReferer(referrer)
        self.incrementGeoByCode(country)

    def checkCountersDataAndModify(self,report=False):
        if report:
            counterMap=eval(self.countryBracket)
            country_total=0
            for key in counterMap.keys():
                country_total+=counterMap[key]
            difference=self.life-country_total
            if difference!=0:
                counterMap["us"]=counterMap.setdefault("us",0)+difference
                
            referrerMap=self.preModify(eval(self.referrerBracket))
            referrer_total=0
            for key in referrerMap.keys(): 
                referrer_total+=int(referrerMap[key])
                
            difference=self.life-referrer_total
            if difference!=0:
                referrerMap["direct"]=referrerMap.setdefault("direct",0)+difference
                self.direct+=difference
            
            self.countryBracket=str(counterMap)
            self.referrerBracket=str(referrerMap)
            db.put(self)
                
    def preModify(self,referrerMap):
        if "twitter" in referrerMap:
            if referrerMap.setdefault("twitter.com",0)<self.twitter:
                self.twitter+=referrerMap["twitter"]
                referrerMap["twitter.com"]=self.twitter
                del referrerMap["twitter"]
        if "facebook" in referrerMap:
            if referrerMap.setdefault("facebook.com",0)<self.facebook:
                self.facebook+=referrerMap["facebook"]
                referrerMap["facebook.com"]=self.facebook
                del referrerMap["facebook"]
        referrerMap["direct"]=self.direct
        return referrerMap        
        

class ClickCounter(BaseCounter, ClickCounterImpl, ReferrerCounterIF, GeoCounterIF):
    pass


class ClickCounterNoIndex(BaseCounterNoIndex, ClickCounterImpl, ReferrerCounterIF, GeoCounterIF):
    pass


def isDeleted(obj):
    if obj is None or hasattr(obj, 'deleted') and obj.deleted :
        return True
    else :
        return False


def validateUniquenessByModel(obj, propertyOrList, parent=None):
    """
    obj - the db model object
    propertyOrList - uniqueness properties to validate, one string or list of string
    """
    if parent is None :
        parent = get_user()
    model = type(obj)
    updateKey = None
    if obj.is_saved() :
        updateKey = obj.key()
    if type(propertyOrList)==list :
        properties = propertyOrList
    else :
        properties = [propertyOrList]
    for prop in properties :
        if parent is None :
            query_base = model.all()
        else :
            query_base = model.all().ancestor(parent)
        if hasattr(model, 'deleted') :
            query_base = query_base.filter('deleted', False)
        query = query_base.filter(prop, getattr(obj,prop))
        matched = query.fetch(limit=2)
        violated = False
        if updateKey is None :
            if len(matched) > 0 :
                violated = True
        else :
            token_map = {}
            for token in matched :
                token_map[token.key()] = token
            token_map.pop(updateKey, None)
            if len(token_map) > 0 :
                violated = True
        if violated :
            raise api_error.ApiError(api_error.API_ERROR_DATA_UNIQUENESS, model.__name__, prop, getattr(obj,prop))


def validateUniqueness(params, propertyOrList, model, key=None, parent=None):
    """
    params - input params
    model - the db model
    propertyOrList - uniqueness properties to validate, one string or list of string
    key - the db.Key or string in case of update, None in case of create
    """
    updateKey = None
    if key is not None :
        updateKey = str(key)

    if type(propertyOrList)==list :
        properties = propertyOrList
    else :
        properties = [propertyOrList]
        
    for prop in properties :
        if not params.has_key(prop) : continue

        value = params.get(prop, None)
        if parent is None :
            query_base = model.all()
        else :
            query_base = model.all().ancestor(parent)
        if hasattr(model, 'deleted') :
            query_base = query_base.filter('deleted', False)
        query = query_base.filter(prop, value)
        matched = query.fetch(limit=2)
        violated = False
        if updateKey is None :
            if len(matched) > 0 :
                violated = True
        else :
            token_map = {}
            for token in matched :
                token_map[str(token.key())] = token
            token_map.pop(updateKey, None)
            if len(token_map) > 0 :
                violated = True
        if violated :
            raise api_error.ApiError(api_error.API_ERROR_DATA_UNIQUENESS, model.__name__, prop, value)
    

def parseList(value, item_type):
    """
    Utility to parse a list of strings into a list of objects of item_type
    """
    if item_type == datastore_types.Key :
        return parseKeyList(value)
    if value is None or value == [] : return []
    if type(value)==str or type(value)==unicode : return [item_type(value)]
    if type(value[0]) not in (str, unicode) : return value
    keys = []
    for token in value :
        if len(token.strip())>0 :
            keys.append(item_type(token.strip()))
    return keys


def parseKeyList(keyIdOrList):
    """
    Utility to parse a list of key ids into a list of key objects
    """
    if (keyIdOrList is None) : return []
    if (type(keyIdOrList)==str or type(keyIdOrList)==unicode) : return [db.Key(keyIdOrList)]
    keys = []
    for token in keyIdOrList :
        keyId = token.strip()
        if len(keyId)>0 :
            keys.append(db.Key(keyId))
    return keys

def parseKeyOrModel(keyIdOrKeyOrModel):
    """
    keyIdOrKeyOrModel - one of the 3 types: 
        1. str or unicode, representing a key id
        2. db.Key
        3. db.Model
    return - db.Key or db.Model
    """
    if keyIdOrKeyOrModel is None : 
        return None
    if type(keyIdOrKeyOrModel) in (str, unicode) : 
        return db.Key(keyIdOrKeyOrModel)
#    """ There is a problem. Sometimes the keyIdOrKeyOrModel is a PropertiedClass. """
#    if type(keyIdOrKeyOrModel) not in (db.Key, db.Model) : 
#        raise api_error.ApiError(api_error.API_ERROR_UNKNOWN, "Invalid key or model input: '%s'" % keyIdOrKeyOrModel)
    return keyIdOrKeyOrModel


def parseStringList(strOrList):
    """
    Utility to normalize a string or a string list into a list of strings
    """
    if (strOrList is None) : return []
    if (type(strOrList)==str or type(strOrList)==unicode) : return [strOrList]
    strs = []
    for token in strOrList :
        if len(token.strip())>0 :
            strs.append(token.strip())
    return strs


def parseBool(strOrBool):
    """
    Utility to normalize a string or a bool value to a bool value.
    """
    if (strOrBool is None) : return None
    if type(strOrBool)==bool :
        return strOrBool
    else :
        value = eval(strOrBool)
        if type(value)==bool :
            return value
        else :
            raise api_error.ApiError(api_error.API_ERROR_UNKNOWN, "Invalid boolean input value : %s" % strOrBool)


def parseByteString(string):
    """
    Utility to parse an encoded value of byte string into a byte string
    """
    if string is None : return None
    raise ApiError(api_error.API_ERROR_DATA_TYPE_NOT_SUPPORTED, db.ByteStringProperty)


def parseBlob(string):
    """
    Utility to parse an encoded value of byte string into a blob
    """
    if string is None : return None
    raise ApiError(api_error.API_ERROR_DATA_TYPE_NOT_SUPPORTED, db.BlobProperty)


def parseDatetime(string, fallback=None):
    """
    Utility to parse a string of date time to date time value
    """
    if string is None : return fallback
    if isinstance(string, datetime.datetime) : return string
    return datetimeparser.parseDateTime(string)


def parseDate(string):
    """
    Utility to parse a string of date to date value
    """
    if string is None : return None
    if isinstance(string, datetime.date) : return string
    return datetime.date(string)


def parseTime(string):
    """
    Utility to parse a string of time to time value
    """
    if string is None : return None
    return datetime.time(string)


def parseRating(string):
    """
    Utility to parse a string of rating integer to a gae Rating object
    """
    if string is None : return None
    return db.Rating(int(string))


PROPERTY_PARSER_MAP = {
    db.StringProperty:unicode,
    db.TextProperty:unicode, 
    db.LinkProperty:unicode, 
    db.Text:unicode, 
    db.Category:unicode, 
    db.Link:unicode, 
    db.Email:unicode,
    db.EmailProperty:unicode, 
    db.IM:unicode, 
    db.PhoneNumber:unicode, 
    db.PostalAddress:unicode,    
    db.StringListProperty:parseStringList,
    db.ListProperty:parseList, 
    db.BooleanProperty:bool,
    db.IntegerProperty:long,
    db.FloatProperty:float,
    db.DateTimeProperty:parseDatetime,
    db.DateProperty:parseDate,
    db.TimeProperty:parseTime,
    db.ByteStringProperty:parseByteString,
    db.BlobProperty:parseBlob,
    db.ReferenceProperty:parseKeyOrModel,
    db.SelfReferenceProperty:parseKeyOrModel,
    db.RatingProperty:parseRating,
    db.GeoPtProperty:None,
    db.IMProperty:None,
                       }


def parseValue(value, prop):
    """
    Utility to parse a value of string or string list to the data type according to the input prop.
    """
    if value is None :
        return None
    property_type = type(prop)
    parser = PROPERTY_PARSER_MAP.get(property_type)
    if parser == None :
        raise ApiError(api_error.API_ERROR_DATA_TYPE_NOT_SUPPORTED, property_type)
    if parser == parseList :
        return parseList(value, prop.item_type)
    return parser(value)
  

def put(objects, batch_size=100):
    batch_count = len(objects)/batch_size
    if len(objects) % batch_size > 0:
        batch_count += 1
    success_count = 0
    for i in range(batch_count):
        index = i * batch_size
        batch = objects[index : index + batch_size]
        try:
            db.put(batch)
            logging.debug("db_base.put() updated %d objects at index %d." % (len(batch), index))
            success_count += len(batch)
        except:
            logging.error("db_base.put() failed updating %d objects at index %d." % (len(batch), index))
    logging.info("db_base.put() updated %d objects out of total %d." % (success_count, len(objects)))
            
    
def txn_put(objects):
    def txn_put_exec(objects):
        db.put(objects)
    db.run_in_transaction(txn_put_exec, objects)    


def txn_delete(objects):
    def txn_delete_exec(objects):
        db.delete(objects)
    db.run_in_transaction(txn_delete_exec, objects)    

    
class RatingCounter(CreatedTimeBaseModel):
    modifiedTime = db.DateTimeProperty(auto_now=True)
    minuteBracket = db.TextProperty()
    hourBracket = db.TextProperty()
    dayBracket = db.TextProperty()
    
    lastUpdateMinute = db.IntegerProperty(indexed=False)
    lastUpdateHour = db.IntegerProperty(indexed=False)
    lastUpdateDay = db.IntegerProperty(indexed=False)
    lastUpdateWeek = db.IntegerProperty(indexed=False)
    lastUpdateMonth = db.IntegerProperty(indexed=False)
    lastUpdateYear = db.IntegerProperty(indexed=False)
    
    c60m = db.IntegerProperty(default=0, indexed=False)
    c24h = db.IntegerProperty(default=0, indexed=False)    
    c7d = db.IntegerProperty(default=0, indexed=False)    
    c30d = db.IntegerProperty(default=0, indexed=False)
    c365d = db.IntegerProperty(default=0, indexed=False)    
    
    def minuteCounters(self):
        if self.minuteBracket is None:
            return []
        else:
            return eval(self.minuteBracket)[1]
        
    def hourCounters(self):
        if self.hourBracket is None:
            return []
        else :
            return eval(self.hourBracket)[1]

    def dayCounters(self):
        if self.dayBracket is None:
            return []
        else :
            return eval(self.dayBracket)[1]
    
    def yesterday_count(self, now = None):
        if self.dayBracket is None:
            return 0
        last_count_day_info, counts = eval(self.dayBracket)
        last_count_day = datetime.date(year=last_count_day_info[0], month=last_count_day_info[1], day=last_count_day_info[2])
        if now is None:
            now = ctz_util.uspacificnow()
        today = datetime.date(year=now.year, month=now.month, day=now.day)
        day_diff = (today - last_count_day).days
        if day_diff == 0 and len(counts) > 1:
            return counts[-2]
        elif day_diff == 1 and len(counts) > 0:
            return counts[-1]
        else:
            return 0
    
    def _minuteDiff(self,clickTime):
        if self.minuteBracket is None :
            return MAX_MINUTE_BRACKET
        lastCounterMinuteInfo = eval(self.minuteBracket)[0]
        lastCounterMinute = datetime.datetime(year=lastCounterMinuteInfo[0], month=lastCounterMinuteInfo[1], day=lastCounterMinuteInfo[2],hour=lastCounterMinuteInfo[3],minute=lastCounterMinuteInfo[4])
        dayDiff = (clickTime-lastCounterMinute).days
        secondDiff = (clickTime-lastCounterMinute).seconds
        return dayDiff*24*60 + secondDiff/60
    
    def _hourDiff(self,clickTime):
        if self.hourBracket is None :
            return MAX_HOUR_BRACKET
        lastCounterHourInfo = eval(self.hourBracket)[0]
        lastCounterHour = datetime.datetime(year=lastCounterHourInfo[0], month=lastCounterHourInfo[1], day=lastCounterHourInfo[2],hour=lastCounterHourInfo[3]) 
        dayDiff = (clickTime-lastCounterHour).days
        secondDiff = (clickTime-lastCounterHour).seconds
        hourDiff = dayDiff*24 + secondDiff/3600        
        return hourDiff
    
    def _dayDiff(self,clickTime):
        if self.dayBracket is None :
            return MAX_DAY_BRACKET
        lastCounterDayInfo = eval(self.dayBracket)[0]
        lastCounterDay = datetime.date(year=lastCounterDayInfo[0], month=lastCounterDayInfo[1], day=lastCounterDayInfo[2])
        today = datetime.date(year=clickTime.year, month=clickTime.month, day=clickTime.day)
        return (today - lastCounterDay).days
    
    def normalizedMinuteCounters(self, clickTime, units=MAX_MINUTE_BRACKET):
        return self._normalizedCounters(self.minuteCounters(), self._minuteDiff(clickTime), units)
    
    def normalizedHourCounters(self, clickTime, units=MAX_HOUR_BRACKET):
        return self._normalizedCounters(self.hourCounters(), self._hourDiff(clickTime), units)
    
    def normalizedDayCounters(self, clickTime, units=MAX_DAY_BRACKET):
        return self._normalizedCounters(self.dayCounters(), self._dayDiff(clickTime), units)
    
    def _normalizedCounters(self, counters, unitDiff, units):
        if unitDiff < 0 :
            logging.warn("Something is wrong with datetime! Counter key: %s" % (self.key().id_or_name(),))
            unitDiff = 0
            
        if unitDiff>=units:
            counters = []
        else :
            cutOffIndex = len(counters) - (units - unitDiff)
            if cutOffIndex >= 0 :
                counters = counters[cutOffIndex:]
            counters.extend([0] * unitDiff)
        if len(counters) < units :
            paddingLeft = [0] * (units - len(counters))
            counters = paddingLeft + counters
        return counters
    
    def stripCounters(self, counterList):
        if counterList is None :
            return []
        
        index = 0
        for i in range(0, len(counterList)) :
            if counterList[i]!=0 :
                index = i
                break
        return counterList[index:]
    
    def increment(self,size=1,clickTime=None):
        if clickTime is None :
            clickTime = datetime.datetime.utcnow()
            
        self.lastUpdateMinute = datetimeparser.intMinute(clickTime)
        self.lastUpdateHour = datetimeparser.intHour(clickTime)
        self.lastUpdateDay = datetimeparser.intDay(clickTime)
        self.lastUpdateWeek = datetimeparser.intWeek(clickTime)
        self.lastUpdateMonth = datetimeparser.intMonth(clickTime)
        self.lastUpdateYear = datetimeparser.intYear(clickTime)
        
        newMinuteInfo = (clickTime.year, clickTime.month, clickTime.day, clickTime.hour,clickTime.minute)
        newMinuteCounters = self.normalizedMinuteCounters(clickTime)
        newMinuteCounters[-1] += size
        newMinuteCounters = self.stripCounters(newMinuteCounters)
        self.minuteBracket = str((newMinuteInfo,newMinuteCounters))
        
        newHourInfo = (clickTime.year, clickTime.month, clickTime.day, clickTime.hour)
        newHourCounters = self.normalizedHourCounters(clickTime)
        newHourCounters[-1] += size
        newHourCounters = self.stripCounters(newHourCounters)
        self.hourBracket = str((newHourInfo,newHourCounters))
        
        newDayInfo = (clickTime.year, clickTime.month, clickTime.day)
        newDayCounters = self.normalizedDayCounters(clickTime)
        newDayCounters[-1] += size
        newDayCounters = self.stripCounters(newDayCounters)
        self.dayBracket = str((newDayInfo,newDayCounters))
        
        self.rateHour(newMinuteCounters)
        self.rateDay(newHourCounters)
        self.rateWeek(newDayCounters)
        self.rateMonth(newDayCounters)
        self.rateYear(newDayCounters)
     
        
    def rateHour(self,minuteCounters):
        if len(minuteCounters) > 0:
            count = min(len(minuteCounters),60)
            hour = 0
            for i in range(1,count+1):
                hour += minuteCounters[-i]
            self.c60m = hour
        
        
    def rateDay(self,hourCounters):
        if len(hourCounters) > 0 :
            count = min(len(hourCounters),24)
            day = 0
            for i in range(1,count+1):
                day += hourCounters[-i]
            self.c24h = day
            
    def rateWeek(self,dayCounters):
        if len(dayCounters) > 0 :
            count = min(len(dayCounters),7)
            week = 0
            for i in range(1,count+1):
                week += dayCounters[-i]
            self.c7d = week
            
    def rateMonth(self,dayCounters):
        if len(dayCounters) > 0 :
            count = min(len(dayCounters),30)
            month = 0
            for i in range(1,count+1):
                month += dayCounters[-i]
            self.c30d = month
            
    def rateYear(self,dayCounters):
        if len(dayCounters) > 0 :
            count = min(len(dayCounters),365)
            year = 0
            for i in range(1,count+1):
                year += dayCounters[-i]
            self.c365d = year
            
    def setHour(self):
        minuteCounters = self.normalizedMinuteCounters(datetime.datetime.utcnow())
        self.rateHour(minuteCounters)
        return self.c60m
        
    def setDay(self):
        hourCounters = self.normalizedHourCounters(datetime.datetime.utcnow())
        self.rateDay(hourCounters)
        return self.c24h
        
    def setWeek(self):
        dayCounters = self.normalizedDayCounters(datetime.datetime.utcnow())
        self.rateWeek(dayCounters)
        return self.c7d
        
    def setMonth(self):
        dayCounters = self.normalizedDayCounters(datetime.datetime.utcnow())
        self.rateMonth(dayCounters)
        return self.c30d
            
    def setYear(self):
        dayCounters = self.normalizedDayCounters(datetime.datetime.utcnow())
        self.rateYear(dayCounters)
        return self.c365d


class StatsCounterIF(DatedNoIndexBaseModel):
    """
    Normally, each text attr is in this format: "((year,month,day,...),[count1,count2,count3,...])", using US/Pacific time zone.
    """
    PADDING_ZERO = 0
    PADDING_OLD_VALUE = 1
    PADDING_NEW_VALUE = 2

    def getCounts(self, attr):
        text = getattr(self, attr, None)
        if text:
            dateInfo, counts = eval(text)
            return (self.tuple_2_date(dateInfo), counts)
        return None, None

    def setCount(self, attr, count, date, padding=PADDING_ZERO):
        if count is not None: count = int(count)
        date = self.period_date(date)
        oldDate, oldCounts = self.getCounts(attr)
        if oldDate is None or len(oldCounts)==0:
            newDate = date
            newCounts = [count]
        else:
            delta = self.period_delta(date, oldDate)
            if delta>0:
                paddings = self.paddings(padding, delta-1, oldValue=oldCounts[-1])
                newDate = date
                newCounts = oldCounts + paddings + [count] 
            else:
                newDate = oldDate
                oldCounts[delta-1] = count
                newCounts = oldCounts
        newCounts = newCounts[-self.MAX_PERIODS:]
        newText = self.text(newDate, newCounts)
        setattr(self, attr, newText)
    
    def totalCounts(self, attr, periods=None):
        if periods is None: periods = self.default_periods()
        counts = self.getCounts(attr)[1]
        if counts is None:
            return 0
        return sum(counts[-periods:])
    
    def cleanCounts(self, attr, date):
        """ Clean all counts of specified attr after specified date. """
        curDate, curCounts = self.getCounts(attr)
        if curDate is None or curDate<=date:
            return
        delta = self.period_delta(curDate, date)
        setattr(self, attr, self.text(date, curCounts[:-delta]))

    @classmethod
    def default_periods(cls):
        return cls.DEFAULT_PERIODS
    
    @classmethod
    def period_date(cls, date):
        pass
                
    @classmethod
    def period_delta(cls, new_date, old_date):
        pass
                
    @classmethod
    def text(cls, date, counts):
        pass
                
    @classmethod
    def paddings(cls, padding, length, oldValue=None, newValue=None):
        if padding==cls.PADDING_ZERO:
            return [0]*length
        elif padding==cls.PADDING_OLD_VALUE:
            return [oldValue]*length
        elif padding==cls.PADDING_NEW_VALUE:
            return [newValue]*length
        else:
            return []

    @classmethod
    def tuple_2_date(cls, dateInfo):
        """ dateInfo in (year, month, day, ...) tuple """
        pass

    @classmethod
    def date_2_tuple(cls, date):
        pass

    
class StatsIF(BaseModel):
    QUERY_LIMIT = 100
    QUERY_LIMIT_KEYS_ONLY = 1000

    def reset(self):
        pass
    
    @classmethod
    def counter_model(cls):
        pass
    
    def get_or_insert_counter(self):
        return self.counter_model().get_or_insert(self.key().name(), parent=self)
    

class HourlyStatsCounterIF(StatsCounterIF):
    """
    Period key is (year,month,day,hour).
    """
    DEFAULT_PERIODS = 24
    MAX_PERIODS = 120
    
    @classmethod
    def period_date(cls, date):
        return datetimeparser.truncate_2_hour(date)

    @classmethod
    def period_delta(cls, new_date, old_date):
        return datetimeparser.timedelta_in_hours(new_date - old_date)
                
    @classmethod
    def text(cls, date, counts):
        return "((%d,%d,%d,%d),%s)" % (date.year, date.month, date.day, date.hour, str(counts))
                
    @classmethod
    def tuple_2_date(cls, dateInfo):
        """ dateInfo in (year, month, day, hour) tuple """
        year, month, day, hour = dateInfo
        return datetime.datetime(year=year, month=month, day=day, hour=hour)

    @classmethod
    def date_2_tuple(cls, date):
        return (date.year, date.month, date.day, date.hour)

    
class HourlyStatsIF(StatsIF):
    updd = db.DateTimeProperty(indexed=False)

    def reset(self):
        self.updd = None


class DailyStatsCounterIF(StatsCounterIF):
    """
    Period key is (year,month,day).
    """
    DEFAULT_PERIODS = 30
    MAX_PERIODS = 120
    
    @classmethod
    def period_date(cls, date):
        return datetimeparser.truncate_2_day(date)

    @classmethod
    def period_delta(cls, new_date, old_date):
        return (new_date - old_date).days
                
    @classmethod
    def text(cls, date, counts):
        return "((%d,%d,%d),%s)" % (date.year, date.month, date.day, str(counts))
                
    @classmethod
    def tuple_2_date(cls, dateInfo):
        """ dateInfo in (year, month, day) tuple """
        year, month, day = dateInfo
        return datetime.date(year=year, month=month, day=day)

    @classmethod
    def date_2_tuple(cls, date):
        return (date.year, date.month, date.day)

    
class DailyStatsIF(StatsIF):
    updd = db.DateProperty(indexed=False)

    def reset(self):
        self.updd = None

