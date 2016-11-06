import datetime
from google.appengine.ext import db

from sns.core.core import User, UserKeyName, UserClickParent
from sns.core.base import DatedBaseModel, BaseCounterNoIndex, ClickCounter, BaseModel


class UserClickCounter(ClickCounter, UserKeyName):
    @classmethod
    def get_or_insert_by_uid_update(cls, uid):
        parent = UserClickParent.get_or_insert_parent(uid=uid)
        return UserClickCounter.get_or_insert_update(cls.keyName(uid), parent=parent)

    def mail(self):
        user = User.get_by_id(self.uid)
        return user.mail if user else None


class UserPostCounter(BaseCounterNoIndex, UserKeyName):
    pass


class UserFailureCounter(BaseCounterNoIndex, UserKeyName):
    pass


class UserExecuteCounter(BaseModel, UserKeyName):
    modifiedTime = db.DateTimeProperty(auto_now=True,indexed=False)
    day = db.IntegerProperty(default=0,indexed=False)
    
    def increment(self,size=1):
        now = datetime.datetime.utcnow()
        if now.day != self.modifiedTime.day:
            self.day = 0
        self.day += size
        
    def update(self):
        self.increment(size=0)


class UserCounters(DatedBaseModel):
    postCounter = db.ReferenceProperty(UserPostCounter, required=True)
    failureCounter = db.ReferenceProperty(UserFailureCounter, required=True)

    @classmethod
    def uniqueness_properties(cls) :
        return []

    def update(self):
        self.postCounter.update()
        self.failureCounter.update()
        return self


class GlobalUserCounter(db.Model):
    lastUpdateTime = db.DateTimeProperty()
    dailyNumber = db.TextProperty()
    dailyIncrease = db.TextProperty()

    @classmethod
    def keyName(cls):
        return "GlobalUserCounter"

    @classmethod
    def get_or_insert_counter(cls):
        return cls.get_or_insert(cls.keyName()) 
    

class UserStats(object):
    """
    UserStats class is designed to carry runtime results of campaign executions.
    So it is not a db model, and it doesn't contain click count. 
    """
    def __init__(self):
        self.post_count = 0
        self.failure_count = 0

    def isZero(self):
        return self.post_count==0 and self.failure_count==0


