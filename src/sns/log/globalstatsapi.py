import datetime, time
import logging
from sets import ImmutableSet

from google.appengine.ext import db
from twitter.api import TwitterApi

import context, deploysns
from common.utils import url as url_util, timezone as ctz_util, klout as klout_util
from common.dateutil.parser import parser as datetime_parser
from common.utils import twitter as twitter_util
from common.content.trove import consts as trove_const
from sns.serverutils import deferred
from sns.core import consts as core_const
from sns.core.core import User, UserClickParent, ChannelParent, SystemStatusMonitor
from sns.core import base as db_base
from sns.core.base import DailyStatsCounterIF
from sns.api import consts as api_const
from sns.api import base as api_base
from sns.chan import consts as channel_const
from sns.chan.models import TAccount, ChannelClickCounter
from sns.chan.api import TAccountProcessor
from sns.cont import consts as cont_const
from sns.cont.models import Topic
from sns.cont import api as cont_api
from sns.cont.topic.api import TopicCacheMgr
from sns.camp import consts as camp_const
from sns.camp.models import Retweet
from sns.deal import consts as deal_const
from sns.deal.models import DealStats
from sns.deal import api as deal_api
from sns.usr.models import UserClickCounter
from sns.url.models import GlobalUrl, GlobalUrlCounter, ShortUrlClickCounter
from sns.post.models import SPost
from sns.log import consts as log_const
from sns.log.models import CmpTwitterAcctStats, GlobalStats, TopicStats, ContentSourceDailyStats
from sns.log.api import CmpTwitterAcctStatsProcessor, RetweetStatsHandler, MentionStatsHandler



class GlobalStatsUpdater():
    def __init__(self, processor=None, statsId=None, stats=None):
        self.processor = processor
        self.statsId = statsId
        self.now = self.processor.now
        self.dayStart = self.processor.dayStart
        self.dayEnd = self.processor.dayEnd
        self.has_error = False
        if stats:
            self.stats = stats
        else:
            self.stats = GlobalStats.get_or_insert_by_id(self.statsId)
        self.statsDate, self.statsInfo = self.stats.get_counter_info()
        self.total = None

    def execute(self):
        if not self.ready():
            return
        self.preExecute()
        self.executeImpl()
        self.postExecute()
        return self.has_error

    def updatedToday(self):
        if self.statsDate and self.statsDate>=self.processor.statsDate:
            logging.info("The global stats %d is already updated today!" % self.statsId)
            return True
        return False

    def ready(self):
        return not self.updatedToday()

    def preExecute(self):
        if self.processor.cmpUsers is None:
            self.processor.cmpUsers = User.all().filter('isContent', True).fetch(limit=1000)
            for cmpUser in self.processor.cmpUsers:
                self.processor.cmpUserMapById[cmpUser.key().id()] = cmpUser

    def executeImpl(self):
        pass

    def postExecute(self):
        if self.has_error:
            logging.warn("Failed updating global stats %d because of error." % self.statsId)
            return
        self.update_info()
        self.stats.put()
        logging.info("Finished updating global stats %d." % self.statsId)

    def update_info(self):
        self.stats.set_counter_info(self.total, self.processor.statsDate)

    def _logException(self):
        logging.exception("Unexpected error when updating global stats %d:" % self.statsId)

    def count(self, clazz, attr):
        userIds = self.processor.cmpUserMapById.keys()
        self.total = 0
        filterDate = self.dayEnd - datetime.timedelta(days=1)
        while True:
            try:
                objs = clazz.all().filter(attr+' > ', filterDate).order(attr).fetch(limit=100)
                if len(objs) == 0:
                    break
                for obj in objs:
                    filterDate = getattr(obj, attr)
                    if self.statsId==log_const.GLOBAL_STATS_CMP_POSTS:
                        if obj.uid in userIds and filterDate < self.dayEnd:
                            self.total += 1
                    else:
                        if filterDate < self.dayEnd:
                            self.total += 1
                if filterDate >= self.dayEnd:
                    break
            except Exception:
                self._logException()


class GlobalStatsUpdaterNonCounter(GlobalStatsUpdater):
    def __init__(self, processor=None, statsId=None, stats=None):
        GlobalStatsUpdater.__init__(self, processor=processor, statsId=statsId, stats=stats)

    def update_info(self):
        self.stats.set_non_counter_info(self.processor.statsDate, self.statsInfo)


class GlobalStatsHistoryUpdaterIF:
    @classmethod
    def channel_stats_counter_attr(cls):
        pass
    
    @classmethod
    def channel_stats_padding_type(cls):
        return DailyStatsCounterIF.PADDING_ZERO
    
    def updateHistory(self, allStatsCounters, days):
        if days<=0:
            return
        totalCounts = [0]*days
        updated = False
        count = 0
        for statsCounter in allStatsCounters:
            count += 1
            date, counts = statsCounter.getCounts(self.channel_stats_counter_attr())
            if counts is None or len(counts)==0:
                continue
            if date is None:
                continue
            offset = (self.processor.statsDate - date).days
            if offset<0:
                counts = counts[:offset]
            elif offset>0:
                paddings = DailyStatsCounterIF.paddings(self.channel_stats_padding_type(), offset, oldValue=counts[-1])
                counts.extend(paddings) 
            counts.reverse()
            self.updateHistoryTotal(totalCounts, counts)
            updated = True
            if count%1000==0:
                logging.info("Global stats '%s' history update progress: %d counters." % (self.channel_stats_counter_attr(), count))
        if updated:
            totalCounts.reverse()
            self.normalizeHistoryTotal(totalCounts)
            if self.statsInfo and len(self.statsInfo)>len(totalCounts):
                statsInfo = self.statsInfo[:-len(totalCounts)] + totalCounts
            else:
                statsInfo = totalCounts
            self.stats.info = DailyStatsCounterIF.text(self.processor.statsDate, statsInfo)
            self.stats.put()
        logging.info("Global stats '%s' history update finished: %d counters." % (self.channel_stats_counter_attr(), count))
    
    def updateHistoryTotal(self, totalCounts, counts):
            for i in range(0, min(len(totalCounts), len(counts))):
                totalCounts[i] += counts[i]
                
    def normalizeHistoryTotal(self, totalCounts):
        pass
    

class GlobalStatsUpdaterCmpClicks(GlobalStatsUpdater):
    def __init__(self, processor):
        GlobalStatsUpdater.__init__(self, processor=processor, statsId=log_const.GLOBAL_STATS_CMP_CLICKS)

    def executeImpl(self):
        self.total = 0
        for user in self.processor.cmpUsers:
            try:
                uid = user.uid
                parent = UserClickParent.get_or_insert_parent(uid=uid)
                userClickCounter = UserClickCounter.get_or_insert(UserClickCounter.keyName(uid),parent=parent)
                counters = userClickCounter.normalizedHourCounters(self.now)
                counters = counters[-24:]
                for c in counters:
                    self.total += c
            except Exception:
                self._logException()
        

class GlobalStatsUpdaterCmpPosts(GlobalStatsUpdater):
    def __init__(self, processor):
        GlobalStatsUpdater.__init__(self, processor=processor, statsId=log_const.GLOBAL_STATS_CMP_POSTS)

    def executeImpl(self):
        self.count(clazz=SPost, attr='modifiedTime')
        

class GlobalStatsUpdaterTotalPosts(GlobalStatsUpdater):
    def __init__(self, processor):
        GlobalStatsUpdater.__init__(self, processor=processor, statsId=log_const.GLOBAL_STATS_TOTAL_POSTS)

    def executeImpl(self):
        self.count(clazz=SPost, attr='modifiedTime')
        

class GlobalStatsUpdaterTotalUniqueUrls(GlobalStatsUpdater):
    def __init__(self, processor):
        GlobalStatsUpdater.__init__(self, processor=processor, statsId=log_const.GLOBAL_STATS_TOTAL_UNIQUE_URLS)

    def executeImpl(self):
        self.count(clazz=GlobalUrl, attr='createdTime')
        

class GlobalStatsUpdaterCmpClickedUrls(GlobalStatsUpdater):
    def __init__(self, processor):
        GlobalStatsUpdater.__init__(self, processor=processor, statsId=log_const.GLOBAL_STATS_CMP_CLICKED_URLS)

    def executeImpl(self):
        self.count(clazz=GlobalUrlCounter, attr='createdTime')
        

class GlobalStatsUpdaterTotalClicks(GlobalStatsUpdater):
    def __init__(self, processor):
        GlobalStatsUpdater.__init__(self, processor=processor, statsId=log_const.GLOBAL_STATS_TOTAL_CLICKS)

    def executeImpl(self):
        self.total = 0
        offset = 0
        while True:
            try:
                clickCounters = UserClickCounter.all().fetch(limit=100,offset=offset)
                if len(clickCounters) == 0:
                    break
                for clickCounter in clickCounters:
                    offset += 1
                    clicks =  clickCounter.normalizedHourCounters(self.now)
                    clicks = clicks[-24:]
                    for c in clicks:
                        self.total += c
            except Exception:
                self._logException()
        

class GlobalStatsUpdaterCmpCounterUpdate(GlobalStatsUpdaterNonCounter):
    def __init__(self, processor, userHashCode):
        GlobalStatsUpdaterNonCounter.__init__(self, processor=processor, statsId=GlobalStatsUpdaterCmpCounterUpdate.user_hash_code_2_stats_id(userHashCode))
        self.userHashCode = userHashCode
        self.users = []

    @classmethod
    def user_hash_code_2_stats_id(cls, userHashCode):
        return log_const.GLOBAL_STATS_CMP_COUNTER_UPDATER_0 + userHashCode
    
    @classmethod
    def updating_statuses(cls, processor):
        return [cls(processor=processor, userHashCode=userHashCode).updatedToday() for userHashCode in range(0, User.USER_HASH_SIZE)]
    
    @classmethod
    def monitor_key_name(cls, userHashCode):
        return cont_const.MONITOR_GLOBAL_STATS_CMP_COUNTER_UPDATER % userHashCode

    def monitorKeyName(self):
        return self.monitor_key_name(self.userHashCode)

    def ready(self):
        if not GlobalStatsUpdaterNonCounter.ready(self):
            return False
        return SystemStatusMonitor.acquire_lock(self.monitorKeyName(), preempt=7200)

    def preExecute(self):
        allCmpUsers = User.all().filter('isContent', True).fetch(limit=1000)
        for cmpUser in allCmpUsers:
            if self.userHashCode==cmpUser.hashCode():
                self.users.append(cmpUser)

    def executeImpl(self):
        logging.info("Updating channel stats for user hash %d with %d users..." % (self.userHashCode, len(self.users)))
        count = 0
        try:
            for user in self.users:
                self.updateStatsForUserChannels(user.uid, user.mail)
                count += 1
        except:
            logging.exception("Unexpected error when dispatching deferred jobs of updating user channel stats: (dispatched %d out of %d) " % (count, len(self.users)))

    def postExecute(self):
        GlobalStatsUpdater.postExecute(self)
        SystemStatusMonitor.release_lock(self.monitorKeyName())

    def updateStatsForUserChannels(self, uid, userEmail):
        logging.info("Updating channel stats for user '%s'(%s)..." % (userEmail, uid))
        parent = ChannelParent.get_or_insert_parent(uid)
        unfilteredChannels = TAccount.all().ancestor(parent).filter('deleted', False).order('nameLower').fetch(limit=1000)
        statsMap = self.get_cstats_for_update(uid, unfilteredChannels, userEmail)
        statsCounterMap = dict([(stats, stats.get_or_insert_counter()) for stats in statsMap.values()])
        channels = []
        for channel in unfilteredChannels:
            chid = channel.keyNameStrip()
            stats = statsMap.get(chid, None)
            if stats:
                if stats.updd == self.processor.statsDate:
                    logging.error(self._statsLogMsg("Already updated!", stats))
                else:
                    channels.append(channel)
        self.updateChannelClickCounts(uid, channels, statsMap, statsCounterMap)
        self.updateChannelPostCounts(uid, statsMap, statsCounterMap)
        self.updateChannelProfiles(channels, statsMap, statsCounterMap)
#        self.updateChannelRetweets(channels, statsMap, statsCounterMap)
#        self.updateChannelKloutScores(channels, statsMap, statsCounterMap)
#        self.updateChannelMentions(channels, statsMap, statsCounterMap)
        for channel in channels:
            stats = statsMap[channel.keyNameStrip()]
            statsCounter = statsCounterMap[stats]
            stats.updd = self.processor.statsDate
            db_base.txn_put([stats, statsCounter])
            logging.debug(self._statsLogMsg("Finished successfully.", stats))
                  
    def _statsLogMsg(self, msg, stats):
        return "Updating channel stats: %s | channel='%s'(%d), user=%s, updd=%s" % (msg, stats.name, stats.chid, stats.userEmail, stats.updd)
        
    def get_cstats_for_update(self, uid, channels, userEmail):
        statsMap = {}
        for channel in channels:
            chid = channel.keyNameStrip()
            stats = CmpTwitterAcctStats.get_by_chid(chid)
            if stats is None:
                logging.error("Stats not found for channel '%s(%s)'!" % (channel.name, chid))
                continue
            stats.uid = uid
            stats.userEmail = userEmail
            stats.reset()
            statsMap[chid] = stats
        return statsMap

    def updateChannelClickCounts(self, uid, channels, statsMap, statsCounterMap):
        now = datetime.datetime.utcnow()
        clickParent = UserClickParent.get_or_insert_parent(uid=uid)
        for channel in channels:
            chid = channel.keyNameStrip()
            stats = statsMap[chid]
            clickCounter = ChannelClickCounter.get_or_insert(channel.key().name(),parent=clickParent)
            clicks =  clickCounter.normalizedHourCounters(now)[-24:]
            click = 0
            for c in clicks:
                click += c
            stats.latelyClick = click
            statsCounter = statsCounterMap[stats]
            statsCounter.setClickCount(stats.latelyClick, self.processor.statsDate)
            stats.totalClick = statsCounter.totalClicks()

    def updateChannelPostCounts(self, uid, statsMap, statsCounterMap):
        filterDate = self.dayEnd
        while True:
            try:
                posts = SPost.all().filter('uid', uid).filter('state', camp_const.EXECUTION_STATE_FINISH).filter('modifiedTime < ', filterDate).order('-modifiedTime').fetch(limit=100)
                if len(posts) == 0:
                    break
                for post in posts:
                    if post.modifiedTime > self.dayStart:
                        chid = str(post.chid)
                        if chid in statsMap.keys():
                            stats = statsMap[chid]
                            stats.latelyPost += 1
                            stats.hashtags += post.count_hashtags()
                filterDate = posts[-1].modifiedTime
                if filterDate < self.dayStart:
                    break
            except:
                logging.exception("Unexpected error when getting post count for channel stats.")
        for stats in statsMap.values():
            statsCounter = statsCounterMap[stats]
            statsCounter.setPostCount(stats.latelyPost, self.processor.statsDate)
            statsCounter.setHashtagCount(stats.hashtags, self.processor.statsDate)
            stats.totalPost = statsCounter.totalPosts()
            stats.totalHashtags = statsCounter.totalHashtags()
    
    def updateChannelProfiles(self, channels, statsMap, statsCounterMap):
        for channel in channels:
            stats = statsMap[channel.keyNameStrip()]
            if stats.chanState==channel_const.CHANNEL_STATE_NORMAL:
                self._updateOneChannelProfile(channel, stats)
            statsCounter = statsCounterMap[stats]
            statsCounter.setFollowerCount(stats.latelyFollower, self.processor.statsDate)

    def _updateOneChannelProfile(self, channel, stats):
        retry = 0
        while retry < 3:
            retry += 1
            try:
                try:
                    tapiResults = channel.get_twitter_api().account.verify_credentials()
                except Exception:
                    logging.exception("Failed getting follower count for channel '%s' for %d times." % (channel.name, retry))
                    continue
                if not tapiResults or not tapiResults.has_key('followers_count'):
                    logging.warning("Twitter info does not contain follower count: %s" % str(tapiResults))
                    break
                stats.latelyFollower = int(tapiResults["followers_count"])
                name = tapiResults.get("screen_name", "")
                nameLower = name.lower()
                avatarUrl=tapiResults.get("profile_image_url", "")
                description = tapiResults.get("description", "")
                backGround = tapiResults.get("profile_background_image_url", "")
                accountName = tapiResults.get("name", "")
                accountUrl = tapiResults.get("url", "")
                location = tapiResults.get("location", "")
                acctCreatedAtStr = tapiResults.get("created_at", "")
                acctCreatedTime = twitter_util.t_strptime(acctCreatedAtStr)
                stats.acctCreatedTime = acctCreatedTime
                stats.name = name
                stats.nameLower = nameLower
                channel.acctCreatedTime = acctCreatedTime
                channel.name = name
                channel.nameLower = nameLower
                channel.avatarUrl = avatarUrl
                channel.description = description
                channel.backGround = backGround
                channel.accountName = accountName
                channel.accountUrl = accountUrl
                channel.location = location
                channel.put()
                from soup.user.models import SoupUser
                user = SoupUser.get_or_insert_by_sns_channel(channel)
                user.name = name
                user.nameLower = nameLower
                user.avatarUrl = avatarUrl
                user.put()
                break
            except Exception:
                logging.exception("Unexpected error when getting follower count for channel '%s'." % (channel.name,))

    def updateChannelRetweets(self, channels, statsMap, statsCounterMap):
        self._updateChannelTwitterStats(channels, statsMap, statsCounterMap, RetweetStatsHandler)
    
    def updateChannelMentions(self, channels, statsMap, statsCounterMap):
        self._updateChannelTwitterStats(channels, statsMap, statsCounterMap, MentionStatsHandler)
    
    TWITTER_STATS_CUT_OFF_DATE = datetime.date(year=2011, month=7, day=1)
    def _updateChannelTwitterStats(self, channels, statsMap, statsCounterMap, tapiHandlerClass):
        for channel in channels:
            stats = statsMap[channel.keyNameStrip()]
            if stats.chanState==channel_const.CHANNEL_STATE_SUSPENDED:
                continue
            statsCounter = statsCounterMap[stats] 
            tapi = TwitterApi(oauth_access_token=stats.oauthAccessToken)
            tapiHandler = tapiHandlerClass(tapi)
            tapiResults = tapiHandler.callApi()
            if len(tapiResults)==0:
                continue
            try:
                tapiResults.reverse()
                dateCountMap = {}
                firstResultDate = None
                for result in tapiResults:
                    try:
                        utcTime = datetime_parser().parse(tapiHandler.date(result))
                        uspTime = ctz_util.to_uspacific(utcTime)
                        uspDate = uspTime.date()
                        if firstResultDate is None:
                            firstResultDate = uspDate
                        if uspDate<self.TWITTER_STATS_CUT_OFF_DATE or uspDate>self.processor.statsDate or len(tapiResults)==tapiHandler.page_size() and uspDate==firstResultDate:
                            continue
                        count = tapiHandler.count(result)
                        dateCount = dateCountMap.get(uspDate, 0)
                        dateCount += count
                        dateCountMap[uspDate] = dateCount
                    except:
                        logging.exception("Unexpected error when parsing Twitter API '%s' results for channel '%s'." % (tapiHandler.api_name(), channel.name))
                logging.debug("Twitter API '%s' results for channel '%s': %s" % (tapiHandler.api_name(), channel.name, str(dateCountMap)))
            except Exception:
                logging.exception("Unexpected error on Twitter API '%s' call for channel '%s'." % (tapiHandler.api_name(), channel.name))
            if not dateCountMap.has_key(self.processor.statsDate):
                dateCountMap[self.processor.statsDate] = 0
            dates = dateCountMap.keys()
            dates.sort()
            setattr(stats, tapiHandler.stats_attr(), dateCountMap[dates[-1]])
            statsCounter.cleanCounts(tapiHandler.stats_counter_attr(), dates[0])
            for date in dates:
                statsCounter.setCount(tapiHandler.stats_counter_attr(), dateCountMap[date], date)
            setattr(stats, tapiHandler.stats_total_attr(), statsCounter.totalCounts(tapiHandler.stats_counter_attr()))

    def updateChannelKloutScores(self, channels, statsMap, statsCounterMap):
        try:
            twitterHandleMap = dict([(channel.keyNameStrip(), channel.name) for channel in channels])
            channelKloutScoreMap = klout_util.op_klout_scores(context.get_context().klout_key(), twitterHandleMap.values())
            time.sleep(0.2) 
            for chid in twitterHandleMap.keys():
                handle = twitterHandleMap[chid]
                stats = statsMap[chid]
                kloutScore = channelKloutScoreMap.get(handle, None)
                if kloutScore is not None:
                    stats.latestKloutScore = kloutScore
                else:
                    """ Treat as a Klout API failure. """
                    if stats.latestKloutScore is None:
                        stats.latestKloutScore = 0
                statsCounter = statsCounterMap[stats]
                statsCounter.setKloutScore(stats.latestKloutScore, self.processor.statsDate)
        except:
            logging.exception("Unexpected error when updating channel Klout scores:")

#    def getSeedChannels(self, uid=2255053):
#        if context.get_context().is_primary_app():
#            try:
#                seedParent = ChannelParent.get_or_insert_parent(uid)
#                return TAccount.all().filter('deleted', False).filter('state', channel_const.CHANNEL_STATE_NORMAL).order('nameLower').ancestor(seedParent).fetch(limit=1000)
#            except Exception:
#                logging.exception('Error when getting seed channels!')
#        return []


class GlobalStatsUpdaterCmpCounterSum(GlobalStatsUpdater):
    def __init__(self, processor, statsId):
        GlobalStatsUpdater.__init__(self, processor=processor, statsId=statsId)

    def executeImpl(self):
        self.total = 0
        count = 0
        try:
            query = CmpTwitterAcctStats.all().filter('chanState', channel_const.CHANNEL_STATE_NORMAL)
            limit = CmpTwitterAcctStats.QUERY_LIMIT
            cursor = None
            while True:
                if cursor:
                    query.with_cursor(cursor)
                statsList = query.fetch(limit=limit)
                count += len(statsList)
                logging.debug("Queried %d channel stats." % count)
                for stats in statsList:
                    self.total += self.count_one_acct(stats)
                if len(statsList)<limit:
                    break
                cursor = query.cursor()
        except Exception:
            self._logException()
        finally:
            logging.info("Queried total %d channel stats." % count)

    def count_one_acct(self, stats):
        pass
    

class GlobalStatsUpdaterCmpFollowers(GlobalStatsUpdaterCmpCounterSum):
    def __init__(self, processor):
        GlobalStatsUpdaterCmpCounterSum.__init__(self, processor=processor, statsId=log_const.GLOBAL_STATS_CMP_FOLLOWERS)

    def count_one_acct(self, stats):
        return stats.latelyFollower
    

class GlobalStatsUpdaterCmpHashtags(GlobalStatsUpdaterCmpCounterSum):
    def __init__(self, processor):
        GlobalStatsUpdaterCmpCounterSum.__init__(self, processor=processor, statsId=log_const.GLOBAL_STATS_HASHTAGS)

    def count_one_acct(self, stats):
        return stats.hashtags
    

class GlobalStatsUpdaterCmpAccts(GlobalStatsUpdater):
    def __init__(self, processor):
        GlobalStatsUpdater.__init__(self, processor=processor, statsId=log_const.GLOBAL_STATS_CMP_TWITTER_ACCTS)

    def executeImpl(self):
        self.total = CmpTwitterAcctStatsProcessor.sns_normal_stats_count()
        

class GlobalStatsUpdaterCmpActiveFeCampaigns(GlobalStatsUpdater):
    def __init__(self, processor):
        GlobalStatsUpdater.__init__(self, processor=processor, statsId=log_const.GLOBAL_STATS_CMP_ACTIVE_FE_CAMPAIGNS)

    def executeImpl(self):
        self.total = CmpTwitterAcctStats.all().filter('state', core_const.FOLLOW_STATS_ACTIVATED).count(limit=10000)
        

class GlobalStatsUpdaterCmpAcctNoTopics(GlobalStatsUpdaterNonCounter):
    def __init__(self, processor):
        GlobalStatsUpdaterNonCounter.__init__(self, processor=processor, statsId=log_const.GLOBAL_STATS_CMP_TWITTER_ACCT_NO_TOPICS)

    def executeImpl(self):
        info = []
        for user in self.processor.cmpUsers:
            channels = TAccount.all().filter('deleted =',False).ancestor(ChannelParent.get_or_insert_parent(uid=user.uid)).order('nameLower').fetch(limit=100)
            for channel in channels:
                addInfo = False
                if len(channel.topics) == 0 :
                    addInfo = True
                    theTopic = 'None'
                else:
                    topicKey = channel.topics[0]
                    topic = Topic.get_by_key_name(Topic.keyName(topicKey))
                    if topic is None:
                        addInfo = True
                        theTopic = topicKey
                if addInfo:
                    info.append(channel.name+':'+user.mail+':'+theTopic)
        self.statsInfo = info


class GlobalStatsUpdaterCmpTwitterAcctBasicInfo(GlobalStatsUpdaterNonCounter):
    def __init__(self, processor):
        GlobalStatsUpdaterNonCounter.__init__(self, processor=processor, statsId=log_const.GLOBAL_STATS_CMP_TWITTER_ACCT_BASIC_INFO)

    def executeImpl(self):
        chinfomap = {}
        try:
            cstats_list = CmpTwitterAcctStatsProcessor().execute_query_all(params={})
            for cstats in cstats_list:
                chinfomap[cstats.chid] = (int(cstats.chanState), int(cstats.latelyFollower), int(cstats.totalClick), int(cstats.totalPost))
        except Exception:
            self._logException()
        self.statsInfo = str(chinfomap)
        logging.info("Collected basic channel info for %d channels." % len(chinfomap))
        
        
class GlobalStatsUpdaterOnceSuspendedChids(GlobalStatsUpdaterNonCounter):
    def __init__(self, processor):
        GlobalStatsUpdaterNonCounter.__init__(self, processor=processor, statsId=log_const.GLOBAL_STATS_ONCE_SUSPENDED_CHIDS)

    def executeImpl(self):
        chids = set([])
        try:
            limit = 1000
            query_suspended = db.Query(TAccount, keys_only=True).filter('isContent', True).filter('state = ', channel_const.CHANNEL_STATE_SUSPENDED).order('-suspendedTime')
            query_restored = db.Query(TAccount, keys_only=True).filter('isContent', True).filter('state = ', channel_const.CHANNEL_STATE_NORMAL).filter('isRestored = ', True).order('-restoredTime')
            key_list = query_suspended.fetch(limit=limit)
            suspended_count = len(key_list)
            key_list.extend(query_restored.fetch(limit=limit))
            restored_count = len(key_list) - suspended_count
            chid_list = [int(TAccount.key_name_strip(key)) for key in key_list]
            chids = set(chid_list)
            logging.info("Refreshing once suspended account list: %d suspended, %d restored, %d total" % (suspended_count, restored_count, len(chids)))
        except Exception:
            self._logException()
        finally:
            if chids:
                self.statsInfo = str(chids)
        
        
class GlobalStatsUpdaterDealStats(GlobalStatsUpdaterNonCounter):
    def __init__(self, processor):
        GlobalStatsUpdaterNonCounter.__init__(self, processor=processor, statsId=log_const.GLOBAL_STATS_DEAL_STATS)

    @classmethod
    def deferred_execute(cls):
        context.set_deferred_context(deploy=deploysns)
        return cls(processor=GlobalStatsProcessor()).execute()

    def preExecute(self):
        pass
    
    def executeImpl(self):
        """ 
        lcd - stands for location category deals. 
        ld - stands for location deals.
        """
        try:
            logging.info("Started daily updating of deal stats...")
            dstats_map, counter_map = deal_api.DealStatsProcessor().daily_deal_count_update()
            logging.info("Updated deal counts for %d deal stats." % len(dstats_map))
            dc_map = CmpTwitterAcctStatsProcessor().deal_channel_map()
            cstats_list = CmpTwitterAcctStats.get_by_key_name([str(dc) for dc in dc_map.keys()])
            counts_map = {}
            key_name_total_total = deal_const.LOCATION_CATEGORY_KEY_TOTAL
            for cstats in cstats_list:
                if not cstats:
                    logging.critical("Some deal stats entry is missing!")
                    continue
                location, category = dc_map[cstats.chid]
                key_name = '_'.join([location, category])
                dstats = dstats_map.get(key_name, None)
                if dstats:
                    dstats.channels = [cstats.name]
                else:
                    logging.info("Missing deal stats of key_name: %s" % key_name)
                    continue
                key_name_location_total = DealStats.location_total_key(location)
                key_name_total_category = DealStats.total_category_key(category)
                self._add_counts_4_location_category(cstats, counts_map, key_name)
                self._add_counts_4_location_category(cstats, counts_map, key_name_location_total)
                self._add_counts_4_location_category(cstats, counts_map, key_name_total_category)
                self._add_counts_4_location_category(cstats, counts_map, key_name_total_total)
            for key_name, counts in counts_map.items():
                dstats = dstats_map.get(key_name, None)
                if dstats is None:
                    logging.info("Missing deal stats of key_name: %s" % key_name)
                    continue
                counter = counter_map[key_name]
                clicks, followers = counts
                counter.setClickCount(clicks, self.processor.dayEnd)
                counter.setFollowerCount(followers, self.processor.dayEnd)
                dstats.updd = self.processor.statsDate
                dstats.clicks = clicks
                dstats.totalClicks = counter.totalClicks()
                dstats.followers = followers
                db_base.txn_put([dstats, counter])
            logging.info("Updated click and follower counts for %d deal stats." % len(dstats_map))
        except Exception:
            self._logException()
            self.has_error = True

    def _add_counts_4_location_category(self, cstats, counts_map, key_name):
        counts = counts_map.get(key_name, (0, 0))
        counts_map[key_name] = (counts[0] + cstats.latelyClick, counts[1] + cstats.latelyFollower)
    
        
class GlobalStatsUpdaterContentSource(GlobalStatsUpdaterNonCounter):
    def __init__(self, processor):
        GlobalStatsUpdaterNonCounter.__init__(self, processor=processor, statsId=log_const.GLOBAL_STATS_CONTENT_SOURCE)
        self._trove_hosted_map = {} # Cache trove hosted status for each url

    @classmethod
    def deferred_execute(cls):
        context.set_deferred_context(deploy=deploysns)
        return cls(processor=GlobalStatsProcessor()).execute()

    def preExecute(self):
        pass
    
    def executeImpl(self):
        self.has_error = not self._execute_impl()
        self.statsInfo = str([])

    def _execute_impl(self):
        success = False
        try:
            """ Phase 1 - Collect domain click counts """
            domain_clicks = self._collect_click_counts()             

            """ Phase 2 - Collect domain post counts """
            domain_posts = self._collect_post_counts()             
            
            """ Phase 3 - Update all domain stats """
            all_updated_domains = domain_posts.keys()
            all_updated_domains.extend(domain_clicks.keys()) 
            all_updated_domains = set(all_updated_domains) 
            logging.info("Started updating total %d domain stats..." % len(all_updated_domains))
            update_list = []
            for domain in all_updated_domains:
                csstats = ContentSourceDailyStats.get_or_insert_by_name(domain)
                csstats.posts = domain_posts.get(domain, 0)
                csstats.clicks = domain_clicks.get(domain, 0)
                csstats_counter = csstats.get_or_insert_counter()
                csstats_counter.setPostCount(csstats.posts, self.processor.statsDate)
                csstats_counter.setClickCount(csstats.clicks, self.processor.statsDate)
                csstats.totalPosts = csstats_counter.totalPosts()
                csstats.totalClicks = csstats_counter.totalClicks()
                csstats.updd = self.processor.statsDate
                update_list.extend([csstats, csstats_counter])
            db_base.put(update_list)
            logging.info("Finished updating %d domain stats." % len(all_updated_domains))
            success = True
        except:
            logging.exception("Unexpected error when updating domain stats!")
        return success

    def _is_trove_hosted(self, url):
        if not context.is_trove_enabled(): return None
        if not url: return None
        if not self._trove_hosted_map.has_key(url):
            global_url = GlobalUrl.get_by_url(url)
            hosted = None
            if global_url and global_url.is_trove_ingested(): 
                hosted = global_url.troveState == trove_const.URL_STATE_HOSTED
            self._trove_hosted_map[url] = hosted
        return self._trove_hosted_map.get(url)
        
    def _collect_post_counts(self):
        logging.info("Started counting posts per domain from SPost...")
        domain_posts = {}
        trove_hosted_posts = 0
        trove_unhosted_posts = 0
        LIMIT = 500
        cursor = 0
        total = 0
        query = SPost.all().filter('modifiedTime >= ', self.dayStart).filter('modifiedTime < ', self.dayEnd)
        while True:
            if cursor:
                query.with_cursor(cursor)
            posts = query.fetch(limit=LIMIT)
            for post in posts:
                domain = post.domain()
                if domain:
                    if domain_posts.has_key(domain):
                        domain_posts[domain] += 1
                    else:
                        domain_posts[domain] = 1
                trove_hosted = self._is_trove_hosted(post.url)
                if trove_hosted is None: continue
                if trove_hosted:
                    trove_hosted_posts += 1
                else:
                    trove_unhosted_posts += 1
            total += len(posts)
            if total and total % 2000 == 0:
                logging.info("Counted total %d SPost objects." % total)
            if len(posts) < LIMIT/2:
                break
            cursor = query.cursor()
        logging.info("Finished counting posts for %d domains from %d SPost objects." % (len(domain_posts), total))
        domain2cs = cont_api.Domain2CSProcessor()
        cs_posts = {cont_const.CS_ALL: total, cont_const.CS_TROVE_HOSTED: trove_hosted_posts, cont_const.CS_TROVE_UNHOSTED: trove_unhosted_posts}
        for domain, posts in domain_posts.items():
            cskey = domain2cs.get_cskey_by_domain(domain)
            if cskey == domain:
                continue
            count = cs_posts.get(cskey, 0)
            count += posts
            cs_posts[cskey] = count
        logging.info("Finished counting posts for %d content sources." % (len(cs_posts), ))
        domain_posts.update(cs_posts)  
        return domain_posts

    def _collect_click_counts(self):
        logging.info("Started counting clicks from short URL click counters...")
        domain_clicks = {}
        total_clicks = 0
        trove_hosted_clicks = 0
        trove_unhosted_clicks = 0
        created_time_stats = {'day':0, 'week':0, 'month':0, 'life':0}
        cutoff_day = self.dayStart
        cutoff_week = cutoff_day - datetime.timedelta(days=6)
        cutoff_month = cutoff_day - datetime.timedelta(days=29)
        LIMIT = 500
        HASH_FACTOR = 47
        url_hash = [set([])] * HASH_FACTOR
        cursor = None
        total = 0
        query = ShortUrlClickCounter.all().filter('modifiedTime >= ', self.dayStart)
        while True:
            if cursor:
                query.with_cursor(cursor)
            url_counters = query.fetch(limit=LIMIT)
            total += len(url_counters)
            for url_counter in url_counters:
                url = url_counter.url()
                hashcode = hash(url) % HASH_FACTOR
                if url in url_hash[hashcode]:
                    continue
                url_hash[hashcode].add(url)
                count = url_counter.yesterday_count()
                if count == 0:
                    continue
                created_time_stats['life'] += count
                if url_counter.createdTime >= cutoff_month:
                    created_time_stats['month'] += count
                if url_counter.createdTime >= cutoff_week:
                    created_time_stats['week'] += count
                if url_counter.createdTime >= cutoff_day:
                    created_time_stats['day'] += count
                total_clicks += count
                domain = url_util.root_domain(url)
                if domain_clicks.has_key(domain):
                    domain_clicks[domain] += count
                else:
                    domain_clicks[domain] = count
                trove_hosted = self._is_trove_hosted(url)
                if trove_hosted is None: continue
                if trove_hosted:
                    trove_hosted_clicks += count
                else:
                    trove_unhosted_clicks += count
            if total and total % 2000 == 0:
                logging.info("Counted %d short URL click counters with %d clicks yesterday." % (total, total_clicks))
            if len(url_counters) < LIMIT/2:
                break 
            cursor = query.cursor()
        logging.info("Finished counting %d short URL click counters with %d clicks into %d root domains." % (total, total_clicks, len(domain_clicks)))
        logging.info("Clicks distribution by short URL created time: %s" % created_time_stats)
        cs_clicks = {cont_const.CS_ALL: total_clicks, cont_const.CS_TROVE_HOSTED: trove_hosted_clicks, cont_const.CS_TROVE_UNHOSTED: trove_unhosted_clicks}
        domain2cs = cont_api.Domain2CSProcessor()
        for domain, clicks in domain_clicks.items():
            cskey = domain2cs.get_cskey_by_domain(domain)
            if cskey is None or cskey == domain:
                continue
            count = cs_clicks.get(cskey, 0)
            count += clicks
            cs_clicks[cskey] = count
        logging.info("Finished counting clicks for %d content sources." % (len(cs_clicks), ))
        domain_clicks.update(cs_clicks)  
        return domain_clicks
        
        
class GlobalStatsUpdaterTwitterSearchRankTopX(GlobalStatsUpdater, GlobalStatsHistoryUpdaterIF):
    def __init__(self, processor, statsId, topX):
        GlobalStatsUpdater.__init__(self, processor=processor, statsId=statsId)
        self.topX = topX

    def executeImpl(self):
        self.total = CmpTwitterAcctStats.all().filter('searchRank > ', 0).filter('searchRank <= ', self.topX).count(limit=100000)
        
    @classmethod
    def channel_stats_counter_attr(cls):
        return 'searchRanks'
    
    @classmethod
    def channel_stats_padding_type(cls):
        return DailyStatsCounterIF.PADDING_OLD_VALUE
    
    def updateHistoryTotal(self, totalCounts, counts):
            for i in range(0, min(len(totalCounts), len(counts))):
                searchRank = counts[i]
                if searchRank and searchRank<=self.topX:
                    totalCounts[i] += 1
                

class GlobalStatsUpdaterTwitterSearchRankTop3(GlobalStatsUpdaterTwitterSearchRankTopX):
    def __init__(self, processor):
        GlobalStatsUpdaterTwitterSearchRankTopX.__init__(self, processor=processor, statsId=log_const.GLOBAL_STATS_TWITTER_SEARCH_RANK_TOP_3, topX=3)
        

class GlobalStatsUpdaterTwitterSearchRankTop20(GlobalStatsUpdaterTwitterSearchRankTopX):
    def __init__(self, processor):
        GlobalStatsUpdaterTwitterSearchRankTopX.__init__(self, processor=processor, statsId=log_const.GLOBAL_STATS_TWITTER_SEARCH_RANK_TOP_20, topX=20)
        

class GlobalStatsUpdaterKloutScoreXth(GlobalStatsUpdater, GlobalStatsHistoryUpdaterIF):
    def __init__(self, processor, statsId, theXth):
        GlobalStatsUpdater.__init__(self, processor=processor, statsId=statsId)
        self.theXth = theXth

    def executeImpl(self):
        results = CmpTwitterAcctStats.all().order('-latestKloutScore').fetch(limit=1, offset=self.theXth-1)
        if len(results)==0:
            self.total = 0
        else:
            self.total = results[0].latestKloutScore
        
    @classmethod
    def channel_stats_counter_attr(cls):
        return 'kloutScores'
    
    @classmethod
    def channel_stats_padding_type(cls):
        return DailyStatsCounterIF.PADDING_OLD_VALUE
    
    def updateHistoryTotal(self, totalCounts, counts):
            for i in range(0, min(len(totalCounts), len(counts))):
                if totalCounts[i]:
                    totalCounts[i].append(counts[i])
                else:
                    totalCounts[i] = [counts[i]]

    def normalizeHistoryTotal(self, totalCounts):
        for i in range(0, len(totalCounts)):
            scores = totalCounts[i]
            if scores and len(scores)>=self.theXth:
                scores.sort()
                totalCounts[i] = scores[-self.theXth]
            else:
                totalCounts[i] = 0
                

class GlobalStatsUpdaterKloutScore100th(GlobalStatsUpdaterKloutScoreXth):
    def __init__(self, processor):
        GlobalStatsUpdaterKloutScoreXth.__init__(self, processor=processor, statsId=log_const.GLOBAL_STATS_KLOUT_SCORE_100TH, theXth=100)
        

class GlobalStatsUpdaterKloutScore1000th(GlobalStatsUpdaterKloutScoreXth):
    def __init__(self, processor):
        GlobalStatsUpdaterKloutScoreXth.__init__(self, processor=processor, statsId=log_const.GLOBAL_STATS_KLOUT_SCORE_1000TH, theXth=1000)
        

class GlobalStatsUpdaterCounterBase(GlobalStatsUpdater):
    def __init__(self, processor, statsId, total=0):
        GlobalStatsUpdater.__init__(self, processor=processor, statsId=statsId)
        self.total = total
        

class GlobalStatsUpdaterRetweetsAll(GlobalStatsUpdaterCounterBase, GlobalStatsHistoryUpdaterIF):
    def __init__(self, processor, total=0):
        GlobalStatsUpdaterCounterBase.__init__(self, processor=processor, statsId=log_const.GLOBAL_STATS_RETWEETS_ALL, total=total)

    @classmethod
    def channel_stats_counter_attr(cls):
        return 'retweetCounts'
    

class GlobalStatsUpdaterRetweetsNonOrganic(GlobalStatsUpdater):
    def __init__(self, processor):
        GlobalStatsUpdater.__init__(self, processor=processor, statsId=log_const.GLOBAL_STATS_RETWEETS_NONORGANIC)
        
    def executeImpl(self):
        self.total = self.day_count(self.dayStart)
        
    @classmethod        
    def day_count(self, dayStart):
        dayEnd = dayStart + datetime.timedelta(days=1)
        return Retweet.all().filter('modifiedTime >= ', dayStart).filter('modifiedTime < ', dayEnd).count(limit=100000)


class GlobalStatsUpdaterRetweetsDupArticles(GlobalStatsUpdater):
    def __init__(self, processor):
        GlobalStatsUpdater.__init__(self, processor=processor, statsId=log_const.GLOBAL_STATS_RETWEETS_DUP_ARTICLES)
        
    def executeImpl(self):
        self.total = self.day_count(self.dayStart)
        
    @classmethod        
    def day_count(self, dayStart):
        dayEnd = dayStart + datetime.timedelta(days=1)
        return Retweet.all().filter('cat', camp_const.RT_CAT_DUPLICATED_URL).filter('modifiedTime >= ', dayStart).filter('modifiedTime < ', dayEnd).count(limit=100000)


class GlobalStatsUpdaterRetweetsTopDeals(GlobalStatsUpdater):
    def __init__(self, processor):
        GlobalStatsUpdater.__init__(self, processor=processor, statsId=log_const.GLOBAL_STATS_RETWEETS_TOP_DEALS)
        
    def executeImpl(self):
        self.total = self.day_count(self.dayStart)
        
    @classmethod        
    def day_count(self, dayStart):
        dayEnd = dayStart + datetime.timedelta(days=1)
        return Retweet.all().filter('cat', camp_const.RT_CAT_ADS_TOP_DEAL).filter('modifiedTime >= ', dayStart).filter('modifiedTime < ', dayEnd).count(limit=100000)


class GlobalStatsUpdaterMentionsAll(GlobalStatsUpdaterCounterBase, GlobalStatsHistoryUpdaterIF):
    def __init__(self, processor, total=0):
        GlobalStatsUpdaterCounterBase.__init__(self, processor=processor, statsId=log_const.GLOBAL_STATS_MENTIONS_ALL, total=total)

    @classmethod
    def channel_stats_counter_attr(cls):
        return 'mentionCounts'


class GlobalStatsProcessor(api_base.AssociateModelBaseProcessor):
    def __init__(self):
        api_base.AssociateModelBaseProcessor.__init__(self)
        self.cmpUsers = None
        self.cmpUserMapById = {}
        self.now = datetime.datetime.utcnow()
        uspacificnow = ctz_util.to_uspacific(self.now)
        uspacificDayEnd = datetime.datetime(year=uspacificnow.year, month=uspacificnow.month, day=uspacificnow.day, tzinfo=uspacificnow.tzinfo)
        utcDayEnd = ctz_util.to_utc(uspacificDayEnd)
        self.dayEnd = datetime.datetime(year=utcDayEnd.year, month=utcDayEnd.month, day=utcDayEnd.day, hour=utcDayEnd.hour)
        self.dayStart = self.dayEnd - datetime.timedelta(days=1)
        self.statsDate = uspacificnow.date() - datetime.timedelta(days=1)

    def getModel(self):
        return GlobalStats
    
    def query_base(self, **kwargs):
        return self.getModel().all()
    
    @classmethod
    def supportedOperations(cls):
        return ImmutableSet([api_const.API_O_CRON_EXECUTE, api_const.API_O_EXECUTE])
    
    def cron_execute(self, params):
        op = params.get('op', None)
        if op:
            if op=='clean':
                deferred.defer(self.__class__._deferred_clean)
            if op=='update_history_retweets_organic':
                self._update_global_stats_retweets_organic()
            if op=='update_history_retweets_dup_articles':
                deferred.defer(self.__class__._deferred_update_history_retweets_dup_articles)
            if op=='update_history_retweets_mentions_all':
                days = int(params.get('days', 7))
                deferred.defer(self.__class__._deferred_update_history_retweets_mentions_all, days=days)
            return
        cmpCounterUpdatingStatuses = GlobalStatsUpdaterCmpCounterUpdate.updating_statuses(self)
        cmpCounterUpdatedToday = all(cmpCounterUpdatingStatuses)
        deferred.defer(self.__class__._deferred_execute, cmpCounterUpdatedToday=cmpCounterUpdatedToday)
        if not cmpCounterUpdatedToday:
            for userHashCode in range(0, User.USER_HASH_SIZE):
                if not cmpCounterUpdatingStatuses[userHashCode]:
                    deferred.defer(self.__class__._deferred_execute_cmp_counter_updater, userHashCode=userHashCode, queueName="cmpcounterupdater")
        
    def execute(self, params):
        op = params.get('op', None)
        if op:
            if op=='get_all_chids':
                return self.get_all_chids()

    def get_all_chids(self):
        gstats = GlobalStats.get_or_insert_by_id(log_const.GLOBAL_STATS_CMP_TWITTER_ACCT_BASIC_INFO)
        return gstats.get_counter_info()[1]
        
    def get_once_suspended_chids(self):
        gstats = GlobalStats.get_or_insert_by_id(log_const.GLOBAL_STATS_ONCE_SUSPENDED_CHIDS)
        return gstats.get_counter_info()[1]
        
    @classmethod
    def _deferred_execute_cmp_counter_updater(cls, userHashCode):
        context.set_deferred_context(deploy=deploysns)
        return GlobalStatsUpdaterCmpCounterUpdate(processor=cls(), userHashCode=userHashCode).execute()

    @classmethod
    def _deferred_execute(cls, cmpCounterUpdatedToday):
        context.set_deferred_context(deploy=deploysns)
        return cls()._execute(cmpCounterUpdatedToday)

    def _execute(self, cmpCounterUpdatedToday):
        if not SystemStatusMonitor.acquire_lock(cont_const.MONITOR_GLOBAL_STATS_UPDATE, preempt=7200):
            return
        try:
            self._execute_impl(cmpCounterUpdatedToday)
        except:
            logging.exception("Unexpected error when executing global stats updates!")
        SystemStatusMonitor.release_lock(cont_const.MONITOR_GLOBAL_STATS_UPDATE)

    def _execute_impl(self, cmpCounterUpdatedToday):
        GlobalStatsUpdaterCmpTwitterAcctBasicInfo(processor=self).execute()
        GlobalStatsUpdaterOnceSuspendedChids(processor=self).execute()
        GlobalStatsUpdaterCmpAcctNoTopics(processor=self).execute()
        GlobalStatsUpdaterTotalClicks(processor=self).execute()
        GlobalStatsUpdaterTotalPosts(processor=self).execute()
        GlobalStatsUpdaterTotalUniqueUrls(processor=self).execute()
        GlobalStatsUpdaterCmpClicks(processor=self).execute()
        GlobalStatsUpdaterCmpPosts(processor=self).execute()
        GlobalStatsUpdaterCmpClickedUrls(processor=self).execute()
        GlobalStatsUpdaterCmpAccts(processor=self).execute()
        GlobalStatsUpdaterCmpActiveFeCampaigns(processor=self).execute()
#        GlobalStatsUpdaterTwitterSearchRankTop3(processor=self).execute()
#        GlobalStatsUpdaterTwitterSearchRankTop20(processor=self).execute()
#        GlobalStatsUpdaterRetweetsNonOrganic(processor=self).execute()
#        GlobalStatsUpdaterRetweetsDupArticles(processor=self).execute()
#        GlobalStatsUpdaterRetweetsTopDeals(processor=self).execute()
        GlobalStatsUpdaterContentSource(processor=self).execute()
        if cmpCounterUpdatedToday:
            GlobalStatsUpdaterCmpFollowers(processor=self).execute()
#            GlobalStatsUpdaterCmpHashtags(processor=self).execute()
#            GlobalStatsUpdaterKloutScore100th(processor=self).execute()
#            GlobalStatsUpdaterKloutScore1000th(processor=self).execute()
#             deferred.defer(GlobalStatsUpdaterDealStats.deferred_execute)
            _channel_global_stats_combo_updated = self._channel_global_stats_combo_updated()
            _topic_stats_combo_updated = self._topic_stats_combo_updated()
            if _channel_global_stats_combo_updated and _topic_stats_combo_updated:
                pass
            else:  
                all_channel_stats, all_channel_stats_counters = CmpTwitterAcctStatsProcessor().get_all_stats_and_counters()
                if not _channel_global_stats_combo_updated:
                    self._channel_global_stats_combo_update(all_channel_stats_counters)
                if not _topic_stats_combo_updated:
                    self._topic_stats_update_combo(all_channel_stats, all_channel_stats_counters)

    def _channel_global_stats_combo_updated(self):
#        gstats = GlobalStats.get_or_insert_by_id(log_const.GLOBAL_STATS_MENTIONS_ALL)
#        statsDate = gstats.get_counter_info()[0] 
#        if statsDate and statsDate>=self.statsDate:
#            logging.info("The channel global stats combo is already updated today!")
#            return True
#        return False
        return True

    def _channel_global_stats_combo_update(self, all_channel_stats_counters):
        if len(all_channel_stats_counters)==0:
            return
        totalRetweets = 0
        totalMentions = 0
        for statsCounter in all_channel_stats_counters:
            rtDate, rtCounts = statsCounter.getRetweetCounts()
            if rtDate==self.statsDate and len(rtCounts)>0 and rtCounts[-1]:
                totalRetweets += rtCounts[-1]
            mentionDate, mentionCounts = statsCounter.getMentionCounts()
            if mentionDate==self.statsDate and len(mentionCounts)>0 and mentionCounts[-1]:
                totalMentions += mentionCounts[-1]
        GlobalStatsUpdaterRetweetsAll(processor=self, total=totalRetweets).execute()
        GlobalStatsUpdaterMentionsAll(processor=self, total=totalMentions).execute()
        GlobalStatsUpdaterRetweetsAll(processor=self).updateHistory(all_channel_stats_counters, 7)
        GlobalStatsUpdaterMentionsAll(processor=self).updateHistory(all_channel_stats_counters, 7)
        self._update_global_stats_retweets_organic()
        
    def _update_global_stats_retweets_organic(self):
        retweets_nonorganic_stats = GlobalStats.get_or_insert_by_id(log_const.GLOBAL_STATS_RETWEETS_NONORGANIC)
        retweets_organic_stats = GlobalStats.get_or_insert_by_id(log_const.GLOBAL_STATS_RETWEETS_ORGANIC)
        retweets_all_stats = GlobalStats.get_or_insert_by_id(log_const.GLOBAL_STATS_RETWEETS_ALL)
        nonorganic_date, nonorganic_counts = retweets_nonorganic_stats.get_counter_info()
        if nonorganic_date != self.statsDate:
            logging.critical("Global stats RetweetsNonOrganic is not updated! %s, %s" % (nonorganic_date, self.statsDate))
        retweets_organic_stats.set_counter_info(0, self.statsDate)
        retweets_all_stats.set_counter_info(nonorganic_counts[-1], self.statsDate)
        db.put([retweets_organic_stats, retweets_all_stats])

#    @classmethod
#    def _deferred_update_history_retweets_mentions_all(cls, days):
#        context.set_deferred_context(deploy=deploysns)
#        return cls()._updateHistoryRetweetsMentionsAll(days)
#
#    def _updateHistoryRetweetsMentionsAll(self, days):
#        allStatsCounters = CmpTwitterAcctStatsProcessor().get_all_channel_stats_counters()
#        if len(allStatsCounters)==0:
#            return
#        GlobalStatsUpdaterRetweetsAll(processor=self).updateHistory(allStatsCounters, days)
#        GlobalStatsUpdaterMentionsAll(processor=self).updateHistory(allStatsCounters, days)
#        GlobalStatsUpdaterTwitterSearchRankTop3(processor=self).updateHistory(allStatsCounters, days)
#        GlobalStatsUpdaterTwitterSearchRankTop20(processor=self).updateHistory(allStatsCounters, days)
#        GlobalStatsUpdaterKloutScore100th(processor=self).updateHistory(allStatsCounters, days)
#        GlobalStatsUpdaterKloutScore1000th(processor=self).updateHistory(allStatsCounters, days)
        
    @classmethod
    def _deferred_update_history_retweets_dup_articles(cls):
        context.set_deferred_context(deploy=deploysns)
        return cls()._updateHistoryRetweetsDupArticles()

    def _updateHistoryRetweetsDupArticles(self):
        dayStart = self.dayStart
        counts = []
        while True:
            dayCount = GlobalStatsUpdaterRetweetsNonOrganic.day_count(dayStart)
            if dayCount==0:
                break
            counts.append(dayCount)
            dayStart = dayStart - datetime.timedelta(days=1)
        if len(counts)<30:
            counts += [0]*(30-len(counts))
        counts.reverse()
        stats = GlobalStats.get_or_insert_by_id(log_const.GLOBAL_STATS_RETWEETS_NONORGANIC)
        stats.info = GlobalStats.text(self.statsDate, counts)
        stats.put()

    def _topic_stats_combo_updated(self):
        topic_keys = TopicCacheMgr.get_all_level_1_topic_key_set()
        tstats_map = dict([(topic_key, TopicStats.get_or_insert_by_topic_key(topic_key)) for topic_key in topic_keys])
        updated = all([tstats.updd == self.statsDate for tstats in tstats_map.values()])
        if updated:
            logging.info("All %d top level topic stats are already updated today!" % len(topic_keys))
            return True
        return False

    def _topic_stats_update_combo(self, all_channel_stats, all_channel_stats_counters):
        topic_keys = TopicCacheMgr.get_all_level_1_topic_key_set()
        tstats_map = dict([(topic_key, TopicStats.get_or_insert_by_topic_key(topic_key)) for topic_key in topic_keys])
        logging.info("Updating topic stats for %d top level topics: %s " % (len(topic_keys), topic_keys))
        for tstats in tstats_map.values():
            tstats.reset()
            tstats.updd = self.statsDate
#        tstats_counter_map = dict([(topic_key, TopicStatsCounter.get_or_insert_by_topic_key(topic_key)) for topic_key in topic_keys])
#        for tstats_counter in tstats_counter_map.values():
#            tstats_counter.reset()
        cstats_map = dict([(cstats.chid, cstats) for cstats in all_channel_stats])
#        cstats_counter_map = dict([(counter.chid, counter) for counter in all_channel_stats_counters])
        topic_map = TopicCacheMgr.get_or_build_all_topic_map()
        all_channels = TAccountProcessor().execute_query_all(params={'deleted':False, 'isContent':True})
        updated_cstats = []
        for channel in all_channels:
            chid = int(channel.keyNameStrip())
            cstats = cstats_map.get(chid, None)
            if cstats is None:
                continue
            topic_info = []
            ancestors = []
            for topic_key in channel.topics:
                topic = topic_map.get(topic_key, None)
                if topic is None:
                    continue
                topic_info.append((topic_key, topic.name))
                ancestors.extend(topic.ancestorTopics)
            ancestors = list(set(ancestors))
            ancestors.sort()
            updated = False
            if cstats.topicInfo != unicode(topic_info) or cstats.topic_ancestors_changed(ancestors):
                cstats.topicInfo = unicode(topic_info)
                cstats.ancestorTopics = ancestors
                updated = True
            if cstats.sync_search_term(): updated = True
            if updated: updated_cstats.append(cstats)
        db_base.put(updated_cstats)
        for cstats in all_channel_stats:
            chid = cstats.chid
            topic_info = eval(cstats.topicInfo) if cstats.topicInfo else []
            ancestor_topic_keys = []
            for item in topic_info:
                topic_key = item[0]
                topic = topic_map.get(topic_key, None)
                if topic: 
                    ancestor_topic_keys.append(topic_key)
                    ancestor_topic_keys.extend(topic.ancestorTopics)
            level_1_ancestors = topic_keys.intersection(set(ancestor_topic_keys))
            for ancestor in level_1_ancestors:
                tstats = tstats_map[ancestor]
                tstats.aggregate_one_cstats(cstats)
        db_base.put(tstats_map.values())
        logging.info("Finished updating topic stats for %d top level topics: %s " % (len(topic_keys), topic_keys))
    
    @classmethod
    def _deferred_clean(cls):
        context.set_deferred_context(deploy=deploysns)
        return cls()._clean()

    def _clean(self):
        pass

