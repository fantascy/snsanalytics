import datetime, time
import logging
import urllib
import random
from sets import Set, ImmutableSet

from google.appengine.ext import db
import json
from twitter import errors as twitter_error

import deploysns
import context
from common import consts as common_const
from common.utils import string as str_util, url as url_util
from common.utils import timezone as ctz_util
from common.utils import datetimeparser
from common.utils import fulltextmatcher
from common.utils.error import Error
from common.utils.facebook import GraphAPI
from common.content import feedfetcher
from common.content.trove import consts as trove_const
from common.content.trove import api as trove_api
from sns import limits as limit_const
from sns.serverutils import url as server_url_util, deferred, memcache
from sns.core.core import User, StandardCampaignParent, SystemStatusMonitor, ChannelParent
from sns.core import base as db_base
from sns.core import core as db_core
from sns.api import errors as api_error
from sns.api import consts as api_const
from sns.api.base import BaseProcessor, AssociateModelBaseProcessor
from sns.chan import consts as channel_const
from sns.chan.models import TAccount, FAccount, FAdminPage
from sns.cont import consts as cont_const
from sns.cont.api import Domain2CSProcessor
from sns.cont.topic.api import TopicProcessor
from sns.feedbuilder import api as feedbuilder_api
from sns.camp import consts as camp_const
from sns.camp.api import CampaignProcessor, SCHEDULE_EXPEDITE_FACTOR
from sns.camp.models import Retweet
from sns.deal import utils as deal_util
from sns.deal.models import TopDeal
from sns.usr.api import UserProcessor
from sns.usr.models import UserPostCounter,UserStats, UserExecuteCounter
from sns.url.models import ShortUrlReserve, GlobalUrl, GlobalUrlCounter, Website
from sns.url.api import ShortUrlProcessor
from sns.ads import api as ads_api 
from sns.log import consts as log_const
from sns.log import api as log_api
from sns.post import consts as post_const
from models import SCampaign, MCampaign, QMCampaign, FCampaign, SExecution, SPost, FeedPostLog
from models import StandardCampaignSmall, MessageCampaignSmall, DirectMessageCampaignSmall, FeedCampaignSmall


"""
Retrieving text for url is time consuming. So we will cache the text of an URL in memcache for some duration.
"""
DEFAULT_URL_TEXT_CACHE_TIME = 600 

FACEBOOK_POST_ATTRS = ['fbName', 'fbLink', 'fbCaption', 'fbDescription', 'fbPicture']
FACEBOOK_POST_MAP ={'fbName':'name',
                    'fbLink':'link',
                    'fbCaption':'caption',
                    'fbDescription':'description',
                    'fbPicture':'picture',
                    }

WARNING_ERRORS = ['Feed action request limit reached',
                  'User not visible',
                  'Skipped status update',
                  'Incorrect signature',
                  'over daily status update limit',
                  'HTTP Error 400: Bad Request',
                  ]


XG_ON_TEMP = db.create_transaction_options(xg=True)


class StandardCampaignProcessorError(Exception):
    pass


class StandardCampaignProcessor(CampaignProcessor):
    MAX_CAMPAIGNS_PER_DEFERRED_JOB = 50

    def __init__(self, timeout=CampaignProcessor.TIMEOUT_FRONTEND):
        CampaignProcessor.__init__(self, timeout=timeout)
        self._currentRule = None
        self._urlMappingIdBlocks = None
        self._posts = []
        self._posting = None
        self._userDailyPostLimit = None
        self._remainingLimit = None
        self._redirectUids = log_api.getPatternValue(log_const.PATTERN_REDIRECT_USER)
        
    @classmethod
    def supportedOperations(cls):
        return ImmutableSet([api_const.API_O_ACTIVATE, 
                           api_const.API_O_DEACTIVATE, 
                           api_const.API_O_POST, 
                           api_const.API_O_SCHEDULE, 
                           api_const.API_O_EXECUTE, 
                           api_const.API_O_POST_JOB_COUNT, 
                           api_const.API_O_POST_EXPEDITE,
                           api_const.API_O_CRON_EXECUTE, 
                           api_const.API_O_QUERY_ALL,
                           api_const.API_O_CHANGE_CAMPAIGN_SNSANALYTICS_SOURCE,
                           ]).union(BaseProcessor.supportedOperations())
    
    def getModel(self):
        return SCampaign
        
    def getSmallModel(self):
        return StandardCampaignSmall
    
    def getPostType(self):
        pass

    def getDefaultScheduleType(self):
        pass
    
    def defaultOrderProperty(self):
        return "nameLower"  

    def limit_exceeded(self, timeout=5):
        daily_post_limit_exceeded = self._remainingLimit <= 0
        if daily_post_limit_exceeded :
            logging.warning("User '%s' reached daily post limit of %s!" % (self._currentRule.parent().email(), self._userDailyPostLimit))
        return daily_post_limit_exceeded or BaseProcessor.isTimeout(self, timeout)
                    
    def create(self, params):
        user = params.get('user', None)
        uid = user.uid if user else None
        rules = StandardCampaignProcessor().query_base(uid=uid).order('-number').fetch(limit=1)
        if len(rules) == 0:
            params['number'] = 0
        else:
            params['number'] = rules[0].number + 1
        batch = params['number']/post_const.POSTING_RULE_PER_BATCH
        parent = StandardCampaignParent.get_or_insert_parent(batch, uid=uid)
        params['parent'] = parent
        params['userHashCode'] = parent.userHashCode
        rule = CampaignProcessor.create(self, params)
        self.activate(rule)
        return rule
                            
    def campaignQueueName(self):
        pass
    
    def cron_execute(self, params):
        op = params.get('op', None)
        if op:
            if op=='shuffle_schedule_start':
                deferred.defer(self.__class__._deferred_shuffle_schedule_start)
            return
        for i in range(0, User.USER_HASH_SIZE):
            deferred.defer(self.__class__._deferred_execute, userHashCode=i, queueName=self.campaignQueueName())
            
    @classmethod
    def _deferred_execute(cls, userHashCode):
        context.set_deferred_context(deploy=deploysns)
        return cls(timeout=cls.TIMEOUT_BACKEND).execute(userHashCode)

    def monitorKeyName(self, userHashCode):
        pass
        
    def execute(self, userHashCode):
        """
        Query all due active rules and unfinished executing rules at the moment. 
        """
        monitorKeyName = self.monitorKeyName(userHashCode)
        if not SystemStatusMonitor.acquire_lock(monitorKeyName, log=True, preempt=self.__class__.TIMEOUT_BACKEND+self.__class__.TIMEOUT_MARGIN):
            return 0
        count = 0
        try:
            count = self._executeOneUserHashCode(userHashCode)
        except:
            logging.exception("Error when executing post campaigns for user hash %d:" % userHashCode)
        finally:
            SystemStatusMonitor.release_lock(monitorKeyName)
            return count
    
    def _executeOneUserHashCode(self, userHashCode):
        utcnow = datetime.datetime.utcnow()        
        activeRuleQuery = self.getModel().all().filter('deleted',False).filter('state', camp_const.CAMPAIGN_STATE_ACTIVATED).filter('userHashCode',userHashCode).filter('scheduleNext <= ', utcnow).order('scheduleNext')
        activeRuleCount = activeRuleQuery.count(1000)
        if activeRuleCount==0 :
            logging.debug('No rules due to execute for hash %s!' % str(userHashCode))
            return 0
        maxRuleCount = self.__class__.MAX_CAMPAIGNS_PER_DEFERRED_JOB
        if activeRuleCount>maxRuleCount:
            logging.info("Total %d rules due to execute for hash %s, processing %s - maximum to be processed per deferred job of %s." % (activeRuleCount,str(userHashCode), maxRuleCount, self.__class__))
            activeRuleCount = maxRuleCount

#         if userHashCode == 1:
#             activeRules = activeRuleQuery.fetch(500)
#             active_rule_info = [(str(rule.basic_info()), str(rule.scheduleNext)) for rule in activeRules]
#             logging.info("Dump of all active rules due for hash %d. %s" % (userHashCode, active_rule_info))
#             activeRules = activeRules[:activeRuleCount]
#         else:
#             activeRules = activeRuleQuery.fetch(activeRuleCount)
        activeRules = activeRuleQuery.fetch(activeRuleCount)
        if len(activeRules)!=0 :
            mostDelayedRule = activeRules[0]
            self.logScheduleDelayStatus(mostDelayedRule.scheduleNext)
        
        parent_rules = {}
        sorted_parents = []
        for rule in activeRules:
            if self.isTimeout():
                break
            parent = rule.parent()
            if not parent_rules.has_key(parent):
                parent_rules[parent] = [rule]
                sorted_parents.append(parent)
            else:
                parent_rules[parent].append(rule)
        logging.info("Hashed %d active post campaigns into %d buckets." % (len(activeRules), len(parent_rules)))

        deferredJobCount = 0
        deferredRuleCount = 0
        for parent in sorted_parents:
            if self.isTimeout():
                break
            rules = parent_rules[parent]
            modelUser = User.get_by_id(parent.uid)
            if not modelUser.isApproved(check_login_user=False):
                for rule in rules:
                    rule.state = camp_const.CAMPAIGN_STATE_ONHOLD
                db.put(rules)
                logging.info("Suspended %d rules for unapproved user %s!" % (len(rules), modelUser.mail))
                continue
            deferredJobCount += 1
            deferredRuleCount += len(rules)
            ids = []
            for rule in rules:
                if self.isTimeout():
                    break
                ids.append(rule.id)
                scheduleType = rule.getScheduleType()
                if scheduleType == camp_const.SCHEDULE_TYPE_NOW:
                    rule = self._doPostNow(rule)
                if scheduleType == camp_const.SCHEDULE_TYPE_ONE_TIME:
                    rule = self._doPostOneTime(rule)
                if scheduleType == camp_const.SCHEDULE_TYPE_RECURRING:
                    rule = self._doPostRecurring(rule)
                rule.revision += 1
            try:  
                db_base.txn_put(rules) 
                self._execute_one_rule_parent(ids)
            except:
                logging.exception("Error when executing %d post campaigns for user %d:" % (len(rules), parent.uid))  
            
        logging.info("Executed %d active post campaigns for %d rule parents." % (deferredRuleCount, deferredJobCount))
        return deferredRuleCount

    def _execute_one_rule_parent(self, ids):
        """
        Execute the one rule, keep deferring until it is fully finished execution.
        Return true if the rule is finished, else False (Timeout).
        """
        successCount = 0
        failureCount = 0
        userEmail = "Unknown"
        for rid in ids:
            if self.isTimeout():
                break
            try :
                rule=db.get(rid)
                contents = rule.contents
                channelNum = 0
                googleCount = 0
                bingCount = 0
                for key in rule.channels:
                    channel = db.get(key)
                    if channel and not channel.deleted and not channel.state == channel_const.CHANNEL_STATE_SUSPENDED:
                        channelNum+=1
                for key in rule.fbDestinations:
                    index = key.find(':')
                    try :
                        channel = db.get(key[:index])
                        if channel and not channel.deleted and not channel.state == channel_const.CHANNEL_STATE_SUSPENDED:
                            channelNum+=1
                    except :
                        self._fixFacebookChannelKey(rule, key[:index])
                        channelNum = len(rule.fbDestinations)
                        break
                contentNum = 0
                for key in contents:
                    content = db.get(key)
                    if not content.deleted:
                        contentNum+=1
                    if content.__class__.__name__ == 'Feed':
                        if feedfetcher.is_googlenews_feed(content.url):
                            googleCount += 1
                        elif feedfetcher.is_bing_feed(content.url):
                            bingCount += 1
                if channelNum==0 or contentNum==0:
                    rule.state = camp_const.CAMPAIGN_STATE_INIT
                    db.put(rule)
                    logging.warning("Inactivate campaign '%s' on no channel or content!" % rule.name)
                    continue
                googleWork = SystemStatusMonitor.get_system_monitor(cont_const.MONITOR_GOOGLE_FEED_SWITCH).work
                bingWork = SystemStatusMonitor.get_system_monitor(cont_const.MONITOR_BING_FEED_SWITCH).work
                if (googleCount >0 and not googleWork) or (bingCount>0 and not bingWork):
                    user = User.get_by_id(rule.parent().uid)
                    if user.isContent:
                        rule.state = camp_const.CAMPAIGN_STATE_ERROR
                        db.put(rule) 
                        logging.warning("Marked as an error campaign: %s!" % rule.basic_info())
                        continue   
                userEmail = rule.parent().keyNameStrip()
                if self._executeOneCampaign(rule)[0]:
                    successCount += 1
                    logging.debug("Finished executing campaign %s." % rule.basic_info())
                    continue
                else :
                    if not self.isTimeout():
                        raise StandardCampaignProcessorError("Expected timeout, but not!")
                    break;
            except Exception:
                failureCount += 1
                rule=db.get(rid)
                userEmail = rule.parent().keyNameStrip()
                logging.exception("Unexpected error when executing campaign %s!" % rule.basic_info())
        unprocessedCount = len(ids) - successCount - failureCount
        logging.debug("%s deferred job of user '%s': total %d, success %d, failure %d, unfinished %d." % (self.__class__, userEmail, len(ids), successCount, failureCount, unprocessedCount))
            
    def _executeOneCampaign(self, rule):
        """
        Execute the one rule.
        Return true if the rule is finished, else False (Timeout).
        """
        rule.syncState()
        return self.post(rule)
    
    def _fixFacebookChannelKey(self, rule, key):
        logging.error("Fixing old fb channel key: %s" % key)
        try :
            oldChannelInfo = rule.fbDestinations
            newChannelInfo = []
            for oldInfo in oldChannelInfo :
                key = oldInfo.split(':')[0] 
                dbKey = db_core.normalize_2_key(key)
                logging.info("Old key info(kind, id_or_name, parent): ('%s', '%s', '%s')" % (dbKey.kind(), dbKey.id_or_name(), dbKey.parent()))
                newDbKey = db.Key.from_path(dbKey.kind(), dbKey.id_or_name(), parent=ChannelParent.get_or_insert_parent(rule.uid).key())
                if newDbKey is None :
                    logging.error("Could not resolve old key to new key!")
                    return
                else :
                    channel = db.get(newDbKey)
                    if channel is not None :
                        logging.info("Found the channel for the old key!")
                        newInfo = "%s:%s" % (str(newDbKey), oldInfo.split(':')[1])
                        newChannelInfo.append(newInfo)
                    else :
                        logging.error("Couldn't find the channel for the old key!")
                        newChannelInfo.append(oldInfo)
            if len(newChannelInfo)>0 :
                logging.info("Old fb channel info: %s" % str(oldChannelInfo))
                logging.info("New fb channel info: %s" % str(newChannelInfo))
                rule.fbDestinations = newChannelInfo
                db.put(rule)
        except :
            logging.exception("Error when fixing old FB channel key:")
    
    def pre_transaction(self):
        Website.get_all(cache_if_missing=True)
            
    def expedite(self, params):
        """
        Expedite scheduled job processing by a time factor. The params include:
        factor - An integer expedite factor. Default to 1. For instance a factor of 15 makes a '15Min' schedule as '1Min' schedule
        expire - Minutes this expedite will expire.
        An admin job, and a primarily debug tool
        """
        factor = int(params.get('factor', 1))
        expire = long(params.get('expire', 0))
        memcache.set(SCHEDULE_EXPEDITE_FACTOR, factor, expire)
        logging.info("Set SCHEDULE_EXPEDITE_FACTOR to a factor of %s and expiring in %s seconds" % (factor, expire))
        return factor

    def post(self, rule, immediate=False):
        """
        Return True if the rule is finished processing normally. 
        """ 
        
        def initWithLimitCheck(rule):
            """
            Return False if daily post limit exceeded.
            """
            uid = str(rule.parent().uid)
            modelUser = User.get_by_id(rule.parent().uid)
            currPostCounter = UserPostCounter.get_by_key_name(UserPostCounter.keyName(uid),modelUser)
            currPostCounter.update(modelUser)
            userDailyPostLimit = limit_const.LIMIT_POST_DAILY_PER_USER
            remainingLimit = userDailyPostLimit - currPostCounter.day
            if remainingLimit <= 0 :
                logging.warning("User '%s' reached daily post limit of %s when processing rule '%s'!" % (uid, userDailyPostLimit, rule.name))
                return False
            if not modelUser.isContent:
                currentExecutionCounter = UserExecuteCounter.get_or_insert(UserExecuteCounter.keyName(uid),parent=modelUser)
                currentExecutionCounter.update()
                userDailyExecutionLimit = limit_const.LIMIT_EXECUTION_DAILY_PER_USER
                if currentExecutionCounter.day >= userDailyExecutionLimit:
                    logging.warning("User '%s' reached daily execution limit of %s when processing rule '%s'!" % (uid, userDailyExecutionLimit, rule.name))
                    return False
            self._userDailyPostLimit = userDailyPostLimit
            self._remainingLimit = remainingLimit
            self._currentRule = rule
            self._resvUrlMappingIds()
            self._posts = []
            self._posting = None
            return True
            
        try :
            
            if not initWithLimitCheck(rule) :
                """
                User daily limit exceeded. Move the task to 11 (use a prime number) hours later. 
                """
                elevenHoursLater = datetime.datetime.utcnow() + datetime.timedelta(hours=11)
                rule.scheduleNext = elevenHoursLater
                rule.state = camp_const.CAMPAIGN_STATE_ACTIVATED
                db.put(rule)
                return True,[]
            
            uid = str(rule.parent().uid)
            modelUser = User.get_by_id(rule.parent().uid)
                      
            if not modelUser.isContent:
                executionCounter = UserExecuteCounter.get_or_insert(UserExecuteCounter.keyName(uid),parent=modelUser)
                executionCounter.increment()
                executionCounter.put()

            result_twitter=[]
            result_facebook=[]
            result_list=[]
            post_success=True
            
            contents = db.get(rule.contents)
            channels = []
            for c in rule.channels :
                channels.append([db.get(c)])
            for c in rule.fbDestinations:
                index =  str(c).find(':')
                wallId = c[index+1:]
                channelKey = c[:index]
                try :
                    channels.append([db.get(channelKey),wallId])
                except :
                    self._fixFacebookChannelKey(rule, channelKey)
                    break
            
            if isinstance(self._currentRule, FCampaign):
                user = User.get_by_id(rule.parent().uid)
                if not rule.has_valid_channel(user=user):
                    self.deactivate(rule)
                    return True, []
                feedEntryList=[]
                recordList=[]
                freq = datetimeparser.timedelta_in_minutes(datetimeparser.parseInterval(rule.scheduleInterval))
                extra = {'blacklist_func': self.__class__.on_cs_blacklist,}
                if rule.channels:
                    channel = db.get(rule.channels[0])
                    if channel and isinstance(channel, TAccount) and channel.topics:
                        topics = channel.topics
                        extra = {'blacklist_func': self.__class__.on_cs_blacklist,
                                 'ads_func': ads_api.AdsProcessor.get_ads,
                                 'topics': topics,
                                 'channel': channel,
                                 'user': user,  
                                 }
                for feedKey in rule.contents :
                    feed = db.get(feedKey)
                    if db_base.isDeleted(feed) :
                        continue
                    record = FeedPostLog.get_or_insert_by_feed_campaign(feed, rule)
                    feed_fetcher = feedbuilder_api.FeedBuilderProcessor.get_feed_fetcher_by_feed(feed, parseFeedUrlFromPage=False)
                    feed_entries = feed_fetcher.fetch(
                        history=record.feedEntries, 
                        limit=rule.maxMessagePerFeed, 
                        freq=freq, 
                        is_cmp=user.isContent, 
                        extra=extra,
                        )
                    logging.debug("Fetched %d feed entries for rule %s" % (len(feed_entries), rule.name))
                    feedEntryList.append(feed_entries)
                    recordList.append(record)
                index = 0
                for entries in feedEntryList:
                    content = contents[index]
                    topics = content.getTopics()
                    for entry in entries:
                        globalUrl = GlobalUrl.get_or_insert_by_feed_entry(entry, title_decorator=rule.truncateMsg)
                        entry.url = globalUrl.url()
                        entry.globalUrl = globalUrl
                        globalUrlCounter = GlobalUrlCounter.get_or_insert_by_url(entry.url)
                        addTopic = False
                        for topic in topics:
                            if topic not in globalUrlCounter.topics:
                                addTopic = True
                                globalUrlCounter.topics.append(topic)
                        if addTopic:
                            globalUrlCounter.put()
                    index += 1
                self.pre_transaction()
                db.run_in_transaction_options(XG_ON_TEMP, self._trans_post, contents, channels, feedEntryList, recordList)
            else:
                for msg in contents:
                    if msg.url:
                        msg.url = GlobalUrl.normalize(msg.url)
                        globalUrl = GlobalUrl.get_or_insert_by_page_parser(msg.url)
                db.run_in_transaction_options(XG_ON_TEMP, self._trans_post, contents, channels)
                
                if immediate :
                    for post in self._posts :
                        postProcessor = PostProcessor()
                        post_result,error_record = postProcessor._do_one_post(post, self._posting, modelUser)
                        UserProcessor().incrementStats(postProcessor._userStats, modelUser)
                        if not post_result:
                            post_success=False
                            post_result=None
                        if post.channel.type == channel_const.CHANNEL_TYPE_TWITTER:
                            result_twitter.append((post_result,error_record,post.channel.name,post.channel.type))
                        else:
                            name, url, channelType = getFacebookPostToNameAndUrl(post)
                            if channelType=='Page' or channelType=='Group':
                                parent_name=post.channel.name
                                parent_url=post.channel.profileUrl
                            else:
                                parent_name=''
                                parent_url=''
                            result_facebook.append((post_result, error_record, name, channelType, url, parent_name, parent_url))
                    result_list=[result_twitter,result_facebook]
            self._saveRemainingUrlMappingIdReserve()
            if immediate:
                return post_success, result_list
            else:
                return True, result_list
        except Exception:
            logging.exception("Unexpected error in executing campaign %s!" % (rule.basic_info(), ))
            self._saveRemainingUrlMappingIdReserve()
            return False, []

    def _trans_post(self,contents,channels,feedEntryList=None,recordList=None):
        """
        Execute a post action of the rule. Raise error if the rule is not activated. 
        After post, set state to expired based on posting schedule.
        """
        rule = self._currentRule
        if rule.className()=='FCampaign':
            self._doPost(contents,channels,feedEntryList,recordList)
        else:
            self._doPost(contents,channels)
        logging.debug('Finished post for rule: %s' % rule.name)
        return rule

    def _doPost(self,contents,channels):
        """
        This is meant to be the shared common action function for all different post schedules. 
        So this function only generates the Posting and Post model objects. It doesn't update the Schedule object, or the Rule object.
        Sanity checks are already done. just go to perform the action.
        """
        errMsg = "Trying to call unimplemented function PostingCampaign._doPost()!"
        logging.error(errMsg)
        raise api_error.ApiError(api_error.API_ERROR_UNKNOWN, errMsg)

    def _doPostNow(self,rule):
        """
        Sanity checks are already done. just go to perform the action.
        """
        
        rule.state = camp_const.CAMPAIGN_STATE_EXPIRED
        return rule
        
    def _doPostOneTime(self,rule):
        """
        Sanity checks are already done. just go to perform the action.
        """
        rule.state = camp_const.CAMPAIGN_STATE_EXPIRED
        return rule

    def _doPostRecurring(self, rule):
        """
        Sanity checks are already done. just go to perform the action.
        """
        now = datetime.datetime.utcnow()  
        if rule.scheduleStart > now and rule.scheduleStart > rule.scheduleNext:
            rule.scheduleNext = rule.scheduleStart
            return rule
        try:
            interval_td = datetimeparser.parseInterval(rule.scheduleInterval, memcache.get(SCHEDULE_EXPEDITE_FACTOR))
        except:
            logging.error("Invalid campaign schedule interval '%s'. %s" % (rule.scheduleInterval, rule.basic_info()))
            rule.state = camp_const.CAMPAIGN_STATE_ERROR
            return rule
        time_since_start = now - rule.scheduleStart
        interval = interval_td.days*86400 + interval_td.seconds
        seconds_since_start = time_since_start.days*86400 + time_since_start.seconds
        cycles = seconds_since_start/interval + 1
        rule.scheduleNext = rule.scheduleStart + cycles*datetime.timedelta(seconds=interval) 
        if rule.scheduleNext < now:
            logging.error("Campaign %s schedule next %s is older than current time %s!" % (rule.basic_info(), rule.scheduleNext, now))
        if rule.scheduleEnd is not None and rule.scheduleNext > rule.scheduleEnd:
            rule.state = camp_const.CAMPAIGN_STATE_EXPIRED
        return rule

    def _doPostUrl(self, content,channels, posting, msg, url, matched_rule_kwds, record=None, feedEntry=None):
        """
        Sanity checks are already done. just go to perform the action.
        """
        rule = self._currentRule
        msg = str_util.strip_one_line(msg)
        if msg is None:
            msg = ''
        if url:
            try:
                url = url.decode('utf-8')
            except:
                pass
        matched_trend_kwds = []
        posts = []
        for channelInfo in channels :
            if self.limit_exceeded() :
                break 
            if  len(channelInfo) == 1:
                wallId = 'twitter'
            else:
                wallId = channelInfo[1]
            channel = channelInfo[0]
            if channel.deleted or channel.state ==  channel_const.CHANNEL_STATE_SUSPENDED:
                continue
            posting.total += 1
            if self._skipKeywordMatch() :
                all_kwds = []
            else :
                all_kwds = self._union_keywords([matched_rule_kwds, matched_trend_kwds])
            trove_mention_type = trove_const.MENTION_NONE
            trove_mention_handle = None
            trove_hosted = False
            if url and context.is_trove_enabled():
                global_url = GlobalUrl.get_by_url(url)
                if global_url:
                    trove_hosted = global_url.is_trove_hosted()
#                 if global_url and global_url.is_trove_smartpicked():
#                     threshold = 1000
#                     rint = random.randint(0, 999)
#                     if rint < threshold:
#                         trove_mention_type = trove_const.MENTION_BOTH if rint < threshold/2 else trove_const.MENTION_PICKER
#                         trove_mention_handle = global_url.troveHandle
            postParent = self._currentRule.parent()
            if url:
                shortUrlResv = ShortUrlReserve.get_by_key_name(postParent.key().name(),parent=postParent)
                urlHash = shortUrlResv.firstCharacter + ShortUrlProcessor.extractShortUrlFromResv(self._urlMappingIdBlocks)
            else :
                urlHash = None
            display_url = ''
            if urlHash is None or rule.titleOnly:
                pass
            else:
                url_root = url_util.root_domain(url)
                if url_root=='trove.com':
                    logging.error("Please do NOT post trove.com pages directly! %s" % url)
                    continue
                if context.is_trove_enabled() and (trove_hosted or trove_mention_type != trove_const.MENTION_NONE):
                    trove_ads_mgr = ads_api.AdsProcessor.get_ads_mgr(url, channel, context_sensitive=False)
                    ads_decorated_url = trove_ads_mgr.get_advertised_url(url, mention_type=trove_mention_type) if trove_ads_mgr else None
#                     if url_util.root_domain(ads_decorated_url)=='trove.com' \
#                         and not datetimeparser.is_in_third_week_of_month(ctz_util.uspacificnow()):
                    if url_util.root_domain(ads_decorated_url)=='trove.com':
#                         display_url = trove_api.get_trove_short_url(ads_decorated_url, add_timestamp=True)
                        display_url = ads_decorated_url + '&ts=' + str(int(time.time()))
                elif self._use_original_domain(url) and isinstance(channel, TAccount):
                    display_url = url
                if not display_url: 
                    display_url = server_url_util.short_url(urlHash)
                display_url = ' %s' % display_url
            if channel.type == channel_const.CHANNEL_TYPE_TWITTER:
                tmsg = self._hashtag_decorate(msg, channel.topics)
                kwds = ' %s' % self._kwds_to_display(all_kwds, tmsg)
                suffix = ' %s' % rule.msgSuffix if rule.msgSuffix else ''
                trove_mention_str = trove_api.get_mention_str(trove_mention_type, trove_mention_handle)
                if trove_mention_str:
                    suffix = '%s %s' % (suffix, trove_mention_str)
                tweet = self._twitter_str_to_display(tmsg, display_url, kwds, suffix)
                if suffix:
                    logging.info("Prepared a curated tweet. %s" % tweet)
            elif channel.type == channel_const.CHANNEL_TYPE_FACEBOOK_ACCOUNT: 
                tmsg = msg
                tweet = self._facebook_str_to_display(tmsg, display_url)
            elif channel.type == channel_const.CHANNEL_TYPE_FACEBOOK_PAGE or channel.type == channel_const.CHANNEL_TYPE_FACEBOOK_APP: 
                tmsg = msg
                tweet = self._facebook_str_to_display(tmsg, display_url)
            tweet = str_util.strip_one_line(tweet)
            posts.append(dict(content=content, channel=channel, wallId=wallId, userHashCode=rule.userHashCode,
                              url=url, urlHash=urlHash, origMsg=msg, msg=tweet, uid=rule.parent().uid,
                              troveMentionType=trove_mention_type, feedEntry=feedEntry))
        if record:
            record.put()
        return posts
    
    def _use_original_domain(self, url):
        return url and url_util.root_domain(url) in post_const.ORIGINAL_URL_DOMAINS
    
    def _hashtag_decorate(self, msg, topics):
        hashtags = TopicProcessor().get_hashtags_for_topics(topics)
        if not hashtags:
            return msg
        words = msg.split(' ')
        for i in range(len(words)):
            if words[i] in hashtags:
                words[i] = '#' + words[i]
        return ' '.join(words) 

    def _twitter_str_to_display(self, tmsg, display_url, kwds, suffix):
        length = len(tmsg) + len(suffix)
        if display_url:
            length += common_const.TWITTER_SHORT_URL_LENGTH
        if length > 140:
            overflow = length - 140
            tmsg = str_util.slice(tmsg, "0:%s" % (len(tmsg) - overflow))
            return "%s%s%s" % (tmsg, display_url, suffix)
        else:
            left = 140 - length
            words = kwds.split()
            keyword = ''
            for word in words:
                a_word = ' ' + word
                if len(a_word) + len(keyword) > left:
                    break
                else:
                    keyword += a_word
            return "%s%s%s%s" % (tmsg, display_url, keyword, suffix)
        
    def _facebook_str_to_display(self, tmsg, display_url=None):
        return "%s %s" % (tmsg, display_url) if display_url else tmsg
        
    def _kwds_to_display(self, kwds, msg):
        ret_str = ''
        kwds = (' '.join(kwds)).split()
        for kwd in kwds :
            kwd_lower = kwd.lower().strip('#')
            ret_str += ' #' + kwd_lower
        return ret_str
        
    def _union_keywords(self, kwds_list):
        """
        Union all the kwds in the kwds_list in provided order.
        """
        if len(kwds_list) == 0 :
            return []
        
        ret_list = []
        ret_set = Set(ret_list)
        for i in range(0, len(kwds_list)) :
            for word in kwds_list[i] :
                if not ret_set.issuperset(Set([word])) :
                    ret_list.append(word)
                    ret_set.add(word)
        return ret_list

    
    def _skipKeywordMatch(self):
        return self._currentRule.skipKeywordMatch is not None and self._currentRule.skipKeywordMatch

    def _match_keywords(self, keywords, title, url, feedEntry=None):
        """
        return tuple(matched, keywords to show)
        matched - True if input keywords is empty, or if any of the input keywords matches either the title or the url content
        keywords - a set of the keywords matched in either the title or the content of the url
        if feedEntry is not None, match again the feed entry, i.e., no URL retrieval needed
        """
        try :
            if self._skipKeywordMatch() or len(keywords) == 0 :
                return True, []
    
            if feedEntry is not None :
                matched_keywords = feedEntry.matched_keywords(keywords)
                if len(matched_keywords)==0 :
                    return False, []
                else :
                    return True, matched_keywords
            
            kwMatcher = fulltextmatcher.FulltextMatcher()
    
            matchedTitle = kwMatcher.match_text(keywords, title)
            if len(matchedTitle) > 0 : 
                # skip full text search to improve some performance
                logging.debug("_matching keywords '%s', title '%s', url '%s', returned '%s' and '%s'" % (','.join(keywords), title, url, True, ','.join(matchedTitle)))
                return True, matchedTitle  
    
            if url is None:
                matchedContent = []
            else :
                urlText = memcache.get(url)
                if urlText is None :
                    urlText = kwMatcher.getText(url)
                    memcache.set(url, urlText, DEFAULT_URL_TEXT_CACHE_TIME)
                matchedContent = kwMatcher.match_text(keywords, urlText)

            matched = len(matchedContent) > 0 or len(matchedTitle) > 0
            ret_kwds = Set(matchedContent).union(Set(matchedTitle))
    
            logging.debug("_matching keywords '%s', title '%s', url '%s', returned '%s' and '%s'" % (','.join(keywords), title, url, matched, ','.join(ret_kwds)))
            return matched, list(ret_kwds)
        except :
            logging.exception("Encountered unexpected error when matching keywords '%s', title '%s', url '%s'" % (','.join(keywords), title, url))
            return False, []
                
        
    def _resvUrlMappingIds(self) :
        postParent = self._currentRule.parent()
        """ Wondering if this is a separate transaction. If so, we can do get_or_insert() here. """
        shortUrlResv = ShortUrlReserve.get_by_key_name(postParent.key().name(),parent=postParent)
        if shortUrlResv is None:
            shortUrlResv = ShortUrlReserve(key_name=postParent.key().name(),firstCharacter=ShortUrlProcessor.randomFirstCharacter(),parent=postParent)
            shortUrlResv.put()
        self._urlMappingIdBlocks = ShortUrlProcessor.consumeShortUrlReserve(shortUrlResv.id, post_const.LIMIT_POST_PER_RULE)
        
    def _saveRemainingUrlMappingIdReserve(self) :
        postParent = self._currentRule.parent()
        shortUrlResv = ShortUrlReserve.get_by_key_name(postParent.key().name(),parent=postParent)
        unconsumedBlocks = self._urlMappingIdBlocks
        for info in unconsumedBlocks:
            block = info[0]
            for i in range(0,len(shortUrlResv.resvBlock)):
                if i >= len(shortUrlResv.resvBlock):
                    break
                if block < shortUrlResv.resvBlock[i] and block > (shortUrlResv.resvBlock[i]-shortUrlResv.resvBlockSize[i]):
                    logging.error('Short url resv save error,clean error data')
                    logging.error('unconsumedBlock %s'%str(unconsumedBlocks))
                    logging.error('Resvblock %s'%str(shortUrlResv.resvBlock))
                    logging.error('Resvblock size %s'%str(shortUrlResv.resvBlockSize))
                    shortUrlResv.resvBlock.pop(i)
                    shortUrlResv.resvBlockSize.pop(i)
                    shortUrlResv.put()
        self._urlMappingIdBlocks = None
        if unconsumedBlocks is not None and len(unconsumedBlocks) > 0 :
            ShortUrlProcessor.saveShortUrlReserve(shortUrlResv.id, unconsumedBlocks)

    def _put_posts(self, posts, posting):
        """
        On success, set the saved posts and posting to self._posts and self._posting.
        On failure, raise exception.
        """
        parent = self._currentRule.parent()
        putPosts = []
        now = datetime.datetime.utcnow()
        for post in posts :
            urlHash = post.pop('urlHash')
            url = post.pop('url')
            feedEntry=post.pop('feedEntry')
            if feedEntry is not None:
                post['feedId']=feedEntry.id
                if isinstance(feedEntry, deal_util.DealFeedEntry):
                    post['extra'] = feedEntry.deal_location_category
                    if feedEntry.deal_location_category:
                        logging.info("TopDeal: marked a top deal '%s' for a post of campaign '%s' of user %s" % 
                                     (feedEntry.deal_location_category,
                                      self._currentRule.name, 
                                      self._currentRule.parent().keyNameStrip()))
            if url is not None :
                dataPost = SPost.get_by_key_name(SPost.keyName(urlHash), parent)
                if dataPost is not None:
                    logging.error('Post already exist for user %s of rule %s'%(parent.keyNameStrip(),self._currentRule.name))
                    logging.error('The post data %s'%str(dataPost))
                post.update(dict(key_name=SPost.keyName(urlHash),url=url,urlHash=urlHash))
            rule = self._currentRule
            if rule.randomize:
                timeWindow = rule.randomizeTimeWindow - 5
                if timeWindow < 0:
                    timeWindow = 0
                delta = datetime.timedelta(minutes=random.randint(0, timeWindow))
                scheduleNext = now + delta
            else:
                scheduleNext = now
            post.update(dict(parent=parent,type=self.getPostType(),execution=posting,revision=posting.revision,state=camp_const.EXECUTION_STATE_INIT,campaign=rule,scheduleNext=scheduleNext))
            post_obj=SPost(**post)
            putPosts.append(post_obj)
        try :
            db.put(putPosts)
            self._posts = putPosts
            self._posting = posting
        except Exception, e :
            objList = []
            for obj in putPosts :
                objList.append(str(obj.key().name()))
            msg = "%s! The put object list is: %s." % (e.message,  ",".join(objList)) 
            logging.error(msg)
            raise e
        
    def _trans_refresh_turn(self,user,filter_date,limit_number=200):
        pass

    @classmethod
    def _deferred_shuffle_schedule_start(cls):
        context.set_deferred_context(deploy=deploysns)
        cls(timeout=cls.TIMEOUT_BACKEND)._shuffle_schedule_start()
    
    def _shuffle_schedule_start(self):
        updated_count = 0
        total_count = 0
        try:
            model = self.getModel()
            logging.info("Start to shuffle schedule start for all %s campaigns" % model.__name__)
            cursor = None
            limit = 200
            schedule_start_minute = 0
            while True:
                query = model.all().filter('deleted', False).order('nameLower')
                if cursor:
                    query.with_cursor(cursor)
                obj_list = query.fetch(limit=limit)
                total_count += len(obj_list)
                logging.info("Queried %d objs." % total_count)
                for obj in obj_list:
                    if obj.state != camp_const.CAMPAIGN_STATE_ACTIVATED:
                        continue
                    if not obj.scheduleStart:
                        continue
                    td = datetime.timedelta(minutes=obj.scheduleStart.minute, hours=obj.scheduleStart.hour)
                    schedule_start = obj.scheduleStart - td
                    schedule_start_minute = (schedule_start_minute + 1) % 180
                    td = datetime.timedelta(hours=schedule_start_minute/60, minutes=schedule_start_minute%60)
                    obj.scheduleStart = schedule_start + td
                    db.put(obj)
                    updated_count += 1
                cursor = query.cursor()
                if len(obj_list)<limit:
                    break
        except Exception:
            logging.exception("Unexpected error when shuffling schedule start for campaigns:")
        finally:
            msg = "Updated %d objects out of total %d." % (updated_count, total_count)
            logging.info(msg)
            return msg
        
    @classmethod
    def on_cs_blacklist(cls, url, topics=[], channel=None):
        cskey = Domain2CSProcessor().get_cskey_by_url(url, context_sensitive=False)
        return cskey in cont_const.CS_BLACKLIST


class MessageCampaignProcessor(StandardCampaignProcessor):
    def __init__(self, timeout=StandardCampaignProcessor.TIMEOUT_FRONTEND):
        StandardCampaignProcessor.__init__(self, timeout=timeout)

    def getModel(self):
        return MCampaign

    def getSmallModel(self):
        return MessageCampaignSmall

    def getPostType(self):
        return post_const.POST_TYPE_MESSAGE

    def getDefaultScheduleType(self):
        camp_const.SCHEDULE_TYPE_NOW
        
    def campaignQueueName(self):
        return "msgcampaign"
    
    def isAddLimited(self):        
        size = self.query_base().count(1000)
        if size<limit_const.LIMIT_ARTICLERULE_ADD_PER_USER:
            return False
        else:
            return True
   
    def monitorKeyName(self, userHashCode):
        return "msg_campaign_execution_%d" % userHashCode
    
    def _doPost(self,contents,channels):
        """
        Sanity checks are already done. just go to perform the action.
        """
        rule = self._currentRule
        logging.debug("Started posting for campaign: %s" + rule.basic_info())
        p_count = rule.revision%post_const.MAX_POSTING_PER_RULE
        posting = SExecution.get_by_key_name(SExecution.keyName(p_count),parent=rule)
        if posting is None:
            posting = SExecution(key_name=SExecution.keyName(p_count),parent=rule,campaign = rule)
        posting.total = 0
        posting.failure = 0
        posting.revision = rule.revision
        posts = []
        
        for article in contents :
            if db_base.isDeleted(article):
                continue
            if rule.msgPrefix is not None :
                msg = "%s %s" %(rule.msgPrefix, article.msg)
            else :
                msg = article.msg
            matched, matched_rule_kwds = self._match_keywords(rule.keywords, msg, article.url)
            if matched :
                posts += self._doPostUrl(article,channels, posting, msg, article.url, matched_rule_kwds)
            if self.limit_exceeded() :
                break
        posting.put()
        self._put_posts(posts, posting)


class QuickMessageCampaignProcessor(MessageCampaignProcessor):
    def getModel(self):
        return QMCampaign
            
    def getSmallModel(self):
        return DirectMessageCampaignSmall
            

class FeedCampaignProcessor(StandardCampaignProcessor):
    def __init__(self, timeout=StandardCampaignProcessor.TIMEOUT_FRONTEND):
        StandardCampaignProcessor.__init__(self, timeout=timeout)

    def getModel(self):
        return FCampaign

    def getSmallModel(self):
        return FeedCampaignSmall

    def getPostType(self):
        return post_const.POST_TYPE_FEED

    def getDefaultScheduleType(self):
        return camp_const.SCHEDULE_TYPE_RECURRING
    
    def campaignQueueName(self):
        return "feedcampaign"
    
    def monitorKeyName(self, userHashCode):
        return "feed_campaign_execution_%d" % userHashCode
    
    @classmethod
    def getScheduleStartInfo(cls):
        memKey = post_const.SCHEDULE_START_MEM_KEY
        scheduleInfo = memcache.get(memKey)
        if scheduleInfo is None:
            startMap = {}
            offset = 0
            while True:
                rules = FCampaign.all().filter('deleted',False).order('nameLower').fetch(limit=100, offset=offset)
                if len(rules) == 0:
                    break
                for rule in rules:
                    offset += 1
                    if rule.state == camp_const.CAMPAIGN_STATE_ACTIVATED:
                        start = rule.scheduleStart.minute
                        if not startMap.has_key(start):
                            startMap[start] = 1
                        else:
                            startMap[start] = startMap[start] +1
            lastRefreshTime = datetime.datetime.utcnow()
            memcache.set(memKey, (startMap,lastRefreshTime), time=86400)
            logging.info('Current start map %s'%str(startMap))
        else:
            startMap = scheduleInfo[0]
            lastRefreshTime = scheduleInfo[1]
        if lastRefreshTime + datetime.timedelta(days=1) < datetime.datetime.utcnow():
            memcache.delete(memKey)
        return (startMap,lastRefreshTime)
    
    def _doPost(self,contents,channels,feedEntryList,recordList):
        """
        Sanity checks are already done. just go to perform the action.
        """
        rule = self._currentRule
        logging.debug("Do post for feed campaign: %s" % rule.basic_info())
        p_count = rule.revision%post_const.MAX_POSTING_PER_RULE
        posting = SExecution.get_by_key_name(SExecution.keyName(p_count),parent=rule)
        if posting is None:
            posting = SExecution(key_name=SExecution.keyName(p_count),parent=rule,campaign = rule)
        posting.total = 0
        posting.failure = 0
        posting.revision = rule.revision
        posts = []
        msg_prefix = ''
        if rule.msgPrefix is not None :
            msg_prefix = rule.msgPrefix + ' '
        
        for feed,  feed_entries, record in map(None, contents, feedEntryList, recordList) :
            if db_base.isDeleted(feed) :
                continue
            feed_url_count = 0
            if feed_entries is None:
                logging.warn("Encountered none feed entry for campaign: " % rule.basic_info())
                continue
            for entry in feed_entries :
                if not url_util.is_valid_url(entry.url) :
                    continue
                try:
                    msg = msg_prefix + entry.title
                except:
                    msg = "%s%s" % (msg_prefix.decode('utf-8','ignore'), entry.title.decode('utf-8','ignore'))
                matched, matched_rule_kwds = self._match_keywords(rule.keywords, msg, entry.url, entry)
                if matched :
                    feed_url_count += 1
                    msg = rule.truncateMsg(msg)
                    posts += self._doPostUrl(feed,channels, posting, msg, entry.url, matched_rule_kwds, record, entry)
                if feed_url_count>=rule.maxMessagePerFeed or self.limit_exceeded() :
                    break
            if self.limit_exceeded() :
                break
        
        posting.put()
        self._put_posts(posts, posting)
    
    def _doPostNow(self):
        """
        sanity checks are already done. just go to perform the action.
        """
        raise api_error.ApiError(api_error.API_ERROR_UNSUPPORTED_OPERATION, 'post now', self.getModel().__name__)
        
    def _doPostOneTime(self):
        """
        sanity checks are already done. just go to perform the action.
        """
        raise api_error.ApiError(api_error.API_ERROR_UNSUPPORTED_OPERATION, 'post one time', self.getModel().__name__)
        
    def isAddLimited(self):        
        size = self.query_base().count(1000)
        if size<limit_const.LIMIT_FEEDRULE_ADD_PER_USER:
            return False
        else:
            return True
        
    def create(self, params, check_limit=True):
        if check_limit and self.isAddLimited():
            raise api_error.ApiError(api_error.API_ERROR_USER_EXCEED_ADD_LIMIT, UserProcessor().getFeedRuleAddLimit(), 'feed posting rule')        
        return StandardCampaignProcessor.create(self, params)                

    def create_dummy(self, user=None):
        params={'name': 'Dummy Feed Campaign %d' % random.randint(10000, 99999)}
        if user: params['user'] = user
        return self.create(params, check_limit=False)
                    
        
class SExecutionProcessor(AssociateModelBaseProcessor):
    def getModel(self):
        return SExecution


class PostProcessor(BaseProcessor):
    MAX_POSTS_PER_DEFERRED_JOB = 50
    
    def __init__(self, timeout=BaseProcessor.TIMEOUT_FRONTEND):
        BaseProcessor.__init__(self, timeout=timeout)
        self._userStats = None
        
    @classmethod
    def supportedOperations(cls):
        return ImmutableSet([api_const.API_O_CRON_EXECUTE, api_const.API_O_QUERY, api_const.API_O_QUERY_ALL]).union(BaseProcessor.supportedOperations())
    
    def getModel(self):
        return SPost

    def monitorKeyName(self, userHashCode):
        return "post_execution_%d" % userHashCode

    def failedPostQuery(self, uid=None):
        if uid is None:
            uid = db_core.get_user_id()
        return self.query_base().filter('state', camp_const.EXECUTION_STATE_FAILED).filter('uid', uid).order('-modifiedTime')

    def cron_execute(self, params):
        for userHashCode in range(0, User.USER_HASH_SIZE):
            deferred.defer(self.__class__._deferred_execute, userHashCode=userHashCode, queueName='post')
            
    @classmethod
    def _deferred_execute(cls, userHashCode):
        context.set_deferred_context(deploy=deploysns)
        return cls(timeout=BaseProcessor.TIMEOUT_BACKEND).execute(userHashCode)

    def execute(self, userHashCode):
        """
        Query all due active rules and unfinished executing rules at the moment. 
        """
        monitorKeyName = self.monitorKeyName(userHashCode)
        if not SystemStatusMonitor.acquire_lock(monitorKeyName, log=True, preempt=self.__class__.TIMEOUT_BACKEND+self.__class__.TIMEOUT_MARGIN):
            return 0
        count = 0
        try:
            count = self._executeOneUserHashCode(userHashCode)
        except:
            logging.exception("Error when executing posts for user hash %d:" % userHashCode)
        finally:
            SystemStatusMonitor.release_lock(monitorKeyName)
            return count
    
    def _executeOneUserHashCode(self, userHashCode):
        utcnow = datetime.datetime.utcnow()
        query= SPost.all().filter('state =', camp_const.EXECUTION_STATE_INIT).filter('userHashCode',userHashCode).filter('scheduleNext <= ', utcnow).order('scheduleNext')
        count=query.count(1000)
        if count==0 :
            return 0
        posts=query.fetch(limit=self.__class__.MAX_POSTS_PER_DEFERRED_JOB)  
        self.logScheduleDelayStatus(posts[0].scheduleNext)
        user_post={}
        for post in posts:
            user = post.parent().keyNameStrip()
            if not user_post.has_key(user):
                user_post[user]=[post.id]
            else:
                u_posts=user_post[user]
                u_posts.append(post.id)
                user_post[user]=u_posts
        deferredPostCount = 0
        for user in user_post.keys():
            if self.isTimeout():
                break
            posts=user_post[user]
            self._real_post(posts)     
            deferredPostCount += len(posts)
        logging.info("Finished execution for %d posts for %d users." % (deferredPostCount, len(user_post)))
        return deferredPostCount

    def _real_post(self, posts):
        user = "Failed to get user name from db."
        try:
            self._userStats = UserStats()
            parent = db.get(posts[0]).parent()
            user = parent.keyNameStrip()
            modelUser = User.get_by_id(parent.uid)
            self._do_real_post_for_user(posts, modelUser)
            logging.debug("Finished %d real posts for user '%s'." % (len(posts), user))
            UserProcessor().incrementStats(self._userStats, modelUser)
        except :
            logging.exception("Unknown exception when doing %d real posts for user '%s'." %(len(posts), user))
          
    def _do_real_post_for_user(self, posts, modelUser):
        num=len(posts)
        posting_keys={}
        for i in range(0,num):
            if self.isTimeout():
                logging.warning("Stopped real posts on time out for user '%s'!" % (modelUser.uidHashCodeStr(),))
                return
            if i>=10:
                logging.warning("Stopped real posts, after finishing 10 in one job, for user '%s'!" % (modelUser.uidHashCodeStr(),))
                return
            post=db.get(posts[i])
            """ One more sanity check can help reduce potential dups. """
            if post.state!=camp_const.EXECUTION_STATE_INIT:
                logging.warning("Skipped a real post for user '%s'. Post state is '%s', not active." % (modelUser.uidHashCodeStr(), post.state))
                continue
            posting=post.execution
            pid = posting.id
            if not pid in posting_keys.keys():
                posting_keys[pid]=posting
            else:
                posting=posting_keys[pid]
            self._do_one_post(post, posting, modelUser)
        
    def _channel_log_msg(self, description, errorMsg, channel, rule):
        """
        A handy internal function to construct log message.
        """
        account = channel.name if channel else 'None'
        accountType = channel.__class__.getAccountType() if channel else 'None'
        return "%s '%s' when posting to %s account '%s' in campaign '%s'" % (description, errorMsg, accountType, account, rule.basic_info())
    
    def _do_one_post(self, post, posting, modelUser):
        rule = posting.campaign
        if self._userStats is None:
            self._userStats = UserStats()
        newUserStats = self._userStats
        newUserStats.post_count += 1
        errorMsg = None
        post_success = False
        error_record = ''
        error_id = None
        channel = post.get_channel()
        chid = post.chid
        if channel and channel.state == channel_const.CHANNEL_STATE_SUSPENDED:
            channel_error_str = "Channel %s is suspended!" % channel.name
        else:
            channel_error_str = memcache.get(channel.keyNameStrip()) if channel else "deleted channel"
        if channel_error_str is not None:
            posting.failure += 1
            newUserStats.failure_count += 1
            post.state = camp_const.EXECUTION_STATE_FAILED
            errorMsg = self._channel_log_msg("Skipped status update because of", channel_error_str, channel, rule)
            errmsg = errorMsg
        else:
            try:
                if isinstance(channel, TAccount):
                    self._do_one_tweet(post, channel, modelUser)
                elif isinstance(channel, FAccount) or isinstance(channel, FAdminPage):
                    pass
#                    self._do_one_fb_post(post, channel, rule)
                post_success=True
                self._resetChannelErrorCount(channel)
            except Exception, ex:
                logging.exception("Post error! %s" % str(ex))
                errmsg = str(ex)
                error_record = errmsg
                if isinstance(ex, twitter_error.TwitterError) and  twitter_error.isPossiblySuspended(ex):
                    channel.errorCount += 1
                    logging.info("%s is possibly suspended. %s" % (channel.login(), str(ex)))
                    if channel.errorCount >= 1:
                        channel.mark_suspended()
                    channel.put()
                posting.failure += 1
                newUserStats.failure_count += 1
                post.state = camp_const.EXECUTION_STATE_FAILED
                error = Error.getErrorByIdentifier(errmsg.encode('utf-8','ignore'), channel.keyNameStrip())
                error_id = error.getErrorIdentifier()
                retrySeconds = error.getRetrySeconds()
                if retrySeconds is not None:
                    memcache.set(channel.keyNameStrip(), error_id, time=retrySeconds)
                    logging.warning(self._channel_log_msg("Marked in memcache for %s seconds for error" % retrySeconds, str(errmsg), channel, rule))
                    errorMsg = self._channel_log_msg("Encountered error", error_id, channel, rule)
                else :
                    if error_id:
                        errorMsg = self._channel_log_msg("Encountered error", error_id, channel, rule)
                    else:
                        errorMsg = self._channel_log_msg("Encountered error", str(errmsg), channel, rule)
        logging.debug("Made a real post for campaign: %s" % rule.basic_info())
        post.errorMsg=errorMsg
        if post.state == camp_const.EXECUTION_STATE_INIT:
            post.state=camp_const.EXECUTION_STATE_FINISH
        update_objs=[post, posting]
        db_base.txn_put(update_objs)
        if post.extra and post.tweetId:
            try:
                top_deal = TopDeal.get_by_key_name_strip(post.extra)
                if top_deal: 
                    top_deal.update(tweet_id=int(post.tweetId))
                    logging.info("TopDeal: updated tweet id for top deal '%s' for campaign: %s" % (top_deal.keyNameStrip(), rule.basic_info()))
            except:
                logging.exception("TopDeal: failed updating tweet id!")
        logging.debug("DB updated a real post status for campaign: %s" % rule.basic_info())
        if not post_success:
            error = Error.getErrorByIdentifier(errmsg.encode('utf-8','ignore'), chid)
            error_record = error.getErrorInfo()           
        return post_success, error_record

    def _do_one_tweet(self, post, channel, modelUser=None):
        """ Return values:
                Tweet id - if normal
                None - if Twitter API over limit
                Raise exception otherwise
        """
        
#         """ Skip certain percentage of snsanalytics.com tweets """
#         if post.msg.find('http://www.snsanalytics.com/') != -1:
#             if random.randint(1, 1000) > 200:
#                 logging.info("Random selection skipped tweet! %s" % post.msg.encode('utf-8', 'ignore'))
#                 return
#             else:
#                 logging.info("Random selection selected tweet! %s" % post.msg.encode('utf-8', 'ignore'))
              
        tapi = channel.get_twitter_api()
#        origPostId = None
#        if modelUser and modelUser.isContent and not modelUser.is_deal(): 
#            globalUrl = GlobalUrl.get_by_url(post.url) if post.url else None
#            if post.url and not globalUrl:
#                logging.error("GlobalUrl is None for post url of @%s(%d) and user '%s': %s" % (channel.name, channel.chid_int(), modelUser.uidHashCodeStr(), post.content_str()))
#            if globalUrl:
#                if globalUrl.postId:
#                    if globalUrl.postId!=post.id:
#                        origPostId = globalUrl.postId
#                else:
#                    globalUrl.postId = post.id
#                    globalUrl.put()
        rt = False
#        if origPostId:
#            rt = True
#            try:
#                origPost = db.get(origPostId)
#                if origPost.tweetId:
#                    status = tapi.statuses.retweet(id=int(origPost.tweetId))
#                    post.tweetId = str(status["id"])
#                    self._saveRetweetInfo(origPost, post)
#                else:
#                    logging.error("Original post does NOT have tweet id for user '%s'!" % modelUser.uidHashCodeStr())
#                    rt = False
#            except:
#                rt = False
        if not rt:
            globalUrl = GlobalUrl.get_by_url(post.url)
            media = globalUrl.mediaUrl if globalUrl else None
            status = tapi.status_update(status=post.msg, media=media)
            post.tweetId = str(status["id"])
        if post.tweetId:
            return post.tweetId
        else:
            error_msg = "Tweet ID not returned after post. %s %s" % (tapi.user_str(), post.content_str())
            raise api_error.ApiError(api_error.API_ERROR_UNKNOWN, error_msg)

    def _saveRetweetInfo(self, origPost, post):
        try:
            chid = origPost.channel.chid_int()
            tweetId = int(origPost.tweetId)
            rtChid = post.channel.chid_int()
            rtId = int(post.tweetId)
            urlHash = origPost.keyNameStrip()
            retweet = Retweet(chid=chid, tweetId=tweetId, rtChid=rtChid, rtId=rtId, urlHash=urlHash)
            retweet.put()
        except:
            logging.exception("Unexpected error when saving retweet:")

    def _do_one_fb_post(self, post, channel, rule):
        logging.debug('Begin to post to Facebook.')
        graph = GraphAPI(channel.oauthAccessToken)
        message = self._facebook_str_to_display(post.msg)
        attachment={}
        
        if post.type == post_const.POST_TYPE_FEED:
            if rule.fbPostStyle == common_const.FACEBOOK_POST_TYPE_STANDARD :
                attachment = getAttachment(post)
        else:
            if rule.fbPostStyle == common_const.FACEBOOK_POST_TYPE_QUICK:
                for attr in FACEBOOK_POST_ATTRS:
                    if getattr(rule,attr) is not None and getattr(rule,attr)!= '':
                        attachment[FACEBOOK_POST_MAP[attr]] = getattr(rule,attr).encode('utf-8','ignore')
                if attachment.has_key('link'):
                    attachment['link'] = server_url_util.short_url(post.urlHash)
            elif rule.fbPostStyle == common_const.FACEBOOK_POST_TYPE_STANDARD :
                if post.url is not None:
                    attachment = getAttachment(post)
        
        actions =  ''
        if post.url is not None:            
            actions = getFbActions(post.url)
            
        if post.wallId == 'me' or post.wallId == 'admin':
            profile_id = 'me'
        else:
            profile_id = post.wallId
                 
        if rule.fbPostStyle == common_const.FACEBOOK_POST_TYPE_STANDARD:
            if not attachment.has_key('picture'):
                if attachment.has_key('description') and str_util.strip_one_line(attachment['description']) is not None:
                    message = message + '\n' + str_util.strip_one_line(attachment['description'])
                    message = self._facebook_str_to_display(message)
                info = graph.put_object(profile_id, 'feed',message=message,actions=actions)
            else:
                description = attachment.get('description','')
                info = graph.put_object(profile_id, 'feed',message=message,actions=actions,picture=attachment['picture'],link=attachment['link'],name=attachment['name'],description=description)
        else:
            picture = attachment.get('picture','')
            link = attachment.get('link','')
            name = attachment.get('name','')
            description = attachment.get('description','')
            info = graph.put_object(profile_id, 'feed',message=message,actions=actions,picture=picture,link=link,name=name,description=description)
            
        sid = info['id']
        index = sid.find('_')
        tweetId = sid[index+1:]
        post.tweetId=tweetId 
        logging.debug('Post to facebook account %s successfully : %s'%(channel.name,str(info)))

    def _resetChannelErrorCount(self, channel):
        try:
            if channel.errorCount>0:
                channel.errorCount = 0
                channel.put()
        except:
            logging.exception("Unexpected error when resetting error count for channel '%s':" % channel.name)


def normalizeMsg(msg):
    if msg is None:
        msg= 'None'
    return msg[:490]


def getAttachment(post):
    url = post.url
    globalUrl = GlobalUrl.get_by_url(url)
    if globalUrl is None:
        logging.error("GlobalUrl %s doesn't exist!" % url)
        return {}
    attachment={}
    shortUrl = server_url_util.short_url(post.urlHash)
    message = normalizeMsg(post.origMsg).encode('utf-8','ignore')
    attachment['link'] = shortUrl
    attachment['name'] = message
    summary = globalUrl.description
    if summary is None or summary.startswith('<') and summary.endswith('>'):
        attachment['description'] = ''
    else:
        attachment['description'] = summary.strip().encode('utf-8','ignore')
    if globalUrl.mediaUrl is not None:
        picture = globalUrl.mediaUrl
        try:
            picture = picture.encode('utf-8')
        except:
            pass
        attachment['picture']=picture
    if globalUrl.title is not None:
        name = globalUrl.title
        try:
            name = name.encode('utf-8','ignore')
        except:
            pass
        attachment['name'] = name
    if attachment['description'] == '':
        if globalUrl.description is not None :
            description = globalUrl.description
            try:
                description = description.strip().encode('utf-8','ignore')
            except:
                pass
            attachment['description'] = description
    attachment['description'] = normalizeDescription(attachment['description'])
    return attachment

def convertOldApi(attachment):
    params = {}
    if attachment.has_key('name') and attachment['name'] != '':
        params['name']=attachment['name']
    if attachment.has_key('link') and attachment['link'] != '':
        params['href']=attachment['link']
    if attachment.has_key('description') and attachment['description'] != '':
        params['description'] = attachment['description']
    if attachment.has_key('picture') and attachment['picture'] != '':
        media = []
        pic_params = {'type':'image','src':attachment['picture'],'href':attachment['link']}
        media.append(pic_params)
        params['media'] = media
    params = json.dumps(params)
    return params
    
def getFacebookPostToNameAndUrl(post):
    if post.channel.type == channel_const.CHANNEL_TYPE_FACEBOOK_ACCOUNT:
        if post.wallId=='me':
            return post.channel.name,post.channel.profileUrl,''
        else:
            pages=post.channel.pages
            groups=post.channel.groups
            for i in range(0,len(pages)):
                page_info=pages[i].split(':')
                if page_info[1]==post.wallId:
                    return urllib.unquote(page_info[0]),"http://www.facebook.com/pages/snsanalytics/"+post.wallId,'Page'
            for i in range(0,len(groups)):
                group_info=groups[i].split(':')
                if group_info[1]==post.wallId:
                    return urllib.unquote(group_info[0]),"http://www.facebook.com/group.php?gid="+post.wallId,'Group'
    elif post.channel.type == channel_const.CHANNEL_TYPE_FACEBOOK_PAGE:
        return post.channel.name,post.channel.url,'FbPage'
    else:        
        return post.channel.name,"http://www.twitter.com/"+post.channel.name,''

def normalizeDescription(text):
    while text.find('<') !=-1 :
        begin = text.find('<')
        end = text.find('>')
        if end == -1:
            text = text[:begin]
        elif end < begin :
            text = text[end+1:]
        else:
            text = text[:begin] + text[end+1:]
    text = text[:500]
    return text
    
def getFbActions(url):
    action_link = {}
    action_link['name'] = 'Share'
    href = urllib.quote(url,safe='%')
    action_link['link'] = 'http://www.facebook.com/share.php?u='+href+'&ref=nf'
    actions = json.dumps(action_link)
    return actions


def main():
    pass    


if __name__ == "__main__":
    main()
