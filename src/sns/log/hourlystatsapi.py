import datetime
import logging
from sets import ImmutableSet

import context, deploysns
from common.utils import url as url_util, timezone as ctz_util
from common.utils import datetimeparser
from common.content.trove import consts as trove_const
from sns.serverutils import deferred
from sns.core.core import SystemStatusMonitor
from sns.core import base as db_base
from sns.api import consts as api_const
from sns.api import base as api_base
from sns.cont import consts as cont_const
from sns.cont import api as cont_api
from sns.url.models import GlobalUrl, GlobalUrlCounter
#from sns.camp import consts as camp_const
from sns.post.models import SPost
from sns.log import consts as log_const
from sns.log.models import HourlyStats, ContentSourceHourlyStats


class HourlyStatsUpdater():
    def __init__(self, processor=None, statsId=None, stats=None):
        self.processor = processor
        self.hourStart = self.processor.start_hour
        self.hourEnd = None
        self.statsId = statsId
        self.statsInfo = None
        self.has_error = False
        self.total = None
        if stats:
            self.stats = stats
        else:
            self.stats = HourlyStats.get_or_insert_by_id(self.statsId)

    def execute(self):
        self.sync()
        if self.uptodate(): return True
        self.preExecute()
        self.executeImpl()
        self.postExecute()
        return self.has_error

    def sync(self):
        self.has_error = False
        self.total = None
        statsDate, self.statsInfo = self.stats.get_counter_info()
        if statsDate and statsDate < self.hourStart:
            self.statsInfo = None
        elif statsDate and statsDate >= self.hourStart:
            self.hourStart = statsDate + datetime.timedelta(hours=1)
        self.hourEnd = self.hourStart + datetime.timedelta(hours=1)

    def uptodate(self):
        if self.hourStart and self.hourStart>=self.processor.end_hour:
            logging.info("The hourly stats %d is already updated for last hour %s!" % (self.statsId, self.hourStart))
            return True
        else:
            logging.debug("The hourly stats %d is updated for %s!" % (self.statsId, self.hourStart))
            return False

    def preExecute(self):
        pass
    
    def executeImpl(self):
        pass

    def postExecute(self):
        if self.has_error:
            logging.warn("Failed updating hourly stats %d because of error." % self.statsId)
            return
        self.update_info()
        self.stats.put()
        logging.info("Finished updating hourly stats %d." % self.statsId)

    def update_info(self):
        self.stats.set_counter_info(self.total, self.hourStart)

    def _logException(self):
        logging.exception("Unexpected error when updating hourly stats %d:" % self.statsId)


class HourlyStatsUpdaterNonCounter(HourlyStatsUpdater):
    def __init__(self, processor=None, statsId=None, stats=None):
        HourlyStatsUpdater.__init__(self, processor=processor, statsId=statsId, stats=stats)

    def update_info(self):
        self.stats.set_non_counter_info(self.hourStart, self.statsInfo)


class HourlyStatsUpdaterContentSource(HourlyStatsUpdaterNonCounter):
    def __init__(self, processor):
        HourlyStatsUpdaterNonCounter.__init__(self, processor=processor, statsId=log_const.HOURLY_STATS_CONTENT_SOURCE)
        self._trove_hosted_map = {} # Cache trove hosted status for each url

    @classmethod
    def deferred_execute(cls):
        context.set_deferred_context(deploy=deploysns)
        return cls(processor=HourlyStatsProcessor()).execute()

    def preExecute(self):
        pass
    
    def executeImpl(self):
        self.has_error = not self._execute_impl()
        self.statsInfo = str([])

    def _execute_impl(self):
        success = False
        try:
            """ Phase 1 - Collect domain post counts """
            domain_posts = self._collect_post_counts()             
            
            """ Phase 2 - Collect domain click counts """
            domain_clicks = self._collect_click_counts()             

            """ Phase 3 - Update all domain stats """
            all_updated_domains = domain_posts.keys()
            all_updated_domains.extend(domain_clicks.keys()) 
            all_updated_domains = set(all_updated_domains) 
            logging.info("Started updating total %d domain stats..." % len(all_updated_domains))
            update_list = []
            for domain in all_updated_domains:
                csstats = ContentSourceHourlyStats.get_or_insert_by_name(domain)
                csstats.posts = domain_posts.get(domain, 0)
                csstats.clicks = domain_clicks.get(domain, 0)
                csstats_counter = csstats.get_or_insert_counter()
                csstats_counter.setPostCount(csstats.posts, self.hourStart)
                csstats_counter.setClickCount(csstats.clicks, self.hourStart)
                csstats.totalPosts = csstats_counter.totalPosts()
                csstats.totalClicks = csstats_counter.totalClicks()
                csstats.updd = self.hourStart
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
        query = SPost.all().filter('modifiedTime >= ', self.hourStart).filter('modifiedTime < ', self.hourEnd)#.filter('state', camp_const.EXECUTION_STATE_FINISH)
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
            if len(posts) < LIMIT:
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
        logging.info("Started counting clicks from global URL counters...")
        domain_clicks = {}
        total_clicks = 0
        trove_hosted_clicks = 0
        trove_unhosted_clicks = 0
        LIMIT = 500
        HASH_FACTOR = 47
        url_hash = [set([])] * HASH_FACTOR
        cursor = None
        total = 0
        query = GlobalUrlCounter.all().filter('modifiedTime >= ', self.hourStart)
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
                logging.info("Counted total %d global URL counters." % total)
            if len(url_counters) < LIMIT:
                break 
            cursor = query.cursor()
        logging.info("Finished counting total %d global URL counters into %d root domains." % (total, len(domain_clicks)))
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
        
        
class HourlyStatsProcessor(api_base.AssociateModelBaseProcessor):
    def __init__(self):
        api_base.AssociateModelBaseProcessor.__init__(self)
        now = datetime.datetime.utcnow()
        self.end_hour = datetimeparser.truncate_2_hour(now)
        uspacificnow = ctz_util.to_uspacific(now)
        self.start_hour = datetimeparser.date_2_datetime(uspacificnow.date() - datetime.timedelta(days=1))

    def getModel(self):
        return HourlyStats
    
    def query_base(self, **kwargs):
        return self.getModel().all()
    
    @classmethod
    def supportedOperations(cls):
        return ImmutableSet([api_const.API_O_CRON_EXECUTE, api_const.API_O_ADMIN])
    
    def cron_execute(self, params):
        op = params.get('op', None)
        if op:
            if op=='clean':
                deferred.defer(self.__class__._deferred_clean)
            return
        deferred.defer(self.__class__._deferred_execute)
        
    @classmethod
    def _deferred_execute(cls):
        context.set_deferred_context(deploy=deploysns)
        if not SystemStatusMonitor.acquire_lock(cont_const.MONITOR_HOURLY_STATS_UPDATE, preempt=900):
            return
        try:
            cls()._execute_impl()
        except:
            logging.exception("Unexpected error when executing hourly stats updates!")
        SystemStatusMonitor.release_lock(cont_const.MONITOR_HOURLY_STATS_UPDATE)

    def _execute_impl(self):
        expire_time = datetime.datetime.now() + datetime.timedelta(minutes=5)
        csstats_updater = HourlyStatsUpdaterContentSource(processor=self)
        has_error = False
        while not has_error and datetime.datetime.now() < expire_time:
            if csstats_updater.execute(): has_error = True

    @classmethod
    def _deferred_clean(cls):
        context.set_deferred_context(deploy=deploysns)
        return cls()._clean()

    def _clean(self):
        pass

