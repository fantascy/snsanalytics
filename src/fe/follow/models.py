import logging
import datetime

from google.appengine.ext import db
from search.core import SearchIndexProperty, porter_stemmer
from twitter.api import TwitterApi

from common.utils import string as str_util
from common.utils import timezone as ctz_util
from sns.core.processcache import PersistedProcessCache
from sns.core.base import DatedNoIndexBaseModel, NameIF
from sns.chan.models import TAccount
from sns.camp import consts as camp_const
from fe import consts as fe_const
from fe.channel.models import FeParentChannel


class FollowCampaign(DatedNoIndexBaseModel, NameIF):
    uid = db.IntegerProperty()
    state = db.IntegerProperty(default=camp_const.CAMPAIGN_STATE_INIT, choices=camp_const.CAMPAIGN_STATES)
    scheduleNext = db.DateTimeProperty(required=True, default=datetime.datetime(1990,1,1))
    unfollowIndexCursor = db.IntegerProperty(required=True, default=0, indexed=False)
    unfollowTimeCursor = db.DateTimeProperty(indexed=False)
    suspendedTime = db.DateTimeProperty()
    search_index = SearchIndexProperty(('name',), indexer=porter_stemmer,relation_index=False)

    def className(self):
        return self.__class__.__name__

    @classmethod
    def get_or_insert_by_chid_uid(cls, chid, uid, **kwargs):
        parent = FeParentChannel.get_or_insert_by_chid(chid)
        obj = cls.get_by_key_name(str(chid), parent=parent)
        if obj:
            return obj
        else:
            channel = TAccount.get_by_chid_uid(chid, uid)
            return cls.get_or_insert(str(chid), parent=parent, uid=uid, name=channel.name, nameLower=channel.nameLower, **kwargs)

    def basic_info(self):
        return "%s %s" % (self.name, self.src_channel().chid_handle_uid_str()) 
    
    @property
    def chid(self):
        return int(self.key().name())
        
    def src_channel(self):
        return TAccount.get_by_chid_uid(self.chid, self.uid)
        
    def src_channel_name(self):
        return self.src_channel().name
    
    def finished(self):
        return self.state == camp_const.CAMPAIGN_STATE_EXPIRED

    def hourly_follow_limit(self, once_suspended_list):
        hourlyFollow = Config.get_config().follow_speed
        if hourlyFollow > fe_const.MAX_HOURLY_FOLLOW:
            hourlyFollow = fe_const.MAX_HOURLY_FOLLOW
        chid = self.chid 
        if chid in once_suspended_list:
            hourlyFollow = hourlyFollow / 2
        return hourlyFollow 
        
    def exceedMaxHourlyFollow(self, once_suspended_list, count, offset=0):
        hourlyFollow = self.hourly_follow_limit(once_suspended_list)
        maxNum = hourlyFollow - offset
        if count>=maxNum :
            logging.info("Follower rule '%s' exceeded hourly maximum follower of %s" % (self.name, maxNum))
            return True
        else :
            return False

    def exceedMaxHourlyUnfollow(self, once_suspended_list, count, offset=0):
        hourlyFollow = self.hourly_follow_limit(once_suspended_list)
        maxNum = hourlyFollow - offset + fe_const.EXTRA_UNFOLLOW
        if count>=maxNum :
            logging.info("Follower campaign '%s' exceeded hourly maximum unfollow of %s." % (self.name, maxNum))
            return True
        else :
            return False
        
    def unfollowHourInterval(self):
        return 24
        
    def unfollowStartOffTime(self, dt=datetime.datetime.utcnow()):
        return dt - datetime.timedelta(hours=3+self.unfollowHourInterval())
        
    def unfollowPreCutOffTime(self, dt=datetime.datetime.utcnow()):
        return dt - datetime.timedelta(hours=1+self.unfollowHourInterval())
        
    def unfollowCutOffTime(self, dt=datetime.datetime.utcnow()):
        return dt - datetime.timedelta(hours=self.unfollowHourInterval())
        
    def unfollowOnly(self):
        return self.src_channel_name().lower() in fe_const.UNFOLLOW_ONLY
        
    def getTwitterApi(self):
        return TwitterApi(oauth_access_token=self.src_channel().oauthAccessToken)

    def set_schedule_next_per_execution(self, db_put=False):
        intervalMinutes = Config.get_execution_interval_minute()
        self.scheduleNext = max(self.scheduleNext + datetime.timedelta(minutes=intervalMinutes), datetime.datetime.utcnow() + datetime.timedelta(minutes=3))
        if db_put:
            db.put(self)
        logging.info("Scheduled to launch rule '%s' again in %d minutes." % (self.name, intervalMinutes))

    def set_schedule_2_next_15_mins(self, db_put=False):
        totalTime = datetime.datetime.utcnow() - self.createdTime
        interval = 900
        total_secs = totalTime.days * 86400 + totalTime.seconds
        t = total_secs / interval
        self.scheduleNext = self.createdTime + (t + 1) * datetime.timedelta(seconds=interval)
        if db_put:
            db.put(self)
        logging.info("Scheduled to launch rule '%s' again next 15 minutes window." % (self.name, ))

    def mark_protected(self, db_put=False):
        self.scheduleNext = datetime.datetime.now() + datetime.timedelta(days=1)
        if db_put:
            db.put(self)
        logging.info("Protected %s." % self.basic_info())

    def mark_suspended(self):
        self.suspendedTime = datetime.datetime.now()
        self.state = camp_const.CAMPAIGN_STATE_SUSPENDED


class SourceTgtflwrs(db.Model):
    user_ids = db.TextProperty('[]')
    cursor = db.IntegerProperty(indexed=False, default=0)
    size = db.IntegerProperty(indexed=False, default=0)

    @classmethod
    def get_or_insert_by_chid(cls, chid):
        parent = FeParentChannel.get_or_insert_by_chid(chid)
        return cls.get_or_insert(str(chid), parent=parent)

    def get_user_ids(self):
        logging.debug("get_user_ids(): cursor=%d; size=%d" % (self.cursor, self.size))    
        return eval(self.user_ids)[self.cursor:] if self.user_ids else []

    def increment_cursor(self, cursor):
        self.cursor = self.cursor + cursor if self.cursor else cursor 
        logging.debug("increment_cursor(): cursor=%d; size=%d" % (self.cursor, self.size))    
    
    def finished(self):
        return self.cursor and self.size and self.cursor >= self.size and self.size > 0

    def reset(self, db_put=False):
        self.user_ids = '[]'
        self.cursor = 0
        self.size = 0
        if db_put: db.put(self)
                
    def set_user_ids(self, user_ids):
        self.size = len(user_ids)    
        self.user_ids = str_util.int_list_2_list_str(user_ids)

    def add_user_ids(self, more):    
        user_ids = eval(self.user_ids) if self.user_ids else []
        user_ids.extend(more)
        self.set_user_ids(user_ids)


class OnceSuspendedCmpAcctSetCache(PersistedProcessCache):
    KEY_NAME = 'pck_cmp_acct_set_once_suspended'


class CompleteCmpAcctBasicInfoCache(PersistedProcessCache):
    KEY_NAME = 'pck_cmp_acct_map_basic_info'


class CompleteCmpAcctSetCache(PersistedProcessCache):
    KEY_NAME = 'pck_cmp_acct_set_complete'


class ConfigCache(PersistedProcessCache):
    KEY_NAME = 'pck_follow_config'
    

class Config:
    def __init__(self):
        self.manually_stopped = False
        self.stop_on_suspension = False
        self.stop_in_weekend = False
        self.skip_stats = True
        self.suspension_detected = False
        self.msg = None
        self.threshold_followers = 2000
        self.threshold_posts = 30
        self.threshold_clicks = 300
        self.follow_speed = 5
        self.begin_hour = 8
        self.hours = 12
        
    @classmethod
    def get_config(cls):
        config = ConfigCache.get()
        return config if config else Config()

    @classmethod
    def set_config(cls, config):
        return ConfigCache.set(config)

    @classmethod
    def reset_config(cls):
        cls.set_config(Config())

    @classmethod
    def get_execution_interval_minute(cls):
        return 60 / cls.get_execution_times_per_hour()
    
    @classmethod
    def get_execution_times_per_hour(cls):
        hourlyFollow = Config.get_config().follow_speed
        hourlyUnFollow = hourlyFollow + fe_const.EXTRA_UNFOLLOW
        execution_times = (hourlyFollow + hourlyUnFollow) / fe_const.API_CALLS_PER_EXECUTION
        return execution_times if execution_times else 1

    def stop_follow(self):
        stop, msg = self._check_status()
        if stop:
            logging.info(msg)
        return stop

    def status_summary(self):
        return self._check_status()[1]

    def _check_status(self):
        if self.manually_stopped:
            return True, "Manually stopped"
        if self.stop_on_suspension and self.suspension_detected:
            return True, "Stopped on suspended accounts! %s" % self.msg
        now = datetime.datetime.utcnow()
        startTime = datetime.datetime(year=2011, month=4, day=2, hour=7)
        weeks = (now - startTime).days/7
        timeW = startTime + weeks * datetime.timedelta(days=7)
        timeR = now - timeW
        if self.stop_in_weekend and timeR > datetime.timedelta(days=0) and timeR < datetime.timedelta(days=2):
            return True, "Stopped follow activities during weekends."
        tzTime = ctz_util.to_tz(now, 'US/Pacific')
        usNow = datetime.datetime(year=tzTime.year,month=tzTime.month,day=tzTime.day,hour=tzTime.hour,minute=tzTime.minute)
        lastDay = datetime.datetime(year=tzTime.year,month=tzTime.month,day=tzTime.day)-datetime.timedelta(days=1)
        lastBegin = lastDay + datetime.timedelta(hours=self.begin_hour)
        lastEnd =  lastBegin + datetime.timedelta(hours=self.hours)
        thisDay = datetime.datetime(year=tzTime.year,month=tzTime.month,day=tzTime.day)
        thisBegin = thisDay + datetime.timedelta(hours=self.begin_hour)
        thisEnd =  thisBegin + datetime.timedelta(hours=self.hours)
        if (lastBegin<usNow<lastEnd) or (thisBegin<usNow<thisEnd):
            pass
        else:
            return True, "Stopped follow activities during non working hours."
        return False, "Follow campaigns are running."

