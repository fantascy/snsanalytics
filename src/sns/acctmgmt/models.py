from google.appengine.ext import db

from sns.core.core import KeyName, ChidKey
from sns.core.base import SoftDeleteNamedBaseModel, DatedNoIndexBaseModel, DatedBaseModel, CreatedTimeBaseModel
from common.utils import string as str_util
from sns.log import consts as log_const
from sns.acctmgmt import consts as acctmgmt_const
from sns.acctmgmt import utils as acctmgmt_util


class YahooKeyName(KeyName):
    @classmethod
    def keyNamePrefix(cls):
        return "Yahoo:"

    @classmethod
    def normalizedName(cls, name):
        return str_util.lower_strip(name)


class YahooAccount(SoftDeleteNamedBaseModel, YahooKeyName):
    """
    represent a yahoo account, the user name is defined in BaseIF
    """
    num = db.IntegerProperty()
    password = db.StringProperty(indexed=False)
    oldPassword = db.StringProperty(indexed=False)
    newPassword = db.StringProperty(indexed=False)
    passwordClue = db.StringProperty(indexed=False)
    state = db.IntegerProperty(default=acctmgmt_const.YAHOO_STATE_INIT, required=True)
    lastLoginTime = db.DateTimeProperty()
    lastPasswdChangeTime = db.DateTimeProperty()
    tHandle = db.StringProperty()
    tPassword = db.StringProperty(indexed=False)
    tOldPassword = db.StringProperty(indexed=False)
    tNewPassword = db.StringProperty(indexed=False)
    tState = db.IntegerProperty(default=acctmgmt_const.TWITTER_STATE_INIT, required=True)
    tLastLoginTime = db.DateTimeProperty()
    tLastPasswdChangeTime = db.DateTimeProperty()
    isCmp = db.BooleanProperty(default=False)
    
    def className(self):
        return self.__class__.__name__
    
    def oid(self):
        return self.key().name().split(':')[1]
    
    @classmethod
    def keyNamePrefix(cls):
        return "Yahoo:"

    @classmethod
    def normalizedName(cls, name):
        return str_util.strip(name.lower())

    @classmethod
    def cu_exclude_properties(cls):
        return SoftDeleteNamedBaseModel.cu_exclude_properties() + [
                'state', 
                'oldPassword', 
                'newPassword', 
                'lastLoginTime', 
                'lastPasswdChangeTime', 
                'tState', 
                'tOldPassword', 
                'tNewPassword', 
                'tLastLoginTime', 
                'tLastPasswdChangeTime',
                'createdTime',
                'modifiedTime',
                 ]
    
    @classmethod
    def update_exclude_properties(cls):
        return cls.cu_exclude_properties() + [
                'name', 
                'nameLower', 
                'password', 
                'passwordClue', 
                'tPassword', 
                 ]

    @classmethod
    def state_property(cls, acctType):
        return acctmgmt_util.state_property(acctType)

    @classmethod
    def time_property(cls, acctType, op):
        return acctmgmt_util.time_property(acctType, op)


class CmpAccountKeyName(KeyName):
    @classmethod
    def keyNamePrefix(cls):
        return "CMP:"

    @classmethod
    def normalizedName(cls, name):
        return str_util.lower_strip(name)


class CmpAccount(DatedNoIndexBaseModel):
    twitter_password = db.StringProperty(indexed=False, required=True)
    email_server = db.StringProperty(choices=log_const.EMAIL_SERVERS)
    email_password = db.StringProperty(indexed=False)
    old_email = db.EmailProperty()
    old_email_password = db.StringProperty(indexed=False)
    old_email_secqa = db.StringProperty(indexed=False)

    def __eq__(self, obj):
        if not isinstance(obj, self.__class__):
            return False
        return  self.key().name() == obj.key().name() and \
                self.twitter_password == obj.twitter_password and \
                self.email_server == obj.email_server and \
                self.email_password == obj.email_password and \
                self.old_email == obj.old_email and \
                self.old_email_password == obj.old_email_password and \
                self.old_email_secqa == obj.old_email_secqa

    def __ne__(self, obj):
        return not self.__eq__(obj)

    
class CmpTwitterPasswd(DatedBaseModel, ChidKey):
    password = db.StringProperty(indexed=False, required=True)


class CmpTwitterPasswdLookup(CreatedTimeBaseModel, ChidKey):
    usermail = db.EmailProperty()
    handle = db.StringProperty()
    
    




