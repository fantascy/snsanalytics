import datetime
import logging
import random
from sets import ImmutableSet
import threading
import math
import json

from google.appengine.ext import db
from twitter.api import TwitterApi
from twitter import errors as twitter_error

import context, deploysns
from common.utils import string as str_util
from common.utils import datetimeparser
from sns import channels as sns_channel
from sns.serverutils import deferred, memcache
from sns.core import consts as core_const
from sns.core.core import User, ChannelParent
from sns.core import base as db_base
from sns.core.taskdaemonnowait import BackendTaskDaemonNoWait
from sns.core.base import DailyStatsCounterIF
from sns.core.processcache import ProcessCache
from sns.api import consts as api_const
from sns.api import base as api_base
from sns.usr import consts as usr_const
from sns.chan import consts as channel_const
from sns.chan.models import TAccount, TAccountKeyName
from sns.cont.models import Topic, TopicTargets
from sns.cont.topic.api import TopicCacheMgr
from sns.camp import consts as camp_const
from sns.deal import consts as deal_const
from sns.post.models import SPost
from sns.femaster.models import Source
from sns.log import consts as log_const
from sns.log.models import CmpTwitterAcctStats, CmpTwitterAcctStatsCounter, CmpTwitterAcctFollowers, CmpTwitterAcctUniqueFollowerCount, CmpDealTwitterAcctUniqueFollowerCount, \
    NoneCmpTwitterAcctFeStats, TopicStats, ContentSourceDailyStats, BlackList, Agent


#class CmpTwitterAcctCache(object):
#    def __init__(self, chid=None, handle=None, state=None, topicKey=None, token=None):
#        self.chid = chid
#        self.handle = handle
#        self.state = state
#        self.topicKey = topicKey
#        self.token = token
#
#class CmpTwitterAcctCacheMgr(object):
#    def __init__(self):
#        context.get_context(raiseErrorIfNotFound=False).set_login_required(login_required=False)
#
#    CMP_TACCOUNT_ALL_CACHE_KEY = 'cmp_twitter_acct_all_memcache_key'
#    CMP_TACCOUNT_BATCH_CACHE_KEY = 'cmp_twitter_acct_batch_memcache_key'
#    CMP_TOPIC_2_TACCOUNT_CACHE_KEY = 'cmp_topic_2_twitter_acct_memcache_key'
#    CACHE_EXPIRATION = 86400 
#    TOTAL_BATCHES = 10
#
#    def get_random_tapi(self):
#        """ Return a valid TwitterApi object using a randomly selected good CMP Twitter account. """
#        cstats = CmpTwitterAcctStats.all().filter('state', channel_const.CHANNEL_STATE_NORMAL).fetch(limit=1)[0]
#        return TwitterApi(oauth_access_token=cstats.oauthAccessToken) 
#        
#    def acctBatchKey(self, batch):
#        return "%s_%s" % (self.CMP_TACCOUNT_BATCH_CACHE_KEY, batch)
#    
#    def chid2Batch(self, chid):
#        return int(chid) % self.TOTAL_BATCHES
#    
#    def flushAll(self):
#        memcache.delete(self.CMP_TACCOUNT_ALL_CACHE_KEY)
#        memcache.delete(self.CMP_TOPIC_2_TACCOUNT_CACHE_KEY)
#        for batch in range(0, self.TOTAL_BATCHES):
#            memcache.delete(self.acctBatchKey(batch))
#    
#    def buildCmpTwitterAcctCache(self):
#        self.flushAll()
#        completeCmpTwitterAcctList = []
#        cmpTwitterAcctBatchMap = {}
#        topic2ChannelsMap = {}
#        query = TAccount.all().filter('deleted', False).filter('isContent', True)
#        limit = 500
#        cursor = None
#        while True:
#            if cursor:
#                query.with_cursor(cursor)
#            channels = query.fetch(limit=limit)
#            for channel in channels:
#                chid = int(channel.keyNameStrip())
#                batch = self.chid2Batch(chid) 
#                topicKey = None
#                if len(channel.topics)>0:
#                    topicKey = channel.topics[0]
#                cmpTwitterAcctCache = CmpTwitterAcctCache(chid=chid, handle=channel.name, state=channel.state, topicKey=topicKey, token=channel.oauthAccessToken)
#                batchAccts = cmpTwitterAcctBatchMap.get(batch, [])
#                batchAccts.append(cmpTwitterAcctCache)
#                cmpTwitterAcctBatchMap[batch] = batchAccts
#                completeCmpTwitterAcctList.append(chid)
#                if cmpTwitterAcctCache.topicKey and cmpTwitterAcctCache.state==channel_const.CHANNEL_STATE_NORMAL:
#                    topicChannels = topic2ChannelsMap.get(cmpTwitterAcctCache.topicKey, [])
#                    topicChannels.append(cmpTwitterAcctCache.chid)
#                    topic2ChannelsMap[cmpTwitterAcctCache.topicKey] = topicChannels
#            if len(channels)==0:
#                break
#            cursor = query.cursor()
#        memcache.set(self.CMP_TACCOUNT_ALL_CACHE_KEY, completeCmpTwitterAcctList, time=self.CACHE_EXPIRATION)
#        memcache.set(self.CMP_TOPIC_2_TACCOUNT_CACHE_KEY, topic2ChannelsMap, time=self.CACHE_EXPIRATION)
#        for batch, batchAcctLists in cmpTwitterAcctBatchMap.items():
#            memcache.set(self.acctBatchKey(batch), batchAcctLists, time=self.CACHE_EXPIRATION)
#        
#    def getAllCacheObjects(self, refresh=True):
#        """ All cache objects are assembled to a tuple of two: (completeAcctMap, completeTopic2ChannelsMap). """
#        completeTopic2ChannelsMap = memcache.get(self.CMP_TOPIC_2_TACCOUNT_CACHE_KEY)
#        completeAcctList = memcache.get(self.CMP_TACCOUNT_ALL_CACHE_KEY)
#        batchCacheMap = {}
#        count = 0
#        for batch in range(0, self.TOTAL_BATCHES):
#            batchCache = memcache.get(self.acctBatchKey(batch))
#            if batchCache:
#                batchCacheMap[batch] = batchCache
#                count += len(batchCache)
#        if completeTopic2ChannelsMap is None or completeAcctList is None or len(completeAcctList)!=count:
#            if refresh:
#                self.buildCmpTwitterAcctCache()
#                return self.getAllCacheObjects(refresh=False)
#            else:
#                completeAcctLength = 0 if completeAcctList is None else len(completeAcctList)
#                logging.critical("CMP Twitter account cache is in bad state! Complete acct length is %d while total count from %d batches is %d." % (completeAcctLength, len(batchCacheMap), count))
#                return ({}, {})
#        allAcctCache = []
#        for batchCache in batchCacheMap.values():
#            allAcctCache.extend(batchCache)
#        completeAcctMap = {}
#        for acctCache in allAcctCache:
#            completeAcctMap[acctCache.chid] = acctCache
#        logging.info("CMP Twitter account cache: total %d accounts and %d topics." % (len(completeAcctMap), len(completeTopic2ChannelsMap)))
#        return completeAcctMap, completeTopic2ChannelsMap
    

class AllCmpTwitterAcctsCache(ProcessCache):
    KEY_NAME = 'pck_cstats_all'


class NormalCmpTwitterAcctsCache(ProcessCache):
    """ All normal state channels. Ranked by followers from high to low. """
    KEY_NAME = 'pck_cstats_normal'


class CmpTwitterAcctCacheMgr:
    _cv = threading.Condition()

    @classmethod
    def is_cache_valid(cls):
        return AllCmpTwitterAcctsCache.is_cache_valid()
    
    @classmethod
    def rebuild_if_cache_not_valid(cls):
        if not cls.is_cache_valid():
            cls.build_all_cache()

    @classmethod
    def flush(cls):
        AllCmpTwitterAcctsCache.flush()
        NormalCmpTwitterAcctsCache.flush()

    @classmethod
    def build_all_cache(cls, force=False):
        if not context.is_backend():
            raise Exception("Only backend server can build topic cache!")
        with cls._cv:
            if cls.is_cache_valid() and not force:
                return True  
            cls.flush()
            startTime = datetime.datetime.utcnow()
            logging.info("CmpTwitterAcctStats cache: started re-building.")
            cstats_list = CmpTwitterAcctStatsProcessor().execute_query_all()
            cstats_map = {}
            normal_cstats_list = []
            for cstats in cstats_list:
                chid = cstats.chid
                if cstats.chanState == channel_const.CHANNEL_STATE_NORMAL:
                    normal_cstats_list.append(cstats)
                cstats_map[chid] = cstats 
            normal_cstats_list.sort(cmp=lambda x, y: cmp(x.latelyFollower, y.latelyFollower), reverse=True)
            AllCmpTwitterAcctsCache.set(cstats_map)
            NormalCmpTwitterAcctsCache.set(normal_cstats_list)
            endTime = datetime.datetime.utcnow() 
            logging.info("CmpTwitterAcctStats cache: finished re-building in %s." % str(endTime-startTime))
            return True

    @classmethod
    def get_or_build_all_cstats_map(cls):
        cls.rebuild_if_cache_not_valid()
        return AllCmpTwitterAcctsCache.get(fallback={})

    @classmethod
    def get_or_build_all_cstats_list(cls):
        return cls.get_or_build_all_cstats_map().values()

    @classmethod
    def has_channel(cls, chid):
        cstats_map = cls.get_or_build_all_cstats_map()
        return cstats_map.has_key(chid)
    
    @classmethod
    def get_or_build_normal_cstats_list(cls):
        cls.rebuild_if_cache_not_valid()
        return NormalCmpTwitterAcctsCache.get(fallback=[])

    @classmethod
    def get_or_build_normal_cstats_map(cls):
        cstats_list = cls.get_or_build_normal_cstats_list()
        return dict([(cstats.chid, cstats) for cstats in cstats_list])

    @classmethod
    def get_random_normal_cstats(cls):
        """ Return a valid TwitterApi object using a randomly selected good CMP Twitter account. """
        cstats_list = cls.get_or_build_normal_cstats_list()
        size = len(cstats_list)
        return cstats_list[random.randint(size/5, size-1)]

    @classmethod
    def get_random_tapi(cls):
        cstats = cls.get_random_normal_cstats()
        return TwitterApi(oauth_access_token=cstats.oauthAccessToken) 
        

class CmpTwitterAcctStatsProcessor(api_base.BaseProcessor):
    def __init__(self):
        context.get_context(raiseErrorIfNotFound=False).set_login_required(login_required=False)
        api_base.BaseProcessor.__init__(self, timeout=api_base.BaseProcessor.TIMEOUT_BACKEND)

    def getModel(self):
        return CmpTwitterAcctStats
    
    @classmethod
    def supportedOperations(cls):
        """"
        Supported public API operations of this processor
        """
        return ImmutableSet([api_const.API_O_EXECUTE, api_const.API_O_CRON_EXECUTE, api_const.API_O_CLEAN,]).union(api_base.BaseProcessor.supportedOperations())

    def create(self, params):
        paramsCopy = params.copy()
        return api_base.BaseProcessor.create(self, paramsCopy)
    
    def query_base(self, **kwargs):
        return self.getModel().all()

    def query(self, params):
        includeCounter = params.pop('include_counter', False) 
        results = api_base.BaseProcessor.query(self, params)
        if includeCounter:
            return [(result, result.get_or_insert_counter()) for result in results]
        else:
            return results
    
    def get_all_stats_and_counters(self, params={'chanState': 0}):
        all_stats = self.execute_query_all(params)
        all_counters = [stats.get_or_insert_counter() for stats in all_stats] 
        return all_stats, all_counters
        
    def get_all_channel_stats_counters(self):
        return CmpTwitterAcctStatsCounterProcessor().execute_query_all(params={})
        
    @classmethod
    def deferred_update_follow_stats(cls, infos):
        context.set_deferred_context(deploy=deploysns)
        cls().updateFollowStats(infos)
        
    def updateFollowStats(self, infos):
        updatedCount = 0
        failureCount = 0
        for info in infos:
            try:
                chid = info.get('chid', '')
                state = int(info.get('state', core_const.FOLLOW_RULE_STATE_INIT))
                server = info.get('server', '')
                feCampaignId = info.get('rid', '')
                feCampaign = str_util.decode_utf8_if_ok(info.get('rule', ''))
                feUserEmail = str_util.decode_utf8_if_ok(info.get('userEmail', ''))
                feModifiedTime = info.get('ruleModified', '')
                logging.info("server=%s, channel=%s, state=%s, campaign='%s(%s)', user='%s', modifiedTime='%s'" % (server, chid, state, feCampaign, feCampaignId, feUserEmail, feModifiedTime))
                if state==core_const.FOLLOW_RULE_STATE_EXECUTING:
                    logging.error("Follow campaign is in wrong 'Executing' state. Please fix!")
                feModifiedTime = datetimeparser.parseDateTime(feModifiedTime)
                stats = CmpTwitterAcctStats.get_by_chid(chid)
                if stats is None:
                    logging.info("Twitter account %s doesn't have stats!" % chid)
                    nonCmpFe = NoneCmpTwitterAcctFeStats(key_name=chid, 
                                                                server = server,
                                                                state = state,
                                                                feCampaign = feCampaign,
                                                                feUserEmail = feUserEmail,
                                                                feModifiedTime = feModifiedTime,
                                                                )
                    db.put(nonCmpFe)
                    continue
                if stats.feModifiedTime is not None and feModifiedTime < stats.feModifiedTime:
                    continue
                stats.feModifiedTime = feModifiedTime
                stats.feUserEmail = feUserEmail
                try:
                    stats.feCampaignId = int(feCampaignId)
                except:
                    pass
                stats.feCampaign = feCampaign
                stats.server = server
                stats.state = core_const.FOLLOW_RULE_TO_STATS_MAP[state]
                stats.syncFeStateError()
                stats.put()
                updatedCount += 1
            except:
                failureCount += 1
                logging.exception("Error updating follow engine status for Twitter account:")
        total = len(infos)
        skipped = total - updatedCount - failureCount
        logging.info("Finished a follow engine status update request: total %d, updated %d, failed %d, skipped %d." % (total, updatedCount, failureCount, skipped))
        return updatedCount

    def cron_execute(self, params):
        op = params.get('op', None)
        if op:
            if op=='count_unique_followers':
                deferred.defer(self.__class__._deferred_count_unique_followers)
            elif op=='sync_channel_statuses':
                deferred.defer(CmpTwitterAcctStatusSyncer.deferred_execute, params)
            elif op=='refresh_followers':
                deferred.defer(self.__class__._deferred_refresh_followers)
            elif op=='refresh_count_unique_followers':
                deferred.defer(self.__class__._deferred_refresh_count_unique_followers)
            elif op=='refresh_search_rank':
                deferred.defer(self.__class__.deferred_refresh_search_rank)
            elif op=='init_follow':
                deferred.defer(self.__class__.deferred_init_follow)
            elif op=='follow_friday':
                deferred.defer(self.__class__._deferred_follow_friday)
            elif op=='clean':
                deferred.defer(self.__class__._deferred_clean)
        return

    def execute_admin(self, params):
        op = params.get('op', None)
        if op:
            if op == 'dup_and_deleted_cmp_channels':
                delete_deleted = True if params.get('delete_deleted', None) else False
                delete_dup = True if params.get('delete_dup', None) else False
                deferred.defer(self.__class__.deferred_dup_and_deleted_cmp_channels, delete_deleted, delete_dup)
            elif op == 'clean_suspended_channels':
                deferred.defer(self.__class__.deferred_clean_suspended_channels)
            elif op == 'clean_channel':
                return self.clean_channel(params)
            elif op == 'delete_deal_channels':
                deferred.defer(self.__class__.deferred_delete_deal_channels)
            elif op == 'recreate_channels':
                deferred.defer(self.__class__.deferred_recreate_channels)
            elif op == 'fix_oauth_tokens':
                deferred.defer(self.__class__._deferred_fix_oauth_tokens)
            elif op == 'refresh_search_rank':
                chid = int(params.get('chid'))
                cstats = CmpTwitterAcctStats.get_by_chid(chid)
                search_results = params.get('search_results')
                search_results = json.loads(search_results) if search_results else []
                rank = self.refresh_search_rank_for_one(cstats, search_results)
                logging.info("Rank of %s is %s" % (cstats.chid_handle_str(), rank))
                return rank
            elif op == 'once_suspended_channel_list':
                from sns.log.globalstatsapi import GlobalStatsProcessor
                return list(GlobalStatsProcessor().get_once_suspended_chids())
            elif op == 'user_id_to_handle':
                user_id = int(params.get('user_id'))
                return CmpTwitterAcctCacheMgr.get_random_tapi().get_handle_by_user_id(user_id)
            elif op == 'remove_posts_for_domain':
                domain = params.get('domain', None)
                days = int(params.get('days', 5))
                cursor = params.get('cursor', None)
                if not domain:
                    return "Please specify a domain!"                
                deferred.defer(self.__class__.deferred_remove_posts_for_domain, domain, days, cursor)
            else:
                return "Invalid op - %s!" % op
            return "Submitted op - %s." % op
        return api_base.BaseProcessor.execute_admin(self, params)

    @classmethod
    def _deferred_fix_oauth_tokens(cls):
        context.set_deferred_context(deploy=deploysns)
        processor = cls()
        objs = processor.execute_query_all(params={})
        update_list = []
        for obj in objs:
            if obj.oauthToken:
                obj.oauthAccessToken = obj.oauthToken
                update_list.append(obj)
        db_base.put(update_list)
        logging.info("Migrated oauth tokens for %d out of %d channels." % (len(update_list), len(objs)))
        
    @classmethod
    def deferred_remove_posts_for_domain(cls, domain, days, cursor=None):
        context.set_deferred_context(deploy=deploysns)
        cutoff_time = datetime.datetime.utcnow() - datetime.timedelta(days=days)
        total = 0
        deleted = 0
        errors = 0
        suspended = 0
        query = SPost.all().order('-modifiedTime')
        while True:
            if cursor:
                query.with_cursor(cursor)
            objs = query.fetch(limit=500)
            for obj in objs:
                if obj.domain() == domain and obj.tweetId:
                    try:
                        channel = obj.get_channel()
                        if not channel:
                            continue
                        if channel.state == channel_const.CHANNEL_STATE_NORMAL:
                            tapi = channel.get_twitter_api()
                            tapi.statuses.destroy(id=int(obj.tweetId))
                        else:
                            suspended += 1
                        db.delete(obj)
                        deleted += 1
                    except:
                        logging.exception("Error removing posts and tweets!")
                        errors += 1
            total += len(objs)
            cursor = query.cursor()
            logging.info("Deleted %d posts with %d errors out of total %d (%d suspended) for domain %s for last %d days." % (deleted, errors, total, suspended, domain, days))
            if not objs or objs[-1].modifiedTime < cutoff_time:
                break
        logging.info("cursor=%s" % cursor)
        logging.info("Finished removing posts for domain %s for %d days." % (domain, days))
        
    def getStats(self, channel, uid):
        try:
            chid = channel.keyNameStrip()
            name = str_util.strip(channel.name)
            if name is None:
                name = 'Unknown'
            stats = CmpTwitterAcctStats.get_by_chid(chid)
            if name.lower() in log_const.KNOWN_NON_CMP_TWITTER_ACCOUNTS and context.get_context().is_primary_app():
                if stats:
                    db.delete(stats)
                return None
            toInit = False
            if stats is None:
                toInit = True
                stats = CmpTwitterAcctStats.get_or_insert_by_channel(channel)
                stats.get_or_insert_counter()
            updated = False
            if toInit:
                if stats.chanState==channel_const.CHANNEL_STATE_SUSPENDED:
                    stats.state = core_const.FOLLOW_STATS_SUSPENDED
                else:
                    stats.state = core_const.FOLLOW_STATS_INACTIVATED
                stats.reset()
                updated = True
            if stats.oauthAccessToken is None:
                stats.oauthAccessToken = channel.oauthAccessToken
                updated = True
            if stats.chanState is None or stats.chanState!=channel.state:
                if channel.state is None:
                    stats.chanState = channel_const.CHANNEL_STATE_NORMAL
                else:
                    stats.chanState = channel.state
                logging.info("getStats() set chanState to %s while channel.state=%s." % (stats.chanState, channel.state))
                updated = True
            if updated:
                stats.put()
            if stats and stats.chanState == channel_const.CHANNEL_STATE_NORMAL:
                Source.get_or_insert_by_cstats(stats)
            return stats
        except:
            logging.exception("Error when getting stats for @%s(%d) of user %d:" % (channel.name, channel.chid_int(), uid))

    @classmethod
    def deferred_recreate_channels(cls):
        from sns.mgmt.models import ContentCampaign
        cmp_users = User.all().filter('isContent', True).fetch(limit=1000)
        uid_user_map = dict([(user.uid, user) for user in cmp_users])
        cmp_camps = ContentCampaign.all().filter('deleted', False).fetch(limit=1000)
        cmp_camp_googlenews = None
        tag_cmp_camp_map = {}
        for cmp_camp in cmp_camps:
            first_included_tag = cmp_camp.first_included_tag()
            if not first_included_tag:
                cmp_camp_googlenews = cmp_camp
            elif first_included_tag not in usr_const.CMP_TAGS:
                logging.error("CMP Campaign unexpected! %s " % cmp_camp.name)
                return
            else:
                tag_cmp_camp_map[first_included_tag] = cmp_camp
        uid_cmp_camp_map = {}
        for user in cmp_users:
            uid = user.uid
            user_tag = user.tags[0] if user.tags else None
            user_tag = str_util.strip(user_tag)
            if not user_tag and not tag_cmp_camp_map.has_key(user_tag):
                logging.debug("User %d has obsolete tag %s!" % (uid, user_tag))
            uid_cmp_camp_map[uid] = tag_cmp_camp_map.get(user_tag, cmp_camp_googlenews)
        good_count = 0
        for chid in sns_channel.COMPLETE_PROD_CHANNEL_SET:
            cstats = CmpTwitterAcctStats.get_by_chid(chid)
            if not cstats:
                logging.error("Channel %d doesn't have stats!" % chid)
                continue
            if not cstats.oauthAccessToken:
                logging.error("Channel %s doesn't have oauth token!" % cstats.chid_handle_str())
                continue
            if not cstats.uid:
                logging.error("Channel %s doesn't have SNS user ID!" % cstats.chid_handle_str())
                continue
            topic_key = cstats.first_topic_key()
            topics = [topic_key] if topic_key else None
            if not topics:
                logging.warn("Channel %s doesn't have a topic!" % cstats.chid_handle_str())
            user = uid_user_map.get(cstats.uid)
            if not user:
                logging.error("Channel %s doesn't have right user!" % cstats.chid_handle_str())
                continue
            good_count += 1
        error_count = len(sns_channel.COMPLETE_PROD_CHANNEL_SET) - good_count
        if error_count > 0:
            logging.error("Found %d errors. Skip recreating channels." % error_count)
            return
        from sns.cont.api import FeedProcessor
        from sns.post.api import FeedCampaignProcessor
        recreated_count = 0
        error_count = 0
        for chid in sns_channel.COMPLETE_PROD_CHANNEL_SET:
            if error_count > 20:
                break
            try:
                cstats = CmpTwitterAcctStats.get_by_chid(chid)
                topic_key = cstats.first_topic_key()
                topics = [topic_key] if topic_key else None
                user = uid_user_map.get(cstats.uid)
                feed = FeedProcessor().create_dummy(user=user)
                feed_camp = FeedCampaignProcessor().create_dummy(user=user)
                feed_camp.contents = [feed.key()]
                feed_camp.put()
                cmp_camp = uid_cmp_camp_map.get(cstats.uid)
                channel_key_name = TAccountKeyName.keyName(str(chid))
                channel_parent = ChannelParent.get_or_insert_parent(uid=cstats.uid)
                channel_info = dict(isContent = True,
                                    chid = str(chid),
                                    userEmail = cstats.userEmail,
                                    state = cstats.chanState, 
                                    name=cstats.name,
                                    nameLower=cstats.nameLower, 
                                    oauthAccessToken=cstats.oauthAccessToken,
                                    topics = topics,
                                    cmpFeedCampaign = feed_camp,
                                    contentCampaign = cmp_camp,
                                    )
                channel = TAccount.get_or_insert(channel_key_name, parent=channel_parent, **channel_info)
                if not channel:
                    logging.error("Error creating channel %s!" % cstats.chid_handle_str())
                    error_count += 1
                else:
                    logging.info("Recreated channel %s." % cstats.chid_handle_str())
                    recreated_count += 1
            except:
                error_count += 1
                logging.exception("Error recreating channel %d!" % chid)
        logging.info("Finished recreating %d channels, running into %d errors." % (recreated_count, error_count))

    @classmethod
    def deferred_delete_deal_channels(cls):
        context.set_deferred_context(deploy=deploysns)
        deal_channels = cls.get_deal_channels()
        logging.info("Deleting %d deal channels..." % len(deal_channels))
        for channel in deal_channels:
            chid = int(channel.keyNameStrip())
            cstats = CmpTwitterAcctStats.get_by_chid(chid)
            if cstats:
                db.delete([cstats.get_or_insert_counter(), cstats])
            if not channel.deleted:
                channel.deleted = True
                db.put(channel)
        logging.info("Deleted %d deal channels and corresponding stats." % len(deal_channels))
                
    @classmethod    
    def get_deal_channels(cls):
        deals = cls.get_loc_deal_channels()
        deals.extend(cls.get_loc_catdeal_channels())
        return deals

    @classmethod    
    def get_loc_catdeal_channels(cls):
        lcd_users = User.all().filter('tags', 'catdeals').fetch(limit=1000) 
        lcd_channels = []
        for user in lcd_users:
            lcd_channels.extend(TAccount.get_user_channels(user))
        return lcd_channels    
            
    @classmethod    
    def get_loc_deal_channels(cls):
        ld_users = User.all().filter('tags', 'deals').fetch(limit=1000)
        ld_channels = [] 
        for user in ld_users:
            ld_channels.extend(TAccount.get_user_channels(user))
        return ld_channels    
            
    @classmethod    
    def deal_channel_map(cls):
        lcd_channels = cls.get_loc_catdeal_channels()
        dc_map = {}
        for channel in lcd_channels:
            if len(channel.topics) == 2:
                dc_map[int(channel.chid)] = (channel.topics[0], channel.topics[1])
        ld_channels = cls.get_loc_deal_channels()
        for channel in ld_channels:
            if len(channel.topics) == 1:
                dc_map[int(channel.chid)] = (channel.topics[0], deal_const.CATEGORY_KEY_GENERAL)
        return dc_map

    @classmethod
    def _deferred_refresh_count_unique_followers(cls):
        context.set_deferred_context(deploy=deploysns)
        cls().refreshCountUniqueFollowers()
        
    def refreshCountUniqueFollowers(self, params={}):
        self.refreshFollowers()
        self.countUniqueFollowers()

    @classmethod
    def _deferred_count_unique_followers(cls):
        context.set_deferred_context(deploy=deploysns)
        cls().countUniqueFollowers()
        
    def countUniqueFollowers(self, params={}):
        cursor = params.get('cursor', None)
        count = params.get('count', 0)
        updatedCount = 0
        uniqueFollowers = set([])
        totalFollowerCount = 0
        deal_acct_updated_count = 0
        deal_acct_count = 0
        deal_unique_followers = set([])
        deal_total_follower_count = 0
        try:
            logging.info("Start to count unique followers for all active CMP Twitter accounts...")
            deal_chids = set(self.deal_channel_map().keys()) 
            limit = 100
            while True:
                query = CmpTwitterAcctStats.all().filter('chanState', channel_const.CHANNEL_STATE_NORMAL)
                if cursor:
                    query.with_cursor(cursor)
                statsList = query.fetch(limit=limit)
                count += len(statsList)
                logging.info("Queried %d stats." % count)
                for stats in statsList:
                    chid = stats.key().name()
                    if int(chid) in deal_chids:
                        deal_acct_count += 1 
                    followerStore = CmpTwitterAcctFollowers.get_by_key_name(chid)
                    if followerStore is None:
                        logging.error("CMP Twitter acct %s doesn't have follower list stored." % stats.chid_handle_str())
                        continue
                    followers = followerStore.getFollowers()
                    uniqueFollowers.update(followers)
                    totalFollowerCount += len(followers)
                    updatedCount += 1
                    if int(chid) in deal_chids:
                        deal_unique_followers.update(followers)
                        deal_total_follower_count += len(followers)
                        deal_acct_updated_count += 1
                logging.info("Current unique followers count is %d out of total %d followers, after counting %d accounts out of total %d accounts queried." % (len(uniqueFollowers), totalFollowerCount, updatedCount, count))
                cursor = query.cursor()
                logging.info("Query cursor: %s" % cursor)
                if len(statsList)<limit:
                    break
            countStore = CmpTwitterAcctUniqueFollowerCount(uniqueCount=len(uniqueFollowers), totalCount=totalFollowerCount, accountCounted=updatedCount, accountTotal=count)
            countStore.put()
            deal_count_store = CmpDealTwitterAcctUniqueFollowerCount(uniqueCount=len(deal_unique_followers), totalCount=deal_total_follower_count, accountCounted=deal_acct_updated_count, accountTotal=deal_acct_count)
            deal_count_store.put()
            return updatedCount, deal_acct_updated_count
        except Exception:
            logging.exception("Unexpected error when counting unique followers:")
            return -1
        finally:
            logging.info("Final unique followers count is %d out of total %d followers, after counting %d accounts out of total %d accounts queried." % (len(uniqueFollowers), totalFollowerCount, updatedCount, count))

    @classmethod
    def _deferred_refresh_followers(cls):
        context.set_deferred_context(deploy=deploysns)
        cls().refreshFollowers()
        
    def refreshFollowers(self, params={}):
        cursor = params.get('cursor', None)
        count = params.get('count', 0)
        updatedCount = 0
        try:
            logging.info("Start refreshing follower list for all CMP Twitter accounts...")
            limit = 100
            while True:
                query = CmpTwitterAcctStats.all().filter('chanState', channel_const.CHANNEL_STATE_NORMAL)
                if cursor:
                    query.with_cursor(cursor)
                statsList = query.fetch(limit=limit)
                count += len(statsList)
                logging.info("Queried %d stats." % count)
                if len(statsList)>0:
                    updatedCount += len(statsList)
                    self.refreshFollowersForBatch(statsList)
                cursor = query.cursor()
                logging.info("Query cursor: %s" % cursor)
                if len(statsList)<limit:
                    break
            return updatedCount
        except Exception:
            logging.exception("Unexpected error:")
            return -1
        finally:
            logging.info("Finished refreshing follower list for %d good accounts out of total %d stats." % (updatedCount, count))

    def refreshFollowersForBatch(self, batch):
        logging.info("Start refreshing follower list for a batch of %d Twitter accounts." % (len(batch), ))
        for stats in batch:
            chid = stats.key().name()
            try:
                if stats.oauthAccessToken is None:
                    logging.error("CmpTwitterAcctStats object %s doesn't have oauth access token yet." % chid)
                    continue
                tapi = TwitterApi(oauth_access_token=stats.oauthAccessToken)
                followers = []
                cursor = -1
                retry = 0
                succeeded = False
                while cursor!=0 and retry<3:
                    try:
                        resp = tapi.followers.ids(user_id=chid, cursor=cursor)
                        cursor = resp['next_cursor']
                        followers += resp['ids']
                        if cursor==0:
                            succeeded = True
                    except Exception, ex:
                        logging.exception("Unexpected Twitter API error when refreshing follower list for Twitter account %s for %d times:" % (stats.chid_handle_str(), retry))
                        if twitter_error.isPossiblySuspended(ex) or twitter_error.isRateLimitExceeded(ex):
                            break
                        retry += 1
                if succeeded:
                    followerStore = CmpTwitterAcctFollowers.get_or_insert(key_name=chid)
                    followerStore.setFollowers(followers)
                    followerStore.put()
            except:
                logging.exception("Unexpected error when refreshing follower list for Twitter account %s!" % (stats.chid_handle_str(), ))
        logging.info("Finished refreshing follower list for a batch of %d Twitter accounts." % (len(batch), ))

    @classmethod
    def _deferred_clean(cls):
        context.set_deferred_context(deploy=deploysns)
        cls().clean()
        
    @classmethod
    def sns_normal_stats_count(cls):
        return CmpTwitterAcctStats.all().filter('chanState', channel_const.CHANNEL_STATE_NORMAL).count(limit=10000)
        
    @classmethod
    def sns_suspended_stats_count(cls):
        return CmpTwitterAcctStats.all().filter('chanState', channel_const.CHANNEL_STATE_SUSPENDED).count(limit=10000)
        
    @classmethod
    def deferred_refresh_search_rank(cls):
        context.set_deferred_context(deploy=deploysns)
        cls().refresh_search_rank()
        
    def refresh_search_rank(self):
        count = 0
        rankedCount = 0
        try:
            statsList = CmpTwitterAcctStats.all().filter('chanState', channel_const.CHANNEL_STATE_NORMAL).order('searchRankModifiedTime').fetch(limit=50)
            for cstats in statsList:
                if cstats.searchTerm is None or cstats.state==channel_const.CHANNEL_STATE_SUSPENDED:
                    results = []
                else:
                    tapi = TwitterApi(oauth_access_token=cstats.oauthAccessToken)
                    try:
                        results = tapi.users.search(q=cstats.searchTerm)
                    except Exception, tex:
                        logging.exception("Refresh Search Rank Twitter API error:")
                        if twitter_error.isTemporaryError(tex):
                            continue
                        else:
                            results = None
                rank = self.refresh_search_rank_for_one(cstats, results)
                if rank:
                    rankedCount += 1
                count += 1
        except:
            logging.exception("Refresh Search Rank error:")
        finally:
            logging.info("%d out of %d accounts appear on the first page of search results." % (rankedCount, count))

    def refresh_search_rank_for_one(self, cstats, results):
        if not results: results = []
        chid = cstats.chid
        rank = None
        for i in range(0, len(results)):
            result = results[i]
            screen_name = result.get('screen_name', None)
            if cstats.nameLower==str_util.lower_strip(screen_name):
                rank = i + 1
                break
        topic_name = cstats.first_topic_name()
        self._refresh_topic_targets(topic_name, results)
        if rank is None and cstats.searchRank is not None:
            logging.info("Refresh Search Rank: Twitter acct %s/%s with topic '%s' disappears from search results. Old rank was %d." % (cstats.name, chid, topic_name, cstats.searchRank))
            cstats.searchRank = None
        elif rank:
            logging.info("Refresh Search Rank: Twitter acct %s/%s with topic '%s' has rank %d." % (cstats.name, chid, topic_name, rank))
            cstats.searchRank = rank
        cstats.searchRankModifiedTime = datetime.datetime.utcnow()
        statsCounter = cstats.get_or_insert_counter()
        statsCounter.setSearchRank(cstats.searchRank, cstats.searchRankModifiedTime)
        logging.debug("Refresh Search Rank: Twitter acct %s/%s rank log: %s." % (cstats.name, chid, statsCounter.searchRanks))
        db_base.txn_put([cstats, statsCounter])
        return rank

    def _refresh_topic_targets(self, topic_name, search_results):
        targets = []
        for result in search_results:
            user_id = result.get('id', None)
            handle = str_util.lower_strip(result.get('screen_name', None))
            score = self._rate_topic_target(result)
            if score: targets.append((user_id, handle, score))
        logging.debug("%s search results: %s" % (topic_name, search_results))
        if not targets: return
        targets.sort(key=lambda x: x[2], reverse=True)
        topic_key = Topic.name_2_key(topic_name)
        logging.debug("%s target handles: %s" % (topic_name, targets))
        TopicTargets.set_targets(topic_key, targets)

    def _rate_topic_target(self, result):
        """ The higher the score the better the target. A 0 score means invalid. """
        user_id = result.get('id', None)
        handle = str_util.lower_strip(result.get('screen_name', None))
        protected = result.get('protected', False)
        followers_count = result.get('followers_count', 0)
        friends_count = result.get('friends_count', 1)
        statuses_count = result.get('statuses_count', 0)
        verified = result.get('verified', False)
        if not user_id or not handle: return 0
        if protected: return 0
        if followers_count < 1000: return 0
        follower_friend_ratio = min(100, followers_count / friends_count) if friends_count else 100
        if follower_friend_ratio <= 5: return 0
        if statuses_count < 50: return 0
        if handle.startswith('_') or handle.endswith('_'): return 0
        if CmpTwitterAcctCacheMgr.has_channel(user_id): return 0
        score = int(math.log(followers_count, 2))
        score *= follower_friend_ratio
        if verified: score *= 10
        return score

    @classmethod
    def deferred_init_follow(cls):
        context.set_deferred_context(deploy=deploysns)
        cls().init_follow()
        
    def init_follow(self):
        FOLLOW_LIMIT = 200
        FOLLOW_MARGIN = 10
        FOLLOW_RATE = 4
        target_list = CmpTwitterAcctStats.all().filter('chanState', channel_const.CHANNEL_STATE_NORMAL).filter('latelyFollower < ', FOLLOW_LIMIT).order('-latelyFollower').fetch(limit=100)
        logging.info("Init follow: Found %d accounts with less than %d followers." % (len(target_list), FOLLOW_LIMIT))
        if len(target_list) == 0:
            return
        target_list = target_list[:FOLLOW_RATE]
        source_query = CmpTwitterAcctStats.all().filter('chanState', channel_const.CHANNEL_STATE_NORMAL).filter('latelyFollower < ', 2500).filter('latelyFollower > ', 300).order('-latelyFollower')
        source_total = source_query.count(limit=100000)
        logging.info("Init follow: total qualified source account is %d." % source_total)
        follow_cursor = 0
        for target in target_list:
            follow_target = FOLLOW_LIMIT + FOLLOW_MARGIN - target.latelyFollower  
            source_fetch_limit = follow_target + 20
            max_offset = source_total - source_fetch_limit
            if max_offset < 0:
                return
            source_fetch_offset = random.randint(0, max_offset)
            source_list = source_query.fetch(limit=source_fetch_limit, offset=source_fetch_offset)
            source_list.sort(lambda x, y: cmp(x.totalClick, y.totalClick), reverse=True)
            logging.info("Init follow: 16th - 25th most clicked source accounts out of total %d at offset %d: %s" % (len(source_list), source_fetch_offset, [(source.totalClick, source.latelyFollower) for source in source_list[15:25]]))
            source_list = source_list[20:]
            follow_count = 0
            failure_count = 0
            target_chid = target.chid
            target_suspended = False
            for source in source_list:
                tapi = TwitterApi(oauth_access_token=source.oauthAccessToken)
                succeeded = False
                try: 
                    tapi.friendships.create(user_id=target_chid)
                    follow_count += 1
                    succeeded = True
                except twitter_error.TwitterError, tex:
                    logging.error("Init follow: following @%s(%d) failed. %s" % (target.name, target.chid, str(tex)))
                    target_suspended = tex.is_following_suspended_target()
                if not succeeded: 
                    failure_count += 1
                    if target_suspended:
                        target.chanState = channel_const.CHANNEL_STATE_SUSPENDED
                    if failure_count > 10 or target_suspended:
                        break
                follow_cursor += 1
            logging.info("Init follow: %d succeeded and %d failed for @%s with %d existing followers." % (follow_count, failure_count, target.name, target.latelyFollower))
            target.latelyFollower += follow_count
            db.put(target)
        logging.info("Init follow: finished initiating %d accounts." % len(target_list))

    @classmethod
    def _deferred_follow_friday(cls):
        context.set_deferred_context(deploy=deploysns)
        cls()._executeFollowFriday()
        
    def _executeFollowFriday(self):
        completeCmpTwitterAcctMap, topic2ChannelsMap = CmpTwitterAcctCacheMgr().getAllCacheObjects()
        preorderTopicList = TopicCacheMgr.get_all_topic_keys_parent1_preorder()
        if completeCmpTwitterAcctMap is None or topic2ChannelsMap is None or preorderTopicList is None:
            errorMsg = "CMP Twitter account cache error!"
            logging.critical(errorMsg)
            return errorMsg
        topicMap = TopicCacheMgr.get_or_build_all_topic_map()
        topicOrderMap = {}
        for i in range(0, len(preorderTopicList)):
            topicOrderMap[preorderTopicList[i]] = i
        ffTweetCount = 0
        for cmpTwitterAcctCache in completeCmpTwitterAcctMap.values():
            handle = cmpTwitterAcctCache.handle
            oauthAccessToken = cmpTwitterAcctCache.token
            topicKey = cmpTwitterAcctCache.topicKey
            if cmpTwitterAcctCache.state==channel_const.CHANNEL_STATE_SUSPENDED or topicKey is None:
                continue
            topic = topicMap.get(topicKey)
            ffTopicKeyCandidates = topic.parentTopics
            ffTopicKeyCandidates.append(topicKey)
            finalTopicCandidates = []
            for candidate in ffTopicKeyCandidates:
                topic = topicMap[candidate]
                if topic.treeSizeP1>=5:
                    finalTopicCandidates.append(topic)
            if len(finalTopicCandidates)==0:
                logging.error("#FF doesn't find right topic for handle '%s'." % handle)
                continue 
            ffTopic = finalTopicCandidates[random.randint(0, len(finalTopicCandidates)-1)]
            ffTopicOrder = topicOrderMap.get(ffTopic.keyNameStrip())  
            sampleSize = 7 if ffTopic.treeSizeP1>=7 else ffTopic.treeSizeP1
            ffTwitterAcctTopics = random.sample(preorderTopicList[ffTopicOrder:ffTopicOrder+ffTopic.treeSizeP1], sampleSize)
            ffHandles = []
            for topic in ffTwitterAcctTopics:
                chids = topic2ChannelsMap.get(topic, [])
                for chid in chids:
                    cache = completeCmpTwitterAcctMap[chid]
                    ffHandles.append(cache.handle)
            ffHandles = list(set(ffHandles))
            if ffHandles.count(handle)>0:
                ffHandles.remove(handle)
            ffHandles = ffHandles[:7]
            if len(ffHandles)==0:
                continue
            ffTweet = self._followFridayTweet(Topic.canonical_name(ffTopic.name), ffHandles) 
            tapi = TwitterApi(oauth_access_token=oauthAccessToken)
            try:
                tapi.statuses.update(status=ffTweet)
                logging.info("Made #FF tweet on @%s: %s" % (handle, ffTweet)) 
                ffTweetCount += 1
            except:
                logging.exception("#FF tweet failed for handle %s!" % handle)
            if ffTweetCount>=100:
                break
        logging.info("Finished #FF campaign with total %d FF tweets." % ffTweetCount) 
        
    def _followFridayTweet(self, topicName, ffHandles):
        tweet = "#FF %s " % topicName
        for handle in ffHandles:
            if len(handle)+len(tweet)+2>140:
                break
            else:
                tweet = "%s @%s" % (tweet, handle)
        return tweet 

    @classmethod
    def deferred_dup_and_deleted_cmp_channels(cls, delete_deleted=False, delete_dup=False):
        context.set_deferred_context(deploy=deploysns)
        cmp_users = User.all().filter('isContent', True).fetch(limit=1000)
        channel_map = {}
        deleted_count = 0
        for user in cmp_users:
            uid = user.uid
            channel_parent = ChannelParent.get_or_insert_parent(uid)
            channels = TAccount.all().ancestor(channel_parent).fetch(limit=1000)
            for channel in channels:
                chid = int(channel.keyNameStrip())
                channel_info = (channel, user)
                channel_infos = channel_map.get(chid, [])
                channel_infos.append(channel_info)
                channel_map[chid] = channel_infos
                if channel.deleted:
                    logging.info("Found a deleted channel %s for CMP user %s." % (channel.chid_handle_str(), user.id_email_str()))
                    deleted_count += 1
                    if delete_deleted: db.delete(channel)
        dup_channels = []
        dup_channel_info = {}
        for key, value in channel_map.items():
            if len(value) > 1:
                dup_channels.append([channel_info[0] for channel_info in value])
                dup_channel_info[key] = [(key, channel_info[0].name, channel_info[0].deleted, channel_info[0].modifiedTime, channel_info[1].key().id(), channel_info[1].mail) for channel_info in value]
        oldest_dups = []
        for dup_channel in dup_channels:
            oldest_dup = dup_channel[0]
            for channel in dup_channel:
                if channel.modifiedTime < oldest_dup.modifiedTime:
                    oldest_dup = channel
            logging.error("Found a duplicated channel %s!" % oldest_dup.chid_handle_str())
            oldest_dups.append(oldest_dup)
        dup_count = len(oldest_dups)
        logging.info("Found %d deleted channels and %d duplicated channels." % (deleted_count, dup_count))
        if delete_dup and oldest_dups:
            db.delete(oldest_dups)
            logging.info("Deleted %d duplicated channels." % len(oldest_dups))
        logging.info("Operation dup_and_deleted_cmp_channels finished.")
        return len(dup_channel_info), dup_channel_info
                
    @classmethod
    def deferred_clean_suspended_channels(cls):
        logging.info("Started cleaning suspended channels.")
        context.set_deferred_context(deploy=deploysns)
        cmp_users = User.all().filter('isContent', True).fetch(limit=1000)
        deleted_stats_count = 0
        deleted_channel_count = 0
        for user in cmp_users:
            logging.info("Cleaning suspended channels for user %s..." % user.mail)
            channel_parent = ChannelParent.get_or_insert_parent(user.uid)
            channels = TAccount.all().ancestor(channel_parent).filter('state', channel_const.CHANNEL_STATE_SUSPENDED).fetch(limit=1000)
            for channel in channels:
                chid = int(channel.keyNameStrip())
                cstats = CmpTwitterAcctStats.get_by_chid(chid)
                if cstats:
                    db.delete([cstats.get_or_insert_counter(), cstats])
                    deleted_stats_count += 1
                if not channel.deleted:
                    channel.deleted = True
                    db.put(channel)
                    deleted_channel_count += 1
        logging.info("Finished cleaning suspended channels. Deleted %d channels and %d stats." % (deleted_channel_count, deleted_stats_count))

    def clean_channel(self, params={}):
        chid = int(params.get('chid'))
        cstats = CmpTwitterAcctStats.get_by_chid(chid)
        if not cstats: return "Stats not found for channel %d!" % chid
        channel_name = cstats.name
        cstats_counter = cstats.get_or_insert_counter()
        db.delete([cstats_counter, cstats])
        return "Removed stats for channel %d@%s!" % (chid, channel_name)
    
    def clean(self, params={}):
        cursor = params.get('cursor', None)
        count = params.get('count', 0)
        updatedCount = 0
        try:
            logging.info("Start to clean CmpTwitterAcctStats records...")
            limit = 100
            while True:
                query = CmpTwitterAcctStats.all()
                if cursor:
                    query.with_cursor(cursor)
                statsList = query.fetch(limit=limit)
                count += len(statsList)
                logging.info("Queried %d stats." % count)
                for stats in statsList:
                    statsCounter = stats.get_or_insert_counter()
                    date, searchRanks = statsCounter.getSearchRanks()
                    updated = self._clean_search_ranks(searchRanks)
                    if not updated:
                        continue
                    statsCounter.searchRanks = DailyStatsCounterIF.text(date, searchRanks)
                    statsCounter.put()
                    updatedCount += 1
                logging.info("Cleaned %d records out of total %d records queried." % (updatedCount, count))
                cursor = query.cursor()
                logging.info("Query cursor: %s" % cursor)
                if len(statsList)<limit:
                    break
            return updatedCount
        except Exception:
            logging.exception("Unexpected error when cleaning CmpTwitterAcctStats records:")
            return -1
        finally:
            logging.info("Completed cleaning! Cleaned %d records out of total %d records queried." % (updatedCount, count))

    @classmethod
    def _clean_search_ranks(cls, searchRanks):
        if not searchRanks:
            return False
        lastPositiveIndex = -1
        for i in range(0, len(searchRanks)):
            if searchRanks[-i-1]>0:
                lastPositiveIndex = len(searchRanks)-i-1
                break
        if lastPositiveIndex==-1:
            return False
        updated = False
        rank = None
        for i in range(0, lastPositiveIndex):
            if searchRanks[i]:
                rank = searchRanks[i]
                continue
            if rank:
                searchRanks[i] = rank
                updated = True
        return updated 


class CmpTwitterAcctStatusSyncer(BackendTaskDaemonNoWait):
    def __init__(self):
        BackendTaskDaemonNoWait.__init__(self, workers=5)
        context.set_deferred_context(deploy=deploysns)
        self.stats_processor = CmpTwitterAcctStatsProcessor()
        
    @classmethod
    def deferred_execute(cls, params):
        return CmpTwitterAcctStatusSyncer().execute()

    def pre_execute(self):
        cmp_users = User.all().filter('isContent', True).fetch(limit=1000)
        logging.info("Channel Status Sync - started for %d users..." % (len(cmp_users), ))
        self.add_tasks(cmp_users)

    def post_execute(self):
        CmpTwitterAcctCacheMgr.build_all_cache(force=True)

    def run_impl(self, task):
        cmp_user = task
        uid = cmp_user.uid
        logging.info("Channel Status Sync - Started for user %d..." % uid)
        parent = ChannelParent.get_or_insert_parent(uid) 
        channels = TAccount.all().ancestor(parent).filter('deleted', False).fetch(limit=1000) 
        for channel in channels:
            try:
                stats = self.stats_processor.getStats(channel, uid)
                oldChannelState = channel.state
                newChannelState = channel.syncState()
                if newChannelState == oldChannelState:
                    continue
                elif newChannelState==channel_const.CHANNEL_STATE_SUSPENDED:
                    self.sync_channel_status(channel, uid, channel_const.CHANNEL_STATE_SUSPENDED, stats)
                else:
                    self.sync_channel_status(channel, uid, channel_const.CHANNEL_STATE_NORMAL, stats)
            except Exception:
                logging.exception("Channel Status Sync - Unexpected error for channel %s of user %d!" % (channel.chid_handle_str(), uid))

    def sync_channel_status(self, channel, uid, status, stats):
        try:
            if channel.state!=stats.chanState:
                stats.chanState = channel.state
                follow_source = Source.get_or_insert_by_cstats(stats)
                db_base.txn_put([stats, follow_source])
            if len(channel.topics)>0 and channel.cmpFeedCampaign is None:
                logging.error("Channel Status Sync - Channel '%s' doesn't have cmp feed campaign." % channel.name)
                if stats.addError(CmpTwitterAcctStats.ERROR_CHANNEL_NO_CMP_FEED_CAMPAIGN):
                    stats.put()
            if status==channel_const.CHANNEL_STATE_SUSPENDED:
                camp = channel.cmpFeedCampaign
                if camp:
                    camp.state = camp_const.CAMPAIGN_STATE_SUSPENDED
                    camp.put()
            else:
                camp = channel.cmpFeedCampaign
                if camp:
                    camp.state = camp_const.CAMPAIGN_STATE_ACTIVATED
                    camp.deleted = False
                    camp.put()
            logging.info("Channel Status Sync - Updated channel %s of user %d." % (channel.chid_handle_str(), uid))
        except Exception:
            logging.exception("Channel Status Sync - Unexpected error when syncing channel %s of user %d!" % (channel.chid_handle_str(), uid))
            return False


class CmpTwitterAcctStatsCounterProcessor(api_base.BaseProcessor):
    def __init__(self):
        context.get_context(raiseErrorIfNotFound=False).set_login_required(login_required=False)
        api_base.BaseProcessor.__init__(self, timeout=api_base.BaseProcessor.TIMEOUT_BACKEND)

    def getModel(self):
        return CmpTwitterAcctStatsCounter
    

class TopicStatsProcessor(api_base.BaseProcessor):
    def __init__(self):
        context.get_context(raiseErrorIfNotFound=False).set_login_required(login_required=False)
        api_base.BaseProcessor.__init__(self, timeout=api_base.BaseProcessor.TIMEOUT_BACKEND)

    def getModel(self):
        return TopicStats

    
class ContentSourceDailyStatsProcessor(api_base.BaseProcessor):
    def __init__(self):
        context.get_context(raiseErrorIfNotFound=False).set_login_required(login_required=False)
        api_base.BaseProcessor.__init__(self, timeout=api_base.BaseProcessor.TIMEOUT_BACKEND)

    def getModel(self):
        return ContentSourceDailyStats

    
class TwitterStatsHandler(object):
    def __init__(self, tapi):
        self.tapi = tapi
    
    @classmethod
    def api_name(cls):
        pass
    
    @classmethod
    def stats_attr(cls):
        pass
    
    @classmethod
    def stats_total_attr(cls):
        pass
    
    @classmethod
    def stats_counter_attr(cls):
        pass
    
    @classmethod
    def page_size(cls):
        return 100
    
    @classmethod
    def max_page_number(cls):
        return 1
    
    def max_result_size(self):
        return self.max_page_number()*(self.page_size()-1)
    
    def count(self, item):
        pass

    def date(self, item):
        return item['created_at']

    def callApi(self):
        max_id = None
        retry = 0
        results = []
        while retry < 3:
            try:
                page = self._callApi(max_id)
                if max_id and len(page)>0:
                    results.extend(page[1:])
                else:
                    results.extend(page)
                if len(page)<self.page_size() or len(results)>=self.max_result_size():
                    break
                max_id = page[-1]['id']
                retry = 0
            except Exception:
                retry += 1
                logging.exception("Failed Twitter API '%s' call for %s for %d times." % (self.api_name(), self.tapi.user_str(), retry))
                continue
        return results

    def _callApi(self):
        pass
    

class RetweetStatsHandler(TwitterStatsHandler):
    def __init__(self, tapi):
        TwitterStatsHandler.__init__(self, tapi)
    
    @classmethod
    def api_name(cls):
        return 'retweets_of_me'
    
    @classmethod
    def stats_attr(cls):
        return 'retweets'
    
    @classmethod
    def stats_total_attr(cls):
        return 'totalRetweets'
    
    @classmethod
    def stats_counter_attr(cls):
        return 'retweetCounts'
    
    def count(self, item):
        return item['retweet_count']
    
    def _callApi(self, max_id=None):
        """ Disabled as part of upgrading to Twitter API 1.1. """
        return []
#        if max_id:
#            return self.tapi.statuses.retweets_of_me(count=self.page_size(), max_id=max_id)
#        else:
#            return self.tapi.statuses.retweets_of_me(count=self.page_size())
    

class MentionStatsHandler(TwitterStatsHandler):
    def __init__(self, tapi):
        TwitterStatsHandler.__init__(self, tapi)
    
    @classmethod
    def api_name(cls):
        return 'mentions'
    
    @classmethod
    def stats_attr(cls):
        return 'mentions'
    
    @classmethod
    def stats_total_attr(cls):
        return 'totalMentions'
    
    @classmethod
    def stats_counter_attr(cls):
        return 'mentionCounts'
    
    @classmethod
    def page_size(cls):
        return 200
    
    def count(self, item):
        return 1
    
    def _callApi(self, max_id=None):
        if max_id:
            return self.tapi.statuses.mentions_timeline(count=self.page_size(), max_id=max_id)
        else:
            return self.tapi.statuses.mentions_timeline(count=self.page_size())
    

class BlackListProcessor(api_base.BaseProcessor):
    def getModel(self):
        return BlackList
    

class AgentProcessor(api_base.BaseProcessor):
    def getModel(self):
        return Agent


def getBlackList(pattern):
    blackList=BlackList.get_by_key_name(BlackList.keyName(pattern))
    if(blackList):
        patternValue=blackList.patternValue
        valueList = eval(patternValue)
        valueList.sort()
        return valueList
    else:
        params={'key_name':BlackList.keyName(pattern),'patternValue':'[]'}
        blackList=BlackListProcessor().create(params)
        patternValue=blackList.patternValue
        valueList = eval(patternValue)
        return valueList


def _matchedBotKeyword(agent, bot_kwds):
    agent_lower = agent.lower()
    for bot_kwd in bot_kwds:
        if agent_lower.find(bot_kwd.lower())!=-1 :
            logging.debug("Agent '%s' is detected to be a bot: name containing '%s'." % (agent, bot_kwd))
            return True
    return False


def getPatternValue(pattern):
    patternValue = memcache.get(BlackList.keyName(pattern))
    if patternValue is None:
        patternValue=getBlackList(pattern)
        memcache.set(BlackList.keyName(pattern), patternValue)
    return patternValue


def getAgentIpList(name):
    agent=Agent.get_by_key_name(Agent.keyName(name))
    if agent:
        ips=agent.ip
        ipList=eval(ips)
        return ipList
    else:
        return None


def addAgent(name,ip):
    try :
        agent=Agent.get_by_key_name(Agent.keyName(name))
        if agent:
            ipList=getAgentIpList(name)
            if ip in ipList:
                pass
            else:
                ipList.append(ip)
                ipValue=str(ipList)
                if len(ipValue) >500:
                    return
                else:
                    params={'id': Agent.get_by_key_name(Agent.keyName(name)).id, 
                            'ip': ipValue,
                            }
                    AgentProcessor().update(params)
        else:
            ipList=[]
            ipList.append(ip)
            ipValue=str(ipList)
            params={'key_name':Agent.keyName(name),'ip':ipValue}
            AgentProcessor().create(params)
    except :
        logging.exception("Unexpected error during agent update.")


def on_iframe_blacklist(url):
#    domain = url_util.full_domain(url)
#    if domain is None :
#        return False
#    domains = getPatternValue(log_const.PATTERN_FRAME_SITE)
#    ds = domain.split('.')
#    end = ds[len(ds)-1]
#    if len(end) == 2 and len(ds) >= 3:
#        d = '.'.join(ds[-3:])
#        if d in domains:
#            return True
#    d = '.'.join(ds[-2:])
#    if d in domains:
#        return True
    return False
        



