import datetime
import logging
import urllib
from sets import Set, ImmutableSet
 
from google.appengine.ext import db
from google.appengine.runtime import DeadlineExceededError
from twitter.api import TwitterApi
from twitter import errors as twitter_error

from common.utils import timezone as ctz_util
import deployfe
import context
from sns.serverutils import deferred, memcache
from common.utils import datetimeparser as datetime_util
from sns.api.base import BaseProcessor
from sns.core import core as db_core
from sns.chan import consts as channel_const
from sns.chan.api import TAccountProcessor
from sns.camp import consts as camp_const
from fe import consts as fe_const
from fe.api import consts as api_const
from fe.api import errors as api_error
from fe.channel.models import ChannelHourlyStats, HourlyFriendList,  CompleteFriendList, UnfollowFriendList, SafeFriendSet, ChannelDailyStats
from fe.follow import utils as follow_util
from fe.follow.models import FollowCampaign, FeParentChannel, SourceTgtflwrs, Config, \
    OnceSuspendedCmpAcctSetCache, CompleteCmpAcctBasicInfoCache, CompleteCmpAcctSetCache


class SourceTgtflwrsProcessor(BaseProcessor):
    def __init__(self, channel, source_tgtflwrs=None):
        self.channel = channel
        self.source_tgtflwrs = source_tgtflwrs if source_tgtflwrs else SourceTgtflwrs.get_or_insert_by_chid(self.channel.chid_int())
        
    def getModel(self):
        return SourceTgtflwrs

    def finished(self):
        return self.source_tgtflwrs.finished()
    
    def get_user_ids(self):
        if self.finished(): 
            self.report_to_femaster_if_finished()
            if self.finished():
                logging.error("Failed reporting to master for channel %s!" % self.channel.chid_handle_uid_str())
                return [] 
        user_ids = self.source_tgtflwrs.get_user_ids()
        return user_ids if user_ids else self.get_tgtflwrs_from_master()

    def get_tgtflwrs_from_master(self):
        chid = self.channel.chid_int()
        url = follow_util.fe_master_req_url('sns/femaster/worker_get_tgtflwrs/?chid=%d' % chid)
        success, data = follow_util.fe_master_urlopen(url)
        if success:
            self.source_tgtflwrs.add_user_ids(data)
            db.put(self.source_tgtflwrs)  
            return self.source_tgtflwrs.get_user_ids()
        else:
            logging.info("Got zero target follower from master for channel %s!" % self.channel.chid_handle_uid_str())
            return []

    def increment_cursor(self, index):
        obj = SourceTgtflwrs.get_or_insert_by_chid(self.channel.chid_int())
        obj.increment_cursor(index)
        db.put(obj)
        self.report_to_femaster_if_finished()
    
    def report_to_femaster_if_finished(self):
        chid = self.channel.chid_int()
        obj = SourceTgtflwrs.get_or_insert_by_chid(chid)
        if obj.finished():
            report_url = follow_util.fe_master_req_url('sns/femaster/worker_report_status?chid=%d' % chid)
            resp = follow_util.fe_master_urlopen(report_url)
            logging.debug("Response on worker_report_status: %s " % str(resp))
            if resp and resp[0]:
                obj.reset(db_put=True)
                return True
        return False


class FollowCampaignProcessor(BaseProcessor):
    def getModel(self):
        return FollowCampaign

    def defaultOrderProperty(self):
        return "nameLower"  
    
    def __init__(self, timeout=BaseProcessor.TIMEOUT_BACKEND):
        BaseProcessor.__init__(self, timeout=timeout)
        self.executionApiCount = 0
        self.apiLimitExceeded = False
        self.skip_stats = False
        self.friendsCount = 0
        self.followersCount = 0
        self._completeFriendList = None
        self._safeFriendSet = None
        self._once_suspended_list = None
        self.rule = None
        self.channel = None
        self.tapi = None
        self.skip_unfollow = False
        self.unfollow_only = False
        self.unfollow_cmp_accts = False
    
    @classmethod
    def supportedOperations(cls):
        """"
        Supported public API operations of this processor
        """
        return ImmutableSet([api_const.API_O_ACTIVATE, 
                           api_const.API_O_DEACTIVATE, 
                           api_const.API_O_EXECUTE, 
                           api_const.API_O_CRON_EXECUTE, 
                           api_const.API_O_QUERY_ALL,
                           api_const.API_O_REFRESH,
                           ]).union(BaseProcessor.supportedOperations())
                               
    def query_base(self, set_ancestor=True, **kwargs):
        query_base = self.getModel().all()
        if set_ancestor:
            uid = db_core.get_user_id()
            query_base = query_base.filter('uid', uid)
        return query_base

    def search(self, keyword, set_ancestor=True, **kwargs):
        uid = db_core.get_user_id()
        return self.getModel().search_index.search(keyword, filters=('uid', uid))

    def reset_timeout(self):
        BaseProcessor.__init__(self, timeout=BaseProcessor.TIMEOUT_BACKEND)
        
    def over_execution_limit(self):
        return self.executionApiCount >= 10
    
    def over_follow_limit(self):
        return self.friendsCount > TwitterApi.NEW_ACCOUNT_FRIENDS_LIMIT and self.friendsCount > self.followersCount
    
    @classmethod
    def get_deferred_per_minute(cls):
        return cls.get_total_active_rule_count() * Config.get_execution_times_per_hour() / 60 + 1

    @classmethod
    def get_total_active_rule_count(cls):
        mem_key = 'totalactivecount'
        count = memcache.get(mem_key)
        if count is None:
            count = FollowCampaign.all().filter('state', camp_const.CAMPAIGN_STATE_ACTIVATED).count()
            memcache.set(mem_key,count,time=3600)
        return count

    @classmethod
    def sync_rule_status(cls, rule, channel=None):
        """ Return True if rule is in good mood to execute follow. """
        if not rule:
            return False
        if not channel:
            channel = rule.src_channel()
        if channel.deleted:
            db.delete(rule)
            logging.info("Deleted rule of channel %s." % channel.chid_handle_uid_str())
            return False
        if follow_util.always_rated_limited(channel.name):
            rule.state = camp_const.CAMPAIGN_STATE_ERROR
            db.put(rule)
            return False
        if cls.should_protect(channel):
            rule.mark_protected(db_put=True)
            return False
        return True

    @classmethod
    def should_protect(cls, channel):
        chid = channel.chid_int()
        chinmap = CompleteCmpAcctBasicInfoCache.get(fallback={})
        if context.is_dev_mode():
            return False 
        if not chinmap.has_key(chid):
            return True
        state, followers, clicks, posts = chinmap.get(chid)
        config = Config.get_config()
        return state == channel_const.CHANNEL_STATE_SUSPENDED or followers > config.threshold_followers or clicks > config.threshold_clicks or posts < config.threshold_posts
    
    def handleException(self, ex):
        if self.rule is None:
            logging.exception("Follow rule object is none.")
            return
        if twitter_error.isTargetSuspended(ex):
            pass
        elif twitter_error.isSuspended(ex):
            self._suspend()
            self.apiLimitExceeded = True
            return
        elif isinstance(ex, DeadlineExceededError):
            pass
        elif isinstance(ex, ValueError):
            pass
        elif twitter_error.isTemporaryError(ex):
            pass
        elif twitter_error.isStatus404(ex):
            pass
        elif twitter_error.isPageNotExist(ex):
            pass
        elif twitter_error.isNotFound(ex):
            pass
        elif twitter_error.isStatus502(ex):
            pass
        elif twitter_error.isNotFriend(ex):
            pass
        elif twitter_error.isAlreadyFollowing(ex):
            pass
        elif twitter_error.isRateLimitExceeded(ex):
            self.apiLimitExceeded = True
        elif twitter_error.isStatus401(ex):
            self.apiLimitExceeded = True
        elif twitter_error.isCouldNotFollow(ex):
            pass
        else:
            self.apiLimitExceeded = True
        ex_msg = str(ex).decode("utf-8", "ignore")
        if self.apiLimitExceeded:
            logging.exception("API limit exceeded! %s %s." % (self.rule.name, self.channel.chid_handle_uid_str()))
            self._finish_execution()
        else:
            logging.warn("%s - %s %s." % (ex_msg, self.rule.name, self.channel.chid_handle_uid_str()))
        
    @classmethod
    def deferred_send_stats_handler(cls):
        context.set_deferred_context(deployfe)
        offset = 0
        limit = 100
        stats_count = 0
        while True:
            rules = FollowCampaign.all().fetch(limit=limit, offset=offset)
            if len(rules) == 0:
                break
            ids = [rule.id for rule in rules]
            deferred.defer(cls.deferred_send_stats, ids=ids, queueName='snsfemaster')
            offset += limit
            stats_count += len(rules)
        logging.info("Sending total %d channel stats to FE master..." % stats_count)
            
    @classmethod
    def deferred_send_stats(cls, ids=[]):
        context.set_deferred_context(deployfe)
        try:
            infos = []
            for rid in ids:
                rule = db.get(rid)
                channel = rule.src_channel()
                chid = channel.chid_str() if channel else None
                if chid is None:
                    continue
                data = {}
                data['chid'] = chid
                data['server'] = context.get_context().application_id()
                user = db_core.get_user_by_id(rule.uid)
                data['userEmail'] = user.mail if user else None
                data['rid'] = rule.key().id()
                data['rule'] = rule.name.encode('utf-8')
                data['state'] = rule.state
                data['ruleModified'] = str(rule.modifiedTime)
                infos.append(data)
            if infos:
                url = follow_util.fe_master_req_url("log/channelstats/fe/set/")
                urllib.urlopen(url, urllib.urlencode({'infos': str(infos)})).read()
            logging.info("Dispatched %d follow stats to SNS server." % len(infos))
        except Exception:
            logging.exception("Exception when sending follow stats!")
                                
    def _finish_execution(self):
        self.rule.set_schedule_2_next_15_mins()
        db.put(self.rule)
        return True

    def _suspend(self):
        try:
            self.apiLimitExceeded = True
            self.rule.mark_suspended()
            self.channel.mark_suspended()
            db.put([self.rule, self.channel])
            logging.error("Marked follow campaign '%s' and channel %s as suspended!" % (self.rule.name, self.channel.chid_handle_uid_str()))
            config = Config.get_config()
            if config.stop_on_suspension:
                utcnow = datetime.datetime.utcnow()
                the_time = ctz_util.to_tz(utcnow, 'US/Pacific')
                config.msg = "Detected suspended account %s at %s US/Pacific time." % (self.channel.chid_handle_uid_str(), str(the_time))
                config.suspension_detected = True
                Config.set_config(config)
            return True
        except Exception:
            logging.exception("Error when marking rule and acct as suspended.")
            return False

    def create(self, params):
        if not params.has_key('parent'):
            params['parent'] = db_core.get_user()
        params['new'] = True
        rule = BaseProcessor.create(self, params)
        self.activate(rule)
        return rule

    def isAddLimited(self):
        return False

    def activate(self, params):
        """
        Activate the rule only, not trigger an action immediately.
        """
        rule = db_core.normalize_2_model(params)
        if rule.state == camp_const.CAMPAIGN_STATE_ACTIVATED:
            raise api_error.ApiError(api_error.API_ERROR_POSTING_RULE_OP_NOT_SUPPORTED_IN_STATE, 'activate', rule.name, rule.state)
        rule.state = camp_const.CAMPAIGN_STATE_ACTIVATED
        rule.unfollowTimeCursor = rule.unfollowStartOffTime()
        rule.put()
        self.rule = rule
        self.cleanCompleteFriendList()
        return rule
    
    def deactivate(self, params):
        """
        De-activate the rule. A rule can only be de-activated from active state.
        """
        rule = db_core.normalize_2_model(params)
        if rule.state != camp_const.CAMPAIGN_STATE_ACTIVATED:
            raise api_error.ApiError(api_error.API_ERROR_POSTING_RULE_OP_NOT_SUPPORTED_IN_STATE, 'deactivate', rule.name, rule.state)
        rule.state = camp_const.CAMPAIGN_STATE_INIT
        rule.put()
        return rule

    def execute_admin(self, params):
        op = params.get('op', None)
        if op:
            if op == 'refresh_cmp_acct_list':
                return self.update_cmp_channel_list()
            elif op == 'refresh_once_suspended_acct_list':
                return self.update_once_suspended_channel_list()
            elif op == 'clean_suspended': 
                return self.__class__.clean_suspended()
        return BaseProcessor.execute_admin(self, params)

    def cron_execute(self, params):
        op = params.pop('op', None)
        if op:
            if op == 'send_stats':
                deferred.defer(self.__class__.deferred_send_stats_handler)
            elif op == 'sync': 
                deferred.defer(self.__class__.deferred_sync)
            elif op == 'migrate': 
                deferred.defer(self.__class__.deferred_migrate)
            else:
                return "Invalid op - %s!" % op
            return True
        config = Config.get_config()
        if config.stop_follow():
            return True
        return self.execute(params)

    def execute(self, params):
        """
        Query all new active rules, and schedule a number of them into deferred. 
        """
        utcnow = datetime.datetime.utcnow()
        ruleQuery = self.query_base(set_ancestor=False).filter('state', camp_const.CAMPAIGN_STATE_ACTIVATED).filter('scheduleNext < ', utcnow).order('scheduleNext')
        executionCount = self.get_deferred_per_minute()
        maxExecutionCount = executionCount * 2
        activeRules = ruleQuery.fetch(maxExecutionCount)
        logging.info("Total due active follow rule count is %d at this moment." % len(activeRules))
        if not activeRules:
            return 0
        mostDelayedRule = activeRules[0]
        mostDelayed = utcnow - mostDelayedRule.scheduleNext
        self.logScheduleDelayStatus(mostDelayedRule.scheduleNext)
        if mostDelayed>datetime.timedelta(minutes=3):
            effectiveExecutionCount = maxExecutionCount
        else:
            effectiveExecutionCount = executionCount
        deferredCount = 0
        for rule in activeRules[:effectiveExecutionCount]:
            msg = " deferred execution for rule '%s' with source channel '%s'." % (rule.name, rule.src_channel_name())
            try:
                rule.set_schedule_next_per_execution(db_put=True)
            except: 
                logging.exception("Could not kick off %s" % msg)
                continue
            deferred.defer(self.__class__.deferred_execute_one_handler, ruleId=rule.id)
            logging.info("Kicked off %s" % msg)
            deferredCount += 1
        logging.info("Kicked off deferred execution for %s active follower rules." % deferredCount)
        return deferredCount

    def _executeOneHandler(self, ruleId, retry):
        """
        Execute the one rule, keep deferring until it is fully finished execution.
        Return true if the rule is finished, else False (Timeout).
        """
        try:
            self.rule = db.get(ruleId)
            self.channel = self.rule.src_channel()
            if not self.sync_rule_status(self.rule, self.channel):
                return True
            self.tapi = self.rule.getTwitterApi()
            followers_count = 0
            friends_count, followers_count = self.tapi.get_friends_followers_count()
            self.friendsCount = friends_count
            self.followersCount = followers_count
            if followers_count > Config.get_config().threshold_followers:
                self.rule.mark_protected(db_put=True)
                return True
            if friends_count < fe_const.SKIP_UNFOLLOW_THRESHOLD:
                self.skip_unfollow = True
            if followers_count > fe_const.UNFOLLOW_CMP_ACCTS_THRESHOLD:
                self.unfollow_cmp_accts = True
            self.reset_timeout()
            if self._executeOne():
                if self.apiLimitExceeded:
                    self.rule.set_schedule_2_next_15_mins(db_put=True)
                logging.info("Finished processing rule '%s', unlocked channel '%s'." % (self.rule.name, self.channel.chid_handle_uid_str()))
                return True
        except Exception, ex:
            if self.rule is None:
                logging.exception("Could not get follow campaign object from id %s:" % ruleId)
            else:
                self.handleException(ex)
            if not self.apiLimitExceeded:
                retry += 1
                if retry < 3:
                    deferred.defer(self.__class__.deferred_execute_one_handler, ruleId=ruleId, retry=retry)
            return True
            
    def _executeOne(self):
        """
        Execute the one rule.
        Return true if the rule is finished, else False (Timeout).
        """
        if self.apiLimitExceeded:
            return True
        if self.rule.finished():
            return True
        if not self._initOne():
            return False
        if self.apiLimitExceeded:
            return True
        if not self._executeUnfollow():
            return False
        if self.apiLimitExceeded:
            return True
        if self.unfollow_only:
            logging.info("Skipped follow for unfollow only channel %s of follow campaign '%s'." % (self.channel.chid_handle_uid_str(), self.rule.name))
        else:
            if not self._executeFollow():
                return False
        return True

    def _initOne(self):
        """
        Return true if initialization is finished, else False (Timeout).
        """
        self.loadSafeFriendSet()
        if self._safeFriendSet is None:
            return False
        self.loadCompleteFriendList()
        if self._completeFriendList is None:
            return False
        completeFriendCount = 0 if self._completeFriendList is None else self._completeFriendList.count()
        logging.info("Follow rule '%s' complete friend list length is %s." % (self.rule.name, completeFriendCount))
        if self._once_suspended_list is None:
            self._once_suspended_list = OnceSuspendedCmpAcctSetCache.get(fallback=set([]))
        return True
        
    def _executeUnfollow(self):
        """
        Execute the un-follow portion of a rule. The unfollow logic should be exactly the same for all follower rules.
        Un-follow friends who are not followers, and not on safelist, and were added at least X days ago, as defined in the rule. 
        Return true if the rule is finished, else False (Timeout).
        This function assumes channel initialization is done.
        Retrieve complete follower history to memory, build a big set. 
        For now, we only do single thread processing. So there is worry for access conflicts. 
        """
        logging.info("Started unfollowing for %s." % self.rule.name)
        if self.skip_unfollow:
            logging.info("Skipped unfollowing because %s has less than %d friends." % (self.channel.chid_handle_uid_str(), self.friendsCount))
            return True
        utcnow = datetime.datetime.utcnow()
        parent = self.rule.parent()
        hourlyStats = ChannelHourlyStats.get_or_insert_by_parent_and_datetime(parent)
        offset = 0
        if self.rule.exceedMaxHourlyUnfollow(self._once_suspended_list, hourlyStats.unfollowCount, offset=offset):
            return True
        unfollowFriendList = UnfollowFriendList.get_by_parent(parent)
        if unfollowFriendList and self.rule.unfollowTimeCursor==unfollowFriendList.createdTime:
            hourlyFriendLists = [unfollowFriendList]
        else:
            startHour = datetime_util.truncate_2_hour(self.rule.unfollowTimeCursor)
            endHour = datetime_util.truncate_2_hour(self.rule.unfollowCutOffTime())
            query = HourlyFriendList.all().ancestor(parent).filter('createdTime < ', endHour).order('createdTime')
            if startHour is not None:
                query = query.filter('createdTime >= ', startHour)
            else:
                self.rule.unfollowIndexCursor = 0
            query = query.order('createdTime')
            hourlyFriendLists = query.fetch(3)
            if unfollowFriendList and (startHour is None or unfollowFriendList.createdTime >= startHour) and unfollowFriendList.createdTime < endHour:
                if len(hourlyFriendLists)>0 and unfollowFriendList.createdTime>hourlyFriendLists[-1].createdTime:
                    pass
                else:
                    hourlyFriendLists.append(unfollowFriendList)
                    hourlyFriendLists.sort(lambda x, y: cmp(x.createdTime, y.createdTime))

        isTimeout = False
        friends_count = self.friendsCount
        followers_count = self.followersCount
        hourlyStats.totalFollowerCount = followers_count
        hourlyStats.totalFriendCount = friends_count
        hourlyStats.put()
        if not self.skip_stats:
            dailyStats = ChannelDailyStats.get_or_insert_by_parent_and_datetime(parent, t=utcnow)
            dailyStats.totalFollowerCount = followers_count
            dailyStats.totalFriendCount = friends_count
            dailyStats.put()

        self.channel.friends_count=friends_count
        self.channel.followers_count=followers_count
        db.put(self.channel)
        
        for hourlyFriendList in hourlyFriendLists:
            if self.isTimeout():
                return False
            if self.over_execution_limit():
                return True
            if self.rule.exceedMaxHourlyUnfollow(self._once_suspended_list, hourlyStats.unfollowCount, offset=offset):
                return True
            if hourlyFriendList.createdTime != self.rule.unfollowTimeCursor:
                if self.rule.unfollowTimeCursor and self.rule.unfollowTimeCursor > hourlyFriendList.createdTime:
                    continue
                else:
                    self.rule.unfollowTimeCursor = hourlyFriendList.createdTime
                    self.rule.unfollowIndexCursor = 0
                    db.put(self.rule)
            friendList = list(hourlyFriendList.getFriends())
            unfollowCount = 0
            cursor = self.rule.unfollowIndexCursor
            startIndex = cursor          
            while cursor < len(friendList):
                if self.isTimeout():
                    isTimeout = True
                    break
                if self.rule.exceedMaxHourlyUnfollow(self._once_suspended_list, hourlyStats.unfollowCount+unfollowCount, offset=offset):
                    break
                if self.over_execution_limit():
                    break
                user_id = int(friendList[cursor])
                if user_id in self._safeFriendSet:
                    logging.info("Target %d is on safe list. Skip unfollowing!" % user_id)
                    cursor += 1
                    continue
                if self.apiLimitExceeded:
                    break
                try:
                    logging.debug("%s unfollowing %s..." % (self.channel.chid_handle_uid_str(), user_id))
                    self.executionApiCount += 1
                    if not context.is_dev_mode():
                        self.tapi.friendships.destroy(user_id=user_id)
                    unfollowCount += 1
                except Exception, ex:
                    self.handleException(ex)
                    if self.apiLimitExceeded:
                        break;
                    elif twitter_error.isNotFriend(ex):
                            unfollowCount += 1
                cursor += 1
            """ End of inner while loop """
            self.rule.unfollowIndexCursor = cursor
            db.put(self.rule)
            logging.info("Unfollow status for '%s': unfollowed=%d; skipped=%d; cursor=%d; listSize=%d; listTime=%s; listType=%s." %\
                         (self.rule.name, unfollowCount, cursor-startIndex-unfollowCount, cursor, len(friendList), hourlyFriendList.createdTime, hourlyFriendList.__class__.__name__))
            if cursor==len(friendList):
                db.delete(hourlyFriendList)
            if unfollowCount>0:
                hourlyStats.unfollowCount += unfollowCount
                hourlyStats.put()
                if not self.skip_stats:
                    dailyStats.unfollowCount += unfollowCount
                    dailyStats.put()
        """ End of outer for loop """
        return not isTimeout
            
    def cleanCompleteFriendList(self):
        completeFriendList = CompleteFriendList.get_or_insert_by_parent(parent=self.rule.parent())
        if completeFriendList:
            db.delete(completeFriendList)
        self._completeFriendList = None

    def loadCompleteFriendList(self):
        """ 
        This function is expected to be executed only by one request at a time for the same source channel. 
        """
        if self._completeFriendList is not None:
            return self._completeFriendList
        parent = self.rule.parent()
        completeFriendList = CompleteFriendList.get_or_insert_by_parent(parent=parent)
        if completeFriendList.lastRefreshTime is None:
            completeFriendList.lastRefreshTime = datetime.datetime(year=1990, month=1, day=1)
        utcnow = datetime.datetime.utcnow()
        if completeFriendList.lastRefreshTime < utcnow - datetime.timedelta(days=3):
            cursor = -1
            completeFriendList.friends=str(Set([]))
            friends = []
            retry = 0
            while cursor != 0 and retry < 3:
                try:
                    resp = self.tapi.friends.ids(user_id=self.rule.chid, cursor=cursor)
                    cursor = resp['next_cursor']
                    friends.extend(resp['ids'])
                    retry = 0
                except Exception, ex:
                    self.handleException(ex)
                    if self.apiLimitExceeded:
                        break
                    else:
                        retry += 1
            completeFriendList.addFriends(friends)
            completeFriendList.lastRefreshTime=utcnow    
            completeFriendList.isInitialized = True
            completeFriendList.put()
            logging.info("Refreshed complete friend list for %s." % self.channel.chid_handle_uid_str())
            unfollowFriendList = UnfollowFriendList.get_or_insert_by_parent(parent=parent)
            if not unfollowFriendList.initialized() or unfollowFriendList.createdTime != self.rule.unfollowTimeCursor:
                unfollowFriendList.reset(db_put=False)
                unfollowList = friends[:2000]
                unfollowFriendList.addFriends(unfollowList)
                filtered = self._filter_unfollow_friends(unfollowFriendList.getFriends())
                if self.unfollow_cmp_accts:
                    logging.info("Refreshing unfollow friend list, unfollowing all CMP accounts as well!")
                else:
                    unfollowFriendList.replaceFriends(filtered)
                createdTime = datetime.datetime.utcnow()
                if len(unfollowList) > 500:
                    createdTime = self.rule.unfollowPreCutOffTime()
                unfollowFriendList.createdTime = createdTime
                unfollowFriendList.put()
                logging.info("Refreshed unfollow friend list for %s." % self.channel.chid_handle_uid_str())
        if completeFriendList.initialized():
            self._completeFriendList = completeFriendList
        return self._completeFriendList

    def _filter_unfollow_friends(self, friends):
        chids = CompleteCmpAcctSetCache.get(fallback=set([]))
        filtered = list(set(friends) - set(chids))
        log_level = logging.WARNING if len(filtered) < len(friends) else logging.INFO
        logging.log(log_level, "_filter_unfollow_friends(): %d cmp accts, %d friends, %d non cmp accts" % (len(chids), len(friends), len(filtered)))
        return filtered
                    
    def loadSafeFriendSet(self):
        """ 
        This function is expected to be executed only by one request at a time for the same source channel. 
        """
        if self._safeFriendSet is not None:
            return self._safeFriendSet
        parent = self.rule.parent()
        safeFriendSet = SafeFriendSet.get_or_insert_by_parent(parent=parent)
        if safeFriendSet.lastRefreshTime is None:
            safeFriendSet.lastRefreshTime = datetime.datetime(year=1990, month=1, day=1)
        utcnow = datetime.datetime.utcnow()    
        if safeFriendSet.lastRefreshTime < safeFriendSet.modifiedTime or safeFriendSet.lastRefreshTime < utcnow - datetime.timedelta(days=3):
            friendSet = set([])
            listIds = safeFriendSet.listIds
            succeeded = True
            for listId in listIds:
                cursor = -1
                safeFriendSet.friends=str(Set([]))
                retry = 0
                while cursor!=0 and retry<3:
                    try:
                        resp = self.tapi.lists.members(list_id=listId, owner_id=self.rule.chid, cursor=cursor)
                        cursor = resp['next_cursor']
                        for user in resp['users']:
                            friendSet.add(user['id'])
                        retry = 0
                    except Exception, ex:
                        self.handleException(ex)
                        retry += 1
                        if self.apiLimitExceeded:
                            break
                if retry > 0:
                    """ Refresh safe list failed. Keep old values. """
                    succeeded = False
                    logging.error("Failed refreshing friend safe list for %s." % self.channel.chid_handle_uid_str())
                    break
            if succeeded:
                safeFriendSet.replaceFriends(friendSet)
                safeFriendSet.lastRefreshTime = utcnow    
                safeFriendSet.put()
                logging.info("Finished refreshing friend safe list for %s." % self.channel.chid_handle_uid_str())
        if safeFriendSet.initialized():
            self._safeFriendSet = safeFriendSet.getFriends()
        return self._safeFriendSet
            
    @classmethod
    def update_cmp_channel_list(cls):
        chinmap = cls._update_channel_list(follow_util.fe_master_req_url("log/gstats/cmp_acct_basic_info/"), CompleteCmpAcctBasicInfoCache)
        if chinmap:
            CompleteCmpAcctSetCache.set(set(chinmap.keys()))
        return chinmap
        
    @classmethod
    def update_once_suspended_channel_list(cls):
        return list(cls._update_channel_list(follow_util.fe_master_req_url("log/gstats/once_suspended_acct_list/"), OnceSuspendedCmpAcctSetCache))
        
    @classmethod
    def _update_channel_list(cls, url, cache):
        retry = 3
        while retry:
            try:
                chinmap = urllib.urlopen(url).read()
                if chinmap:
                    chinmap = eval(chinmap)
                    cache.set(chinmap)
                    logging.info("Finished updating CMP account info for %d accounts. %s" % (len(chinmap), url))
                    return chinmap
                    break
                else:
                    logging.error("Failed updating CMP account info. %s" % url)
            except Exception:
                logging.exception("Failed updating CMP account info. %s" % url)
            retry -= 1
        return None
        
    def _executeFollow(self):
        """
        Execute the follow portion of a rule.
        Return true if the rule is finished, else False (Timeout).
        This function assumes channel initialization is done.
        Retrieve complete friends history to memory, build a big set, and put into memcache. 
        For now, we only do single thread processing. So there is worry for access conflicts. 
        Then, retrieve the follower list based on the current target acct cursor. Follow them one by one.
        Before every timeout check, we store new friend info into friends history, and update the memcache accordingly.
        """
        if self.over_execution_limit():
            return True
        if self.over_follow_limit():
            logging.warn("Account already following too many people, skip following!")
            return True
        utcnow = datetime.datetime.utcnow()
        offset = 0
        parent = self.rule.parent()
        hourlyFriendList = HourlyFriendList.get_or_insert_by_parent_and_datetime(parent, t=utcnow)
        if hourlyFriendList.overFollowLimit or self.rule.exceedMaxHourlyFollow(self._once_suspended_list, hourlyFriendList.count(), offset=offset):
            self.apiLimitExceeded = True
            return True
        friendSet = Set(self._completeFriendList.getFriends()) 
        logging.info("Complete friend list has %d friends." % len(friendSet))         
        isTimeout = False
        while not self.rule.finished():
            if self.isTimeout():
                return False
            if hourlyFriendList.overFollowLimit or self.rule.exceedMaxHourlyFollow(self._once_suspended_list, hourlyFriendList.count(), offset=offset):
                self.apiLimitExceeded = True
                return True
            if self.over_execution_limit():
                return True
            tgtflwrs = SourceTgtflwrsProcessor(channel=self.channel).get_user_ids()  
            if len(tgtflwrs) == 0:
                logging.debug("No target follower for %s." % self.channel.chid_handle_uid_str())
                return True
            logging.debug("Target followers: %s" % str(tgtflwrs))
            newFriends = []
            index = 0
            for tgtflwr in tgtflwrs:
                if self.rule.exceedMaxHourlyFollow(self._once_suspended_list, hourlyFriendList.count()+len(newFriends), offset=offset):
                    self.apiLimitExceeded = True
                    break
                if self.over_execution_limit():
                    break
                if self.isTimeout():
                    isTimeout = True
                    break
                index += 1
                if tgtflwr in friendSet: 
                    logging.info("%s is already following %s, skip." % (self.channel.chid_handle_uid_str(), tgtflwr)) 
                    continue
                try:
                    self.executionApiCount += 1
                    if not context.is_dev_mode():
                        self.tapi.friendships.create(user_id=tgtflwr)
                    newFriends.append(tgtflwr)
                    logging.debug("%s following %s succeeded." % (self.rule.src_channel_name(), tgtflwr))
                except Exception, ex:
                    logging.warn("%s following %s failed." % (self.rule.src_channel_name(), tgtflwr))
                    self.handleException(ex)
                    if self.apiLimitExceeded:
                        hourlyFriendList.overFollowLimit = True
                        hourlyFriendList.put()
                        break
                    else:
                        continue
            """ End of inner while loop """
            update_msg = "%s followed %d followers, skipped %d." % (self.channel.chid_handle_uid_str(), len(newFriends), index - len(newFriends))
            logging.debug(update_msg)
            SourceTgtflwrsProcessor(channel=self.channel).increment_cursor(index)
            updated_objs = []
            newCompleteFriends = [] 
            if len(newFriends)>0:
                hourlyFriendList.addFriends(newFriends)
                hourlyStats = ChannelHourlyStats.get_or_insert_by_parent_and_datetime(parent, t=utcnow)
                hourlyStats.followCount += len(newFriends)
                updated_objs.append(hourlyFriendList)
                updated_objs.append(hourlyStats)
                newCompleteFriends.extend(newFriends) 
                if not self.skip_stats:
                    dailyStats = ChannelDailyStats.get_or_insert_by_parent_and_datetime(parent, t=utcnow)
                    dailyStats.followCount += len(newFriends)
                    db.put(dailyStats)
            if len(newCompleteFriends)>0: 
                self._completeFriendList.addFriends(newCompleteFriends) 
                friendSet.update(newCompleteFriends) 
                updated_objs.append(self._completeFriendList) 
            if len(updated_objs)>0:
                db.put(updated_objs)
                if newFriends:
                    logging.info("Followed successfully. %s" % update_msg)
                else:
                    logging.info(update_msg)
            db.put(self.rule)
        """ End of outer while loop """
        return not isTimeout

    @classmethod
    def deferred_execute_one_handler(cls, ruleId, retry=0):
        context.set_deferred_context(deployfe)
        return cls()._executeOneHandler(ruleId, retry)

    @classmethod
    def deferred_migrate(cls):
        context.set_deferred_context(deployfe)
        all_campaigns = cls().execute_query_all(params={})
        old = []
        new = {}
        for campaign in all_campaigns:
            try:
                parent = campaign.parent()
            except:
                old.append(campaign)
                continue
            if not isinstance(parent, FeParentChannel):
                old.append(campaign)
            else:
                new[campaign.chid] = campaign
        db.delete(old)
        logging.info("Deleted %d old campaigns." % len(old))
        all_channels = TAccountProcessor().execute_query_all()
        create_count = 0
        for channel in all_channels:
            chid = channel.chid_int()
            uid = channel.parent().uid
            if new.has_key(chid) or channel.deleted:
                continue
            state = camp_const.CAMPAIGN_STATE_ACTIVATED if channel.state==channel_const.CHANNEL_STATE_NORMAL else camp_const.CAMPAIGN_STATE_SUSPENDED
            campaign = FollowCampaign.get_or_insert_by_chid_uid(chid, uid, state=state)
            new[chid] = campaign
            create_count += 1
        logging.info("Finished migration with creating %d new campaigns. Total new campaign count is %d." % (create_count, len(new)))

        all_campaigns = cls().execute_query_all(params={})
        old = []
        new = {}
        for campaign in all_campaigns:
            parent = campaign.parent()
            if not isinstance(parent, FeParentChannel):
                old.append(campaign)
            else:
                new[campaign.chid] = campaign
        db.delete(old)
        logging.info("Deleted %d old campaigns." % len(old))
        all_channels = TAccountProcessor().execute_query_all()
        create_count = 0
        for channel in all_channels:
            chid = channel.chid_int()
            uid = channel.parent().uid
            if new.has_key(chid) or channel.deleted:
                continue
            state = camp_const.CAMPAIGN_STATE_ACTIVATED if channel.state==channel_const.CHANNEL_STATE_NORMAL else camp_const.CAMPAIGN_STATE_SUSPENDED
            campaign = FollowCampaign.get_or_insert_by_chid_uid(chid, uid, state=state)
            new[chid] = campaign
            create_count += 1
        logging.info("Finished migration with creating %d new campaigns. Total new campaign count is %d." % (create_count, len(new)))

    @classmethod
    def deferred_sync(cls):
        context.set_deferred_context(deployfe)
        cls.update_cmp_channel_list()
        cls.update_once_suspended_channel_list()
        cls.sync_channel_campaign_statuses()

    @classmethod
    def sync_channel_campaign_statuses(cls):
        channel_update_count = 0
        channel_delete_count = 0
        camp_update_count = 0
        camp_delete_count = 0
        try:
            update_list = []
            chinmap = CompleteCmpAcctBasicInfoCache.get(fallback={})
            all_channels = TAccountProcessor().execute_query_all()
            valid_chids = set([])
            for channel in all_channels:
                chid = channel.chid_int()
                uid = channel.parent().uid
                if channel.deleted:
                    db.delete(channel)
                    channel_delete_count += 1
                    continue
                valid_chids.add(channel.chid_int())
                chinfo = chinmap.get(chid, None)
                if chinfo is None:
                    logging.error("Missing %s basic info!" % channel.chid_handle_uid_str())
                    continue
                new_channel_state = chinfo[0]
                if new_channel_state != channel.state:
                    channel.state = new_channel_state
                    update_list.append(channel)
                    channel_update_count += 1
                new_camp_state = camp_const.CAMPAIGN_STATE_ACTIVATED if channel.state==channel_const.CHANNEL_STATE_NORMAL else camp_const.CAMPAIGN_STATE_SUSPENDED
                campaign = FollowCampaign.get_or_insert_by_chid_uid(chid, uid, state=new_camp_state)
                if new_camp_state != campaign.state:
                    campaign.state = new_camp_state
                    update_list.append(campaign)
                    camp_update_count += 1
                db.put(update_list)
            all_campaigns = cls().execute_query_all(params={})
            for campaign in all_campaigns:
                parent = campaign.parent()
                if not isinstance(parent, FeParentChannel) or parent.chid not in valid_chids:
                    db.delete(campaign)
                    camp_delete_count += 1
        except Exception:
            logging.exception("Error when syncing statuses for channels and follow campaigns!")
        logging.info("Updated %d and deleted %d channels. Updated %d and deleted %d campaigns." % (channel_update_count, channel_delete_count, camp_update_count, camp_delete_count))
        
    @classmethod
    def clean_suspended(cls):
        channel_count = 0
        camp_count = 0
        try:
            all_channels = TAccountProcessor().execute_query_all(params=dict(state=channel_const.CHANNEL_STATE_SUSPENDED))
            db.delete(all_channels)
            channel_count = len(all_channels)
            all_camps = cls().execute_query_all(params=dict(state=camp_const.CAMPAIGN_STATE_SUSPENDED))
            db.delete(all_camps)
            camp_count = len(all_camps)
        except Exception:
            logging.exception("Error when cleaning suspended channels and follow campaigns!")
        logging.info("Deleted %d suspended channels and %d suspended campaigns." % (channel_count, camp_count))
        return channel_count, camp_count

        
