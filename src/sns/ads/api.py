import logging
import random
from sets import ImmutableSet


import context, deploysns
from common import consts as common_const
from common.utils import timezone as ctz_util
from common.utils import url as url_util
from common.utils import misc as misc_util
from common.utils import math as math_util
from common.content.trove import consts as trove_const
from common.content.trove import api as trove_api
from common.content import feedfetcher
from sns.serverutils import deferred
from sns.core import core as db_core
from sns.api import consts as api_const
from sns.api.base import BaseProcessor
from sns.chan.models import TAccount
from sns.camp import consts as camp_const
from sns.camp.models import Retweet
from sns.url.models import GlobalUrl, GlobalShortUrl
from sns.deal.models import TopDeal
from sns.cont import consts as cont_const
from sns.cont.feedsources import CSFSFeedFetcher
from sns.cont.models import TopicCSContent, Topic
from sns.cont import api as cont_api
from sns.cont.topic.api import TopicCacheMgr


class AdsMgr():
    DAILY_LIMIT = 0
    CSKEY = None
    CONTENT_INTERVAL = 10
    CONTENT_CUTOFF_HOURS = common_const.CONTENT_CUTOFF_HOURS
    L1_TOPIC_MAP = {}
    def __init__(self, channel=None, topics=[], history=[]):
        self.channel = channel
        self.topics = topics
        self.history = history
        self.url_history = [eval(tup_str)[1] for tup_str in self.history]
        self.now = ctz_util.uspacificnow()
        self._l1_topic_key_sns = None
        self._l1_topic_key_advertiser = None
        self._sns_topic_matches_advertiser = None
        
    @classmethod
    def advertiser_name(cls):
        return cls.CSKEY

    @classmethod
    def get_monitor_key(cls):
        return "monitor_ads_%s" % '_'.join(cls.CSKEY.split('.')) 

    @classmethod
    def is_serving_ads(cls):
        return False 
            
    def new_count_info(self, date=None, hour=None, date_count=0, hour_count=0):
        date_str = str(date if date else self.now.date())
        hour = hour if hour else self.now.hour
        return {'date': date_str,
                'hour': hour, 
                'date_count': date_count,
                'hour_count': hour_count,
                }
        
    def get_count_info(self):
        monitor = db_core.SystemStatusMonitor.get_system_monitor(self.get_monitor_key())
        try:
            if monitor and monitor.info:
                count_info = eval(monitor.info)
                if count_info['date'] != str(self.now.date()):
                    return self.new_count_info()
                elif count_info['hour'] != self.now.hour:
                    count_info['hour'] = self.now.hour
                    count_info['hour_count'] = 0
                return count_info
        except:
            logging.exception("Ads: unexpected error when getting ads count info.")
        return self.new_count_info()
    
    def set_count_info(self, count_info):
        monitor = db_core.SystemStatusMonitor.get_system_monitor(self.get_monitor_key())
        monitor.info = unicode(count_info)
        db_core.SystemStatusMonitor.set_system_monitor(monitor)

    @classmethod
    def hour_limit(cls):
        return cls.DAILY_LIMIT / 24 + 1 
            
    def over_limit(self, count_info):
        return count_info['date_count'] >= self.DAILY_LIMIT or count_info['hour_count'] >= self.hour_limit() 
        
    def enough_content_interval(self):
        if not self.url_history or len(self.url_history) < self.CONTENT_INTERVAL:
            return False
        url_history = self.url_history[-self.CONTENT_INTERVAL:]
        for url in url_history:
            if cont_api.Domain2CSProcessor().get_cskey_by_url(url, context_sensitive=False) == self.CSKEY:
                logging.debug("Ads: #%s content tweeted recently." % self.advertiser_name())
                return False
        return True
        
    def get_ads(self):
        try:
            if not self.is_serving_ads():
                return None
            if not self.enough_content_interval():
                logging.debug("Ads: not enough content interval.")
                return None
            if not self.sns_topic_matches_advertiser():
                logging.debug("Ads: advertiser #%s doesn't match topics %s." % (self.advertiser_name(), self.topics_str()))
                return None
            count_info = self.get_count_info()
            if self.over_limit(count_info):
                logging.debug("Ads: over ads limit.")
                return None
            ads = self.execute_get_ads()
            if ads:
                count_info['date_count'] += 1
                count_info['hour_count'] += 1
                self.set_count_info(count_info)
                logging.info("Ads: qualified a #%s tweet for %s. %s." % (self.advertiser_name(), self.channel_topics_str(), count_info))
                return ads
            else:
                return None
        except:
            logging.exception("Ads: error when getting ads!")
        return None

    def execute_get_ads(self):
        if not self.topics:
            return None
        query = TopicCSContent.all().filter('cskey', self.CSKEY).filter('topics', self.topics[0])
        count = query.count(100000)
        if count == 0:
            logging.debug("Ads: no #%s content found for topic %s." % (self.advertiser_name(), self.topics[0]))
            return None
        offset = random.randint(0, count - 1)
        topic_csc = query.fetch(limit=1, offset=offset)
        if not topic_csc:
            return None
        topic_csc = topic_csc[0]
        contents = topic_csc.get_contents(contcutoffhours=self.CONTENT_CUTOFF_HOURS)
        if not contents:
            return None
        content = contents[self.pick_1_from_n(len(contents))]
        return feedfetcher.FeedEntry(content['title'],
                                     url = content['url'],
                                     title = self.customize_title(content['title']),
                                     keywords = content['keywords'],
                                     updated = content['publish_date'],
                                     summary = content['description'], 
                                     )
    
    def pick_1_from_n(self, n):
        seed = random.randint(0, n * 1000 - 1)
        fraction = 1.0 * seed / n / 1000
        fraction = fraction * fraction
        index = int(fraction * n)
        if index == n:
            index = n - 1
        logging.info("Ads: picked index %d out of %d entries. #%s %s" % (index, n, self.advertiser_name(), self.channel_topics_str()))
        return index
    
    def l1_topic_key_sns(self):
        if not self._l1_topic_key_sns:
            self._l1_topic_key_sns = self.l1_topic_key_sns_impl()
        return self._l1_topic_key_sns 

    def l1_topic_key_advertiser(self):
        if not self._l1_topic_key_advertiser:
            self._l1_topic_key_advertiser = self.l1_topic_key_advertiser_impl()
        return self._l1_topic_key_advertiser 

    def sns_topic_matches_advertiser(self):
        if self._sns_topic_matches_advertiser is None:
            self._sns_topic_matches_advertiser = self.sns_topic_matches_advertiser_impl()
        return self._sns_topic_matches_advertiser 
        
    def l1_topic_key_sns_impl(self):
        ancestor_lists = []
        for topic_key in self.topics:
            topic = Topic.get_by_topic_key(topic_key)
            if not topic:
                continue
            ancestor_lists.append(topic.ancestors_plus_self())
        ancestors = misc_util.list_dedupe_preserve_order(ancestor_lists)
        try:
            all_l1_topic_keys = TopicCacheMgr.get_all_level_1_topic_key_set()
            for ancestor in ancestors:
                if ancestor not in all_l1_topic_keys:
                    continue
                return ancestor
        except:
            logging.exception("Error when getting sns target topic key for #%s for topics %s!" % (self.advertiser_name(), self.topics_str()))
            return None

    def l1_topic_key_advertiser_impl(self):
        return self.l1_topic_key_sns()

    def sns_topic_matches_advertiser_impl(self):
        return not self.l1_topic_key_advertiser()
        
    def topics_str(self):
        return "[%s]" % ', '.join(self.topics if self.topics else [])

    def channel_str(self):
        return "@%s(%d)" % (self.channel.name, self.channel.chid_int()) if self.channel else ""

    def channel_topics_str(self):
        return "%s %s" % (self.channel_str(), self.topics_str())

    @classmethod
    def customize_title(cls, title):
        return title

    @classmethod
    def analytics_params_sns(cls, params={}):
        pass
    
    def analytics_params_advertiser(self):
        return  {'utm_source': 'snsanalytics', 'utm_medium': 'twitter', 'utm_campaign': 'Contact+SNS+For+More+Referrer'}

    def get_advertised_url(self, url):
        return url_util.add_params_2_url(url, self.analytics_params_advertiser()) 
    
    
class HarkAdsMgr(AdsMgr):
    DAILY_LIMIT = 1000
    CONTENT_CUTOFF_HOURS = 0
    CSKEY = cont_const.CS_HARK
    
    def sns_topic_matches_advertiser_impl(self):
        return True
        
    @classmethod
    def customize_title(cls, title):
        index = title.find("Sound Clip")
        if index > 0:
            title = title[:index]
        return "#snsaudio %s" % title

    def analytics_params_advertiser(self):
        return  {'utm_source': 'snsana', 'utm_medium': 'cpc', }

    @classmethod
    def add_analytics_params_for_orginal_url(cls, url):
        if url_util.root_domain(url) != cls.advertiser_name():
            return url
        return url_util.add_params_2_url(url, {'utm_source': 'snsana', 'utm_medium': 'cpc', })


class ExaminerAdsMgr(AdsMgr):
    DAILY_LIMIT = 2000
    CONTENT_INTERVAL = 5
    CSKEY = cont_const.CS_EXAMINER
    L1_TOPIC_MAP = {
        'us': 'metro',
        'regional': 'world',
        'hobbies': 'hobby',
        'outside': 'other',
        }
    L2_TOPIC_MAP = {
        'celebrities': 'celebrity',
        }

    def l1_topic_key_advertiser_impl(self):
        ancestor_lists = []
        for topic_key in self.topics:
            topic = Topic.get_by_topic_key(topic_key)
            if not topic:
                continue
            ancestor_lists.append(topic.ancestors_plus_self())
        ancestors = misc_util.list_dedupe_preserve_order(ancestor_lists)
        for ancestor in ancestors:
            if self.L2_TOPIC_MAP.has_key(ancestor):
                return self.L2_TOPIC_MAP[ancestor]
        for ancestor in ancestors:
            if self.L1_TOPIC_MAP.has_key(ancestor):
                return self.L1_TOPIC_MAP[ancestor]
        try:
            all_l1_topic_keys = TopicCacheMgr.get_all_level_1_topic_key_set()
            for ancestor in ancestors:
                if ancestor not in all_l1_topic_keys:
                    continue
                if self.L1_TOPIC_MAP.has_key(ancestor):
                    return self.L1_TOPIC_MAP[ancestor]
                else:
                    return ancestor
        except:
            logging.exception("Error when getting target topic key for advertiser %s for topics '%s'!" % (self.advertiser_name(), ', '.join(self.topics) if self.topics else ''))
            return None

    def analytics_params_advertiser(self):
        l1_topic_key_advertiser = self.l1_topic_key_advertiser()
        return  {'cid': "RSS-sns-%s" % l1_topic_key_advertiser, } if l1_topic_key_advertiser else {}
    

class BleacherreportAdsMgr(AdsMgr):
    DAILY_LIMIT = 5000
    CONTENT_INTERVAL = 3
    CSKEY = cont_const.CS_BLEACHERREPORT
    L1_TOPIC_MAP = {}
    L2_TOPIC_MAP = {}

    def sns_topic_matches_advertiser_impl(self):
        return True
        
    def analytics_params_advertiser(self):
        return  {'utm_source': 'twitter.com', 'utm_medium': 'referral', 'utm_campaign': 'sitemap-snsanalytics'}


class JollyAdsMgr(AdsMgr):
    DAILY_LIMIT = 5000
    CONTENT_INTERVAL = 10
    CSKEY = cont_const.CS_JOLLY
    L1_TOPIC_MAP = {}
    L2_TOPIC_MAP = {}

    def sns_topic_matches_advertiser_impl(self):
        return False
        
    def analytics_params_advertiser(self):
        return  dict(utm_source='snsanalytics', 
                     utm_medium='display', 
                     utm_campaign='sns_jolly_tweet_%s' % self.campaign_identifier(),
                     )

    @classmethod
    def utm_campaign_sns(cls):
        return "jollychic.com %s" % cls.campaign_identifier()
        
    @classmethod
    def campaign_identifier(cls):
        return 'devel001' if context.is_dev_mode() else 'test001'
    

class WetpaintAdsMgr(AdsMgr):
    DAILY_LIMIT = 5000
    CONTENT_INTERVAL = 3
    CSKEY = cont_const.CS_WETPAINT
    L1_TOPIC_MAP = {}
    L2_TOPIC_MAP = {}

    def sns_topic_matches_advertiser_impl(self):
        return True
        
    def analytics_params_advertiser(self):
        return  {'utm_source': 'twitter.com', 'utm_medium': 'snsanalytics', 'utm_campaign': 'vrl'}


class TroveAdsMgr(AdsMgr):
    def get_advertised_url(self, url, mention_type=trove_const.MENTION_NONE):
        global_url = GlobalUrl.get_by_url(url)
        if not global_url or not global_url.is_trove_ingested():
            logging.error("URL is expected to be ingested! %s" % url)
            return url
        hosted = global_url.is_trove_hosted()
        utm_params = trove_api.get_utm_params(hosted, mention_type)
        return url_util.add_params_2_url(global_url.troveUrl, utm_params)


class TroveHostedAdsMgr(TroveAdsMgr):
    CSKEY = cont_const.CS_TROVE_HOSTED

    def analytics_params_advertiser(self):
        return  {'utm_source': trove_const.UTM_SOURCE, 'utm_medium': trove_const.UTM_MEDIUM, 'utm_campaign': trove_const.UTM_CAMPAIGN_HOSTED}


class TroveUnhostedAdsMgr(TroveAdsMgr):
    CSKEY = cont_const.CS_TROVE_UNHOSTED

    def analytics_params_advertiser(self):
        return  {'utm_source': trove_const.UTM_SOURCE, 'utm_medium': trove_const.UTM_MEDIUM, 'utm_campaign': trove_const.UTM_CAMPAIGN_UNHOSTED}


class TopDealAdsMgr(AdsMgr):
    DAILY_LIMIT = 1800
    CSKEY = cont_const.CS_DEALS
    
    def __init__(self, channel=None, topics=[], history=[]):
        AdsMgr.__init__(self, channel=channel, topics=topics, history=history)
        self.location = None
    
    def l1_topic_key_sns_impl(self):
        return 'us'

    def sns_topic_matches_advertiser_impl(self):
        all_us_top_keys = TopicCacheMgr.get_all_us_topic_key_set()
        if not all_us_top_keys or not self.topics:
            return False
        for topic_key in self.topics:
            if topic_key in all_us_top_keys:
                self.location = topic_key
                return True
        return False

    def execute_get_ads(self):
        if not self.l1_topic_key_sns():
            return None
        try:
            top_deal = None
            if self.location:
                top_deal = TopDeal.get_by_location_category(self.location)
                if top_deal is None:
                    logging.info("Ads: top deal doesn't exist for location %s. Trying to use the us_general top deal." % self.location)
                elif top_deal.tweetId is None:
                    logging.info("Ads: top deal is not tweeted yet. Trying to use the us_general top deal. %s" % top_deal)
            if top_deal is None or top_deal.tweetId is None:
                top_deal = TopDeal.get_by_location_category('us')
                if top_deal is None:
                    logging.error("Ads: the us_general top deal is not available.")
            if top_deal and top_deal.tweetId:
                if not top_deal.is_expiring():
                    tapi = self.channel.get_twitter_api()
                    retweets = Retweet.all().filter('cat', camp_const.RT_CAT_ADS_TOP_DEAL).filter('rtChid', self.channel.chid_int()).filter('tweetId', top_deal.tweetId).order('-modifiedTime').fetch(limit=1)
                    if retweets:
                        tapi.statuses.destroy(id=retweets[0].rtId)
                        logging.info("Ads: removed previous top deal retweet for %s." % self.channel_topics_str())
                    status = tapi.statuses.retweet(id=top_deal.tweetId) 
                    Retweet(cat=camp_const.RT_CAT_ADS_TOP_DEAL, tweetId=top_deal.tweetId, rtId=status['id'], rtChid=self.channel.chid_int()).put() 
                    return feedfetcher.FeedEntry(top_deal.title,
                                                 url = top_deal.url,
                                                 title = top_deal.title,
                                                 keywords = [],
                                                 updated = self.now,
                                                 summary = None,
                                                 extra = {'published': True} 
                                                 )
                else:
                    logging.info("Ads: top deal is expiring. %s" % str(top_deal))
        except:
            logging.exception("Ads: Failed qualifying #%s ads for %s!" % (self.advertiser_name(), self.channel_topics_str()))
        return None


class FeedSourceAdsMgr(AdsMgr):
    DAILY_LIMIT = 500
    CONTENT_INTERVAL = 5
    FSID = None

    @classmethod
    def is_serving_ads(cls):
        return True 
            
    def sns_topic_matches_advertiser_impl(self):
        return True
        
    def analytics_params_advertiser(self):
        return  {'utm_source': 'snsanalytics', 'utm_medium': 'twitter'}

    def execute_get_ads(self):
        feed_fetcher = CSFSFeedFetcher.get_feed_fetcher(self.CSKEY, self.FSID, self.topics)
        if not feed_fetcher:
            return None
        entries = feed_fetcher.fetch(self.history, limit=1)
        entry = entries[0] if entries else None
        if entry:
            logging.info("Found a feed source ads entry. %s" % str(entry))
        return entry
    

class TribuneBroadcastingAdsMgr(FeedSourceAdsMgr):
    CONTENT_INTERVAL = 2
    CSKEY = cont_const.CS_TRIBUNE_BROADCASTING
    FSID = cont_const.FEED_SOURCE_TRIBUNE_BROADCASTING

    @classmethod
    def is_serving_ads(cls):
        return False 
    

class SbnationAdsMgr(FeedSourceAdsMgr):
    CONTENT_INTERVAL = 2
    CSKEY = cont_const.CS_SBNATION
    FSID = cont_const.FEED_SOURCE_SBNATION
            
    @classmethod
    def is_serving_ads(cls):
        return False 
    

ADS_MGR_LIST = [TroveHostedAdsMgr, TroveUnhostedAdsMgr, JollyAdsMgr] #[SbnationAdsMgr, HarkAdsMgr, TopDealAdsMgr, ExaminerAdsMgr, BleacherreportAdsMgr, WetpaintAdsMgr]
ADS_MGR_MAP = dict([(ads_mgr_clazz.advertiser_name(), ads_mgr_clazz) for ads_mgr_clazz in ADS_MGR_LIST])


class AdsProcessor(BaseProcessor):
    def getModel(self):
        pass

    @classmethod
    def supportedOperations(cls):
        return ImmutableSet([api_const.API_O_CRON_EXECUTE, 
                           ]).union(BaseProcessor.supportedOperations())
                           
    @classmethod
    def get_ads(cls, topics=[], channel=None, user=None, history=[], limit=1):
        limit = 1 # always set to 1 for now
        if topics and channel and user:
            if user.is_deal():
                return []
            else:
                ads_entries = []
                for ads_mgr_clazz in ADS_MGR_LIST:
                    ads = ads_mgr_clazz(channel=channel, topics=topics, history=history).get_ads()
                    if ads:
                        ads_entries.append(ads)
                        if len(ads_entries) >= limit:
                            break
                return ads_entries
        return []

    @classmethod
    def get_ads_mgr(cls, url, channel=None, cskey=None, context_sensitive=True, fallback=False):
        if not cskey:
            cskey = cont_api.Domain2CSProcessor().get_cskey_by_url(url, context_sensitive=context_sensitive)
        ads_mgr_clazz = ADS_MGR_MAP.get(cskey, AdsMgr if fallback else None)
        topics = channel.topics if channel else []
        return ads_mgr_clazz(topics=topics, channel=channel) if ads_mgr_clazz else None

    @classmethod
    def add_analytics_params_advertiser(cls, url, channel, cskey=None, context_sensitive=True):
        url = url_util.remove_analytics_params(url)
        ads_mgr = cls.get_ads_mgr(url, channel=channel, cskey=cskey, context_sensitive=context_sensitive, fallback=True)
        if not ads_mgr:
            return url
        return ads_mgr.get_advertised_url(url)

    def execute_admin(self, params):
        op = params.get('op', None)
        if op == 'promote_tweet':
            surl = params.get('surl', None)
            uid = params.get('uid', None)
            if uid: uid = int(uid)
            if not surl or not uid:
                return "This operation requires surl and uid!"
            deferred.defer(self.__class__.deferred_promote_tweet_by_uid, surl, uid)
            return "Submitted promote_tweet operation correctly."
        return BaseProcessor.execute_admin(self, params)
    
    def cron_execute(self, params):
        return
    
    @classmethod
    def deferred_promote_tweet_by_uid(cls, surl, uid):
        context.set_deferred_context(deploy=deploysns)
        tweet_id = GlobalShortUrl.get_tweet_id_by_surl(surl)
        if not tweet_id:
            logging.error("Couldn't find tweet for surl %s!" % surl)
            return
        user = db_core.User.get_by_id(uid)
        channels = TAccount.get_user_channels(user, cmp_required=False)
        rt_count = 0
        fav_count = 0
        for channel in channels:
            try:
                tapi = channel.get_twitter_api()
                if math_util.true_by_percentage(80):
                    tapi.statuses.retweet(id=tweet_id)
                    rt_count += 1
                if math_util.true_by_percentage(70):
                    tapi.favorites.create(id=tweet_id)
                    fav_count += 1
            except:
                logging.exception("Unexpected exception while using channel %s to promote surl %s!" % (channel.chid_handle_uid_str(), surl))
        logging.info("Promoted surl %s with %d RTs and %d favorites using %s." % (surl, rt_count, fav_count, user.id_email_str()))
