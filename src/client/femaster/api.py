import datetime, time
import threading
import logging

from twitter import errors as twitter_error

from sns.femaster import consts as femaster_const 
from common.utils import datetimeparser 
from common.multithreading.taskdaemonnowait import TaskDaemonNoWait
from sns.api import consts as api_const
from client import apiclient
from client.base.api import ApiBase
from client.channel.api import TAccountCacheMgr, TAccountApi
from client.content.api import TopicCacheMgr
from client.femaster.s3 import SysFollowAllocWeekly, SrcFollowAllocMonthly


THREAD_POOL = 5     
TASK_LIMIT = 100     
TIME_BUCKET = 600

def thread_name():
    return "Thread %d" % threading.current_thread().ident 


class FeMasterCacheMgr:
    """ 
        _system_follow_cache is a map of X weeks of follow history. All followers of the same week are hold in a set.
    """
    WEEKS_OF_SYSTEM_FOLLOWERS = 3
    _cv = threading.Condition()
    _system_follower_cache = None
    _system_follower_cache_oldest_week = None

    @classmethod
    def is_cache_valid(cls):
        if cls._system_follower_cache is None or cls._system_follower_cache_oldest_week is None:
            return False
        return cls._system_follower_cache_oldest_week >= cls.system_follow_cache_oldest_valid_int_week() 
    
    @classmethod
    def flush(cls):
        with cls._cv:
            TAccountCacheMgr.clear()
            TopicCacheMgr.clear()
            _system_follower_cache = None

    @classmethod
    def build(cls, force=False):
        with cls._cv:
            if cls.is_cache_valid() and not force:
                return True  
            cls.flush()
            startTime = datetime.datetime.utcnow()
            logging.info("%s: Started re-building cache." % thread_name())
            TAccountCacheMgr.load()
            TopicCacheMgr.load()
            cls.consolidate_change_logs()
            cls._system_follower_cache = set([])
            now = datetime.datetime.utcnow()
            for i in range(cls.WEEKS_OF_SYSTEM_FOLLOWERS + 1):
                int_week = datetimeparser.intWeek(now - datetime.timedelta(weeks=i))
                sys_follow_alloc_weekly = SysFollowAllocWeekly.get_by_time_bucket(int_week)
                user_ids = sys_follow_alloc_weekly.get_json()
                if user_ids:
                    cls._system_follower_cache.update(user_ids)
            cls._system_follower_cache_oldest_week = cls.system_follow_cache_oldest_valid_int_week()
            logging.info("%s: Cached total %d Twitter user ids for system follow history." % (thread_name(), len(cls._system_follower_cache)))
            endTime = datetime.datetime.utcnow() 
            logging.info("%s: Finished re-building cache in %s." % (thread_name(), str(endTime-startTime)))
            return True
    
    @classmethod
    def rebuild_if_cache_not_valid(cls):
        if not cls.is_cache_valid():
            cls.build()

    @classmethod
    def system_follow_cache_oldest_valid_int_week(cls, utcnow=datetime.datetime.utcnow()):
        utcnow = utcnow if utcnow else datetime.datetime.utcnow()   
        return datetimeparser.intWeek(utcnow - datetime.timedelta(weeks=cls.WEEKS_OF_SYSTEM_FOLLOWERS))

    @classmethod
    def cache_count(cls):
        return len(cls._system_follower_cache) if cls._system_follower_cache else 0
        
    @classmethod
    def add_tgtflwrs(cls, followers):
        """ The runtime method that keeps the cache in sync with all updated follows. """
        cls.rebuild_if_cache_not_valid()
        with cls._cv:
            cls._system_follower_cache.update(followers)
            logging.info("%s: Added %d ids to system follower cache of total %d." % (thread_name(), len(followers), cls.cache_count()))
            
    @classmethod
    def filter_followers(cls, followers):
        """ Return followers that are not on the cache. """
        followers = set(followers)
        cls.rebuild_if_cache_not_valid()
        with cls._cv:
            return followers.difference(cls._system_follower_cache)
            
    @classmethod
    def consolidate_change_logs(cls):
        log_keys_to_delete = []
        while True:
            """ TODOX Check correctness """
            log_keys = TgtflwrAllocationLogApi().query(params=dict(keys_only=True, order='createdTime', limit=100))['objs']
            if not log_keys:
                break
            current_weekly_history=None
            for log_key in log_keys:
                log = TgtflwrAllocationLogApi().get(params=dict(id=log_key))
                if log is None:
                    logging.critical("TgtflwrAllocationLog object not found! %s" % log_key)
                    continue
                log_api = TgtflwrAllocationLogApi(log)
                int_week  = datetimeparser.intWeek(log_api.createdTime)
                if current_weekly_history and current_weekly_history.time_bucket != int_week:
                    current_weekly_history.commit()
                    TgtflwrAllocationLogApi().delete(params=dict(ids=log_keys_to_delete))
                    current_weekly_history = None
                if current_weekly_history is None:
                    current_weekly_history = SysFollowAllocWeekly.get_by_time_bucket(int_week)
                current_weekly_history.add_user_ids(log_api.tgtflwrs)
                log_keys_to_delete.append(log_key)
            if current_weekly_history is not None:
                current_weekly_history.commit()
                TgtflwrAllocationLogApi().delete(params=dict(ids=log_keys_to_delete))


class TgtflwrsApi(ApiBase):
    @classmethod
    def transform_obj(cls, obj):
        obj = ApiBase.transform_obj(obj)
        if obj is None:
            return None
        if not isinstance(obj, dict):
            return obj
        tgtflwrs = obj.get('tgtflwrs', None)
        obj['tgtflwrs'] = eval(tgtflwrs) if tgtflwrs else []
        return obj
            
    @property
    def tgtflwrs(self):
        return self.obj['tgtflwrs']


class SourceApi(TgtflwrsApi):
    API_MODULE = api_const.API_M_FE_MASTER_SOURCE
    MONTHS_OF_UNIQUE_FOLLOWER_ALLOCATION = 3 

    @property
    def chid(self):
        return int(self.obj['key_name'])
        
#     @classmethod
#     def transform_obj(cls, obj):
#         obj = TgtflwrsApi.transform_obj(obj)
#         if obj is None: return None
#         obj['tgtflwrs'] = obj['tgtflwrs'][:50]
#         return obj
    
    def allocate_followers(self, allocated):
        monthly_history = SrcFollowAllocMonthly.get_by_chid_and_time(self.chid, datetime.datetime.utcnow())
        monthly_history.add_user_ids(allocated)
        monthly_history.commit()
        """ TODOX Check correctness """
        return TgtflwrAllocationLogApi().create(params=dict(chid=self.chid, tgtflwrs=allocated))

    def allocated_follower_history(self, months=None):
        if not months:
            months = self.MONTHS_OF_UNIQUE_FOLLOWER_ALLOCATION
        user_ids = []
        int_month = datetimeparser.intMonth(datetime.datetime.utcnow())
        while months > -1:
            monthly_history = SrcFollowAllocMonthly.get_by_chid_and_time_bucket(self.chid, int_month)
            if monthly_history and monthly_history.get_json():
                user_ids.extend(monthly_history.get_json())
            int_month = datetimeparser.decrement_int_month(int_month)
            months -= 1
        return set(user_ids)

    def query_under_allocated(self, limit=100):
        sources = self.admin(params={'op': 'query_under_allocated', 'limit': limit})
        return self.transform_obj_list(sources)

    def get_disallowed_user_id_set(self, months=None):
        user_id_set = self.allocated_follower_history()
        follower_list = self.admin(params={'op': 'get_follower_list', 'chid': self.chid})
        user_id_set.update(follower_list)
        return user_id_set

    def str(self):
        source = self.obj
        if source is None:
            return "Source(None)"
        return "Source(key_name=%s, state=%d, enough=%s, count=%s, tgtflwrs=%s)" % (source['key_name'], source['state'], source['enough'], source['count'], source['tgtflwrs'])

    def add_tgtflwrs(self, more_tgtflwrs):    
        self.tgtflwrs.extend(more_tgtflwrs)
        self.obj['count'] = len(self.tgtflwrs)
        self.obj['enough'] = self.obj['count'] >= femaster_const.TARGET_FOLLOWERS_ALLOC_SIZE

    def actual_count(self):
        return len(self.tgtflwrs)


class TargetApi(TgtflwrsApi):
    """ Target processor concurrency assumes only one process running at any time. """
    API_MODULE = api_const.API_M_FE_MASTER_TARGET
    _cv = threading.Condition()
    _target_cv_map = {}
    
    def __init__(self, obj=None):
        ApiBase.__init__(self, obj)
        self.topic_key = None
        self._tapi = None
    
    @property
    def tapi(self):
        if self._tapi is None:
            self._tapi = TAccountCacheMgr.get_random_tapi()
        return self._tapi
        
    @classmethod
    def get_or_insert_by_handle(cls, topic_key, handle):
        if not handle:
            logging.error("%s: Unexpected empty handle!" % thread_name())
            return None
        tapi = TAccountCacheMgr.get_random_tapi()
        user_id = tapi.get_user_id_by_handle(handle)
        if user_id:
            return cls.get_or_insert_by_user_id(user_id, handle)
        else:
            error_msg = "Target handle %s is invalid!" % handle
            TopicTargetErrorApi.get_or_insert_by_topic_key(topic_key, error_msg)
            logging.error("%s: %s" % (thread_name(), error_msg))
            return None

    @classmethod
    def get_by_user_id(cls, user_id):
        return cls.transform_obj(cls().admin(params=dict(op='get_by_user_id', user_id=user_id)))

    @classmethod
    def get_or_insert_by_user_id(cls, user_id, handle):
        return cls.transform_obj(cls().admin(params=dict(op='get_or_insert_by_user_id', user_id=user_id, handle=handle)))

    @classmethod
    def get_target_cv(cls, user_id):
        with cls._cv:
            _target_cv = cls._target_cv_map.get(user_id, None)
            if _target_cv is None:
                _target_cv = threading.Condition()
                cls._target_cv_map[user_id] = _target_cv
            return _target_cv 

    def mark_invalid_and_update(self):
        self.obj['state'] = femaster_const.TARGET_STATE_ERROR
        self.update()
        
    def is_active(self):
        return self.obj['state'] == femaster_const.TARGET_STATE_NORMAL and not self.obj['completed']

    def add_tgtflwrs(self, more_followers):
        if not more_followers:
            return 
        self.obj['offset'] += len(more_followers) 
        self.tgtflwrs.extend(more_followers)
        self.size = len(self.tgtflwrs)

    def set_tgtflwrs(self, followers):
        self.obj['tgtflwrs'] = followers
        self.size = len(self.tgtflwrs)

    def allocate_followers(self, size, history=set([])):
        followers = self.tgtflwrs
        allocated = []
        i = 0
        for i in range(len(followers)):
            if followers[i] in history:
                continue
            allocated.append(followers[i])
            if len(allocated) == size:
                break
        remaining = followers[i+1:]
        self.set_tgtflwrs(remaining)
        return allocated

    def handle(self):
        return self.obj['handle']

    def user_id(self):
        return int(self.key_name)

    def user_id_handle_str(self):
        return "%d@%s" % (self.user_id(), self.handle())

    def is_valid(self):
        error_msg = None
        retry = 3
        while retry:
            retry -= 1
            try:
                info = self.tapi.users.show(user_id=self.user_id())
                followings = info['friends_count']
                followers = info['followers_count']
                if followings > followers / 2:
                    error_msg = "Invalid target %s! Followings/followers %d/%d ratio is too high!" % (self.user_id_handle_str(), followings, followers)
                    break
                elif followers < 1000:
                    error_msg = "Invalid target %s! Follower count %d is less than 1000!" % (self.user_id_handle_str(), followers)
                    break
                else:
                    return True
            except Exception, ex:
                if twitter_error.isTemporaryError(ex):
                    logging.warn("%s: Temporary Twitter API error. %s" % (thread_name(), str(ex).decode('utf-8', 'ignore')))
                    continue
                else:
                    logging.error("%s: Invalid target %s! %s" % (thread_name(), self.user_id_handle_str(), str(ex)))
                    break
        if error_msg:
            TopicTargetErrorApi.get_or_insert_by_topic_key(self.topic_key, error_msg)
            logging.error("%s: %s" % (thread_name(), error_msg))
        return False

    def execute_follower_allocation(self, source_api, size=femaster_const.TARGET_FOLLOWERS_ALLOC_SIZE):
        user_id = self.user_id()
        channel = TAccountCacheMgr.channel_map.get(user_id)
        if channel:
            error_msg = "Target account should not be a SNS account. %s" % TAccountCacheMgr.chid_handle_str(user_id)
            TopicTargetErrorApi.get_or_insert_by_topic_key(self.topic_key, error_msg)
            logging.error("%s: %s" % (thread_name(), error_msg))
            return []
        with self.get_target_cv(user_id):
            if not self.is_valid():
                logging.debug("%s: TargetApiexecute_follower_allocation() invalid target." % thread_name())
                self.mark_invalid_and_update()
            if not self.is_active():
                logging.debug("%s: TargetApiexecute_follower_allocation() bad target." % thread_name())
                return []
            source_allocated_follower_history = source_api.get_disallowed_user_id_set()
            allocated = self.allocate_followers(size, history=source_allocated_follower_history)
            remaining = size - len(allocated)
            logging.debug("%s: TargetApiexecute_follower_allocation() need allocate %d more." % (thread_name(), remaining))
            if remaining and self.load_next_follower_page():
                more_allocated = self.allocate_followers(remaining, history=source_allocated_follower_history)
                allocated.extend(more_allocated)
                logging.debug("%s: TargetApiexecute_follower_allocation() allocated %d more." % (thread_name(), len(more_allocated)))
            if allocated:
                logging.debug("%s: TargetApiexecute_follower_allocation() allocated %d total." % (thread_name(), len(allocated)))
                FeMasterCacheMgr.add_tgtflwrs(allocated)        
                self.update()
                source_api.allocate_followers(allocated)
            return allocated
        
    def load_next_follower_page(self):
        if self.obj['completed']:
            logging.info("%s Started." % self._load_next_follower_page_log_prefix())
            return True
        return self._load_next_follower_page()

    def _load_next_follower_page(self, retry=3):
        target = self.obj
        while retry:
            try:
                retry -= 1
                cursor = self.obj['cursor']
                completed = self.obj['completed']
                if cursor is None: cursor = -1
                if cursor == 0 and not completed: 
                    target['completed'] = True
                    logging.warn("%s Marked target completed. Skipped retrieving followers for target." % self._load_next_follower_page_log_prefix())
                    self.update()
                    return True
                response = TAccountApi.retrieve_followers(chid=self.tapi.user_id(), user_id=self.user_id(), cursor=cursor)
                logging.info("%s previous_cursor=%s; next_cursor=%s; count=%s" % 
                             (self._load_next_follower_page_log_prefix(), 
                              response['previous_cursor'], 
                              response['next_cursor'], 
                              len(response['ids'])))
                next_cursor = response["next_cursor"]
                target['cursor'] = next_cursor
                followers = response['ids']
                target['offset'] += len(followers)
                filtered_followers = FeMasterCacheMgr.filter_followers(followers)  
                logging.info("%s: Found %d new followers out of total %d on the page." % (thread_name(), len(filtered_followers), len(followers)))
                self.add_tgtflwrs(filtered_followers)
                if next_cursor == 0: 
                    target['completed'] = True
                    logging.info("%s Marked target completed." % self._load_next_follower_page_log_prefix())
                self.update()
                return True
            except Exception, ex:
                if twitter_error.isTemporaryError(ex) and retry:
                    logging.warn("%s: Temporary Twitter API error. %s" % (thread_name(), str(ex).decode('utf-8', 'ignore')))
                else:
                    logging.exception("%s Unexpected error!" % self._load_next_follower_page_log_prefix())
                    break
        return False

    def _load_next_follower_page_log_prefix(self):
        return "%s: Refreshing follower list for source %s and target %s at cursor %d." % (thread_name(), self.tapi.user_id(), self.user_id_handle_str(), self.obj['cursor'])


class TopicTargetApi(ApiBase):
    API_MODULE = api_const.API_M_FE_MASTER_TOPIC_TARGET

    @classmethod
    def get_by_topic_key(cls, topic_key):
        return cls.transform_obj(cls().admin(params=dict(op='get_by_topic_key', topic_key=topic_key)))

    @classmethod
    def get_target_by_topic_key(cls, topic_key):
        return TargetApi.transform_obj(cls().admin(params=dict(op='get_target_by_topic_key', topic_key=topic_key)))

    @classmethod
    def get_or_insert_by_topic_key(cls, topic_key, user_id):
        return cls.transform_obj(cls().admin(params=dict(op='get_or_insert_by_topic_key', topic_key=topic_key, user_id=user_id)))
         

class TopicTargetErrorApi(ApiBase):
    API_MODULE = api_const.API_M_FE_MASTER_TOPIC_TARGET_ERROR
         
    @classmethod
    def get_or_insert_by_topic_key(cls, topic_key, error_msg):
        return cls.transform_obj(cls().admin(params=dict(op='get_or_insert_by_topic_key', topic_key=topic_key, error_msg=error_msg)))
         

class TgtflwrAllocationLogApi(TgtflwrsApi):
    API_MODULE = api_const.API_M_FE_MASTER_ALLOC_LOG
    

class TgtflwrFollowLogApi(TgtflwrsApi):
    API_MODULE = api_const.API_M_FE_MASTER_FOLLOW_LOG
         

class TgtflwrAllocationTaskDaemon(TaskDaemonNoWait):
    def __init__(self):
        TaskDaemonNoWait.__init__(self, workers=THREAD_POOL)
        
    def run_impl(self, task):
        source_api = SourceApi(task)
        chid = source_api.chid
        logging.debug("%s: Started processing source %s." % (thread_name(), chid))
        if not TAccountCacheMgr.has_key(chid):
            source_api.delete(dict(id=source_api.key))
            logging.error("%s: Channel %d doesn't exist! Deleted the source object." % (thread_name(), chid))
            return False
        if TAccountCacheMgr.is_once_suspended(chid):
            logging.info("%s: %s is once suspended. Skip it." % (thread_name(), TAccountCacheMgr.chid_handle_str(chid)))
            return False
        topic_key = TAccountCacheMgr.first_topic_key(chid)
        if topic_key is None:
            logging.error("%s: %s doesn't have topic!" % (thread_name(), TAccountCacheMgr.chid_handle_str(chid)))
            return False
        target_api = self.get_target_api(topic_key)
        if not target_api: return False
        alloc_size = femaster_const.TARGET_FOLLOWERS_ALLOC_SIZE - source_api.actual_count()
        if alloc_size > 0:
            logging.debug("%s: Allocate size is %d." % (thread_name(), alloc_size))
            target_api.topic_key = topic_key
            tgtflwrs = target_api.execute_follower_allocation(source_api, size=alloc_size)
            if tgtflwrs:
                source_api.add_tgtflwrs(tgtflwrs)
                """ TODOX not finished """
                source_api.update()
                logging.info("%s: Successfully allocated %d followers from target %s for %s." % (thread_name(), len(tgtflwrs), target_api.user_id_handle_str(), source_api.chid))
                return True
        logging.debug("%s: Failed allocating target followers." % thread_name())
        return False

    def get_target_api(self, topic_key):
        target = TopicTargetApi.get_target_by_topic_key(topic_key)
        if not target:
            logging.error("%s: Topic %s has no target." % (thread_name(), topic_key))
            return None
        return TargetApi(target)
        
    def pre_execute(self):
        FeMasterCacheMgr.consolidate_change_logs()
        sources = SourceApi().query_under_allocated(limit=TASK_LIMIT)
        logging.info("%s: Retrieved %d sources." % (thread_name(), len(sources)))
        self.add_tasks(sources)


if __name__ == '__main__':
    while True:
        apiclient.login_as_admin()
        FeMasterCacheMgr.rebuild_if_cache_not_valid()
        TgtflwrAllocationTaskDaemon().execute()
        time.sleep(TIME_BUCKET)

