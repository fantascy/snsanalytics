import logging
from datetime import datetime, timedelta

from google.appengine.ext import db
from google.appengine.ext.db import polymodel

from search.core import SearchIndexProperty, porter_stemmer
from common.utils import string as str_util 
from sns.core.core import KeyName, User
from sns.core.base import DatedBaseModel, SoftDeleteNamedBaseModelPoly, SoftDeleteBaseModel, ClickCounter

from sns.email import consts as mail_const
from sns.camp.models import Campaign, Execution, Post
 
class MPost(Post):  
    @classmethod
    def keyNamePrefix(cls):
        return "MPost:"    
    
    
class EmailContactKeyName(KeyName):
    @classmethod
    def keyNamePrefix(cls):
        return "EmailContact:"

    @classmethod
    def normalizedName(cls, name):
        return str_util.strip(name.lower())


class EmailContact(DatedBaseModel, EmailContactKeyName):
    """
    email - email of contact
    If and only if both first name and last name are none, use full name.
    """
    email = db.EmailProperty()
    firstName = db.StringProperty()
    lastName = db.StringProperty()
    fullName = db.StringProperty()
    unsub = db.BooleanProperty(default=False)
    searchIndex = SearchIndexProperty(('email','firstName', 'lastName', 'fullName'), indexer=porter_stemmer,relation_index=False)


class EmailListKeyName(KeyName):
    
    @classmethod
    def keyNamePrefix(cls):
        return "EmailList:"
    
    
class EmailList(polymodel.PolyModel, SoftDeleteNamedBaseModelPoly, EmailListKeyName):
    type = db.IntegerProperty(default=mail_const.MAIL_LIST_TYPE_NORMAL, choices=mail_const.MAIL_LIST_TYPES)
    count = db.IntegerProperty(default=0)
    searchIndex = SearchIndexProperty(('name','description'), indexer=porter_stemmer,relation_index=False)
    
    def fetch_list(self, cursor=mail_const.EXEC_CURSOR_START ,limit=mail_const.EXEC_MAIL_LIST_LIMIT, type=None):
        cquery = []
        clist = []
        try:
            logging.info('Executing Campaigns:cursor: %s' % cursor) 
            if cursor == mail_const.EXEC_CURSOR_START:
                cquery = EmailContact.all().filter('unsub =', False).ancestor(self).order('email').fetch(limit) 
                logging.info('Executing Campaigns:cquery 1: %s' % cquery)  
            else:
                cquery = EmailContact.all().filter('unsub =', False).ancestor(self).filter('email >', cursor).order('email').fetch(limit)
                logging.info('Executing Campaigns:cquery 2: %s' % cquery) 
            for c in cquery:
                clist.append(c)
        except:
            logging.exception('EmailList.fetch_list Exception')
            pass
        return clist
  
  
class DynamicEmailList(EmailList):
    pass


class DefaultSystemEmailList(DynamicEmailList):
    
    def fetch_list(self, cursor=mail_const.EXEC_CURSOR_START ,limit=mail_const.EXEC_MAIL_LIST_LIMIT, type=None):
        ulist = None
        clist = []
        try:
            if type == None:
                ulist = User.all().filter('mail >', cursor).order('mail').fetch(limit)
            else:
                ulist = User.all().filter('mail >', cursor).filter(type + ' =', True).order('mail').fetch(limit)
            
            for u in ulist:
                if not u.mail == None:
                    fullName=unicode(u.mail) if u.name==None else u.name
                    c = EmailContact(parent=self, email=u.mail, fullName=fullName)
                    clist.append(c)
                if len(clist) == 0:
                    clist
        except Exception, (err_msg) :
            logging.info('fetch error : %s' %err_msg)
        return clist
            
            
class TestSystemEmailList(DynamicEmailList):
    
    def fetch_list(self, cursor=mail_const.EXEC_CURSOR_START ,limit=mail_const.EXEC_MAIL_LIST_LIMIT, type=None):
        ulist = None
        clist = []
        try:
            if type == None:
                ulist = User.all().filter('mail >', cursor).order('mail').fetch(limit)
            else:
                ulist = User.all().filter('mail >', cursor).filter(type + ' =', True).order('mail').fetch(limit)
            
            for u in ulist:
                if not u.mail == None:
                    fullName=unicode(u.mail) if u.name==None else u.name
                    c = EmailContact(parent=self, email=u.mail, fullName=fullName)
                    clist.append(c)
                if len(clist) == 0:
                    clist
        except Exception, (err_msg) :
            logging.info('fetch error : %s' %err_msg)
        return clist
        
        
    
class EmailTemplate(polymodel.PolyModel, SoftDeleteNamedBaseModelPoly):
    replyTo = db.ReferenceProperty(EmailContact, collection_name='reply_to')
    subject =db.StringProperty(required=True)
    textBody = db.TextProperty()
    htmlBody = db.TextProperty()
    type = db.StringProperty(default=mail_const.MAIL_TEMPLATE_TYPE_INIT, choices=mail_const.MAIL_TEMPLATE_TYPES)
    searchIndex = SearchIndexProperty(('name','description', 'subject'), indexer=porter_stemmer,relation_index=False)
    
    
    
class EmailListClickCounterKeyName(KeyName):
    
    @classmethod
    def keyNamePrefix(cls):
        return "EmailListCC:"
    
    
class EmailListClickCounter(ClickCounter, EmailListClickCounterKeyName):
    pass


class MailCampaign(Campaign):
    param = db.StringProperty(indexed=False)
    isDefault = db.BooleanProperty(required=True, default=False)
    event = db.StringProperty()
    sender = db.StringProperty(required=True, indexed=False)
    toLists = db.ListProperty(db.Key, indexed=False)
    toBlacklists = db.ListProperty(db.Key, indexed=False)
    actualRecipient = db.StringProperty(default=mail_const.NONE_MAIL_ACTUAL_RECIPIENT, indexed=False)
    

class MailExecution(Execution):
    """
    templateBody - stores pre-processing results of mail template body. One pre-processing example is short URL replacement.  
    """
    templateBody = db.TextProperty()
    success      = db.IntegerProperty(default=0)
    failed       = db.IntegerProperty(default=0)
    executingTime = db.DateTimeProperty(auto_now_add=True)
    event = db.StringProperty()
    dump = db.StringProperty()

    @classmethod
    def keyNamePrefix(cls):
        return "MailExecution:"    
    

class EmailContactClickCounterKeyName(KeyName):
    @classmethod
    def keyNamePrefix(cls):
        return "EmailContactCC:"

    @classmethod
    def normalizedName(cls, name):
        raise Exception("Unsupported operation! This key needs the following 3 piece info: email, mailListId, mailCampaignId")
        
    @classmethod
    def keyName(cls, email, mailListId, mailCampaignId):
        return "%s%s:%s:%s" % (cls.keyNamePrefix(), 
                               KeyName.normalizedName(email), 
                               KeyName.normalizedName(mailListId), 
                               KeyName.normalizedName(mailCampaignId),
                               ) 
    
    
class EmailContactClickCounter(DatedBaseModel, EmailContactClickCounterKeyName):
    """
    All objects of this model should have a key name, with format as defined in EmailContactClickCounterKeyName.
    email - value is the same as the one in mailContact, a redundant property for query purpose.
    """
    email = db.EmailProperty(required=True)
    list = db.ReferenceProperty(EmailList, required=True)
    campaign = db.ReferenceProperty(Campaign, required=True)
    count = db.IntegerProperty(default=0, required=True)
    
    
class EmailContactSubscribleStateKeyName(KeyName):
    
    @classmethod
    def keyNamePrefix(cls):
        return "EmailContactSS:"
    
    
class EmailContactSubscribleState(SoftDeleteBaseModel, EmailContactSubscribleStateKeyName):
    
    email = db.StringProperty()
    unsubTemplateid = db.StringProperty()
    unsubTemplateType = db.StringProperty()
    unsubCampaignId = db.StringProperty(indexed=False)
    unsub = db.BooleanProperty(default=False)

    
def getThisWeek(counter):
    return getWeekCounter(counter ,delta=0)

def getLastWeek(counter):
    return getWeekCounter(counter ,delta=1)
    
def getWeekCounter(counter ,delta=0):
    count = 0
    try:
        int(delta)
    except:
        return count
    today = datetime.utcnow() - timedelta(days=7*delta)
    if not counter == None and not counter.dayBracket == None:
        dayBracket = eval(counter.dayBracket)
        checkDay = datetime(year=dayBracket[0][0],month=dayBracket[0][1],day=dayBracket[0][2])
        flag = today.weekday()
        thatday = today - timedelta(7+flag)
        weekclicklist = []
        
        if (checkDay - thatday).days + 2 > len(dayBracket[1]) + 7:
            weekclicklist = []
        elif (checkDay - thatday).days >= 6:
            weekclicklist = dayBracket[1][-(checkDay-thatday).days-2:-(checkDay-thatday).days+5]
        elif (checkDay-thatday).days >= -1:
            if len(dayBracket[1]) >= (checkDay-thatday).days+2:
                weekclicklist = dayBracket[1][-(checkDay-thatday).days-2:]
            else:
                weekclicklist = dayBracket[1][:]
        else:
            pass
        for c in weekclicklist:
            count += c
            
    return count

def getAll(counter):
    
    if counter == None:
        return None
    return counter.life


class CounterPrototype():
    
    def __init__(self, counter, name=None):
        
        self.counter = counter
        self.lastWeek = getLastWeek(counter)
        self.thisWeek = getThisWeek(counter)
        self.all = None if counter == None else counter.life
        self.name = name
        
    def get_week(self, delta=0):
        return getWeekCounter(self.counter, delta=delta)    
    
    
class Report():
    
    def __init__(self):
        self.user = None
        self.tweets = None
        self.failures = None
        self.twitterAccounts = []
        self.facebookAccounts = []
        self.facebookPages = []
        self.testObj = []
    
    
class TimeOutException(Exception):
    pass    
        

        
    


