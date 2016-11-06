import datetime
import logging
import urllib
import random
from sets import ImmutableSet

import json
from google.appengine.ext import db
from common.utils import datetimeparser
import context, deploysns
from common.utils import string as str_util, url as url_util, timezone as ctz_util
from sns.serverutils import deferred, memcache
from sns.core import core as db_core
from sns.core import base as db_base
from sns.api import consts as api_const
from sns.api.base import BaseProcessor
from sns.camp import consts as camp_const
from sns.cont.models import Topic
from sns.cont.topic.api import TopicCacheMgr
from sns.deal import consts as deal_const
from sns.deal import utils as deal_util
from sns.deal.models import DealBuilder, CatDealBuilder, DealStats, DealStatsCounter, TopDeal


class DealFeedFetcher(deal_util.DealFeedUtilFetcher):
    @classmethod
    def predefined_groupon_top_deal_by_location(cls, location):
        top_deal_url = GrouponApi.get_city_2_top_deal_map().get(location, None)
        if top_deal_url:
            location_topic = Topic.get_by_key_name_strip(location)
            if location_topic:
                location_name = location_topic.name.split(',')[0]
                title = "Best Deal of the Day in %s! " % location_name
                return deal_util.Deal(
                    url=top_deal_url,
                    title=title, 
                    sourceKey=deal_const.DEAL_SOURCE_GROUPON,
                    price=None,
                    bought=None,
                    expireTime=None,
                                      )
        return None

    def predefined_top_deal(self):
        location, category = self.get_location_category_tuple()
        if category == deal_const.CATEGORY_KEY_GENERAL:
            return self.predefined_groupon_top_deal_by_location(location)
        return None


class DealBuilderProcessor(BaseProcessor):
    def getModel(self):
        return DealBuilder

    @classmethod
    def supportedOperations(cls):
        return ImmutableSet([api_const.API_O_CRON_EXECUTE, 
                           ]).union(BaseProcessor.supportedOperations())
                           
    def create(self, params):
        key_name = DealBuilder.keyName(params['location'])
        paramsCopy = params.copy()
        paramsCopy['key_name'] = key_name
        if not paramsCopy.has_key('uid'):
            paramsCopy['uid'] = db_core.get_user_id()
        return BaseProcessor.create(self, paramsCopy)
            
    def cron_execute(self, params):
        utcnow = datetime.datetime.utcnow()
        activeQuery = self.getModel().all().filter('deleted',False).filter('state', camp_const.CAMPAIGN_STATE_ACTIVATED).filter('scheduleNext <= ', utcnow).order('scheduleNext')
        activeCount = activeQuery.count(1000)
        logging.info("Total %s deal builders are due." % str(activeCount))
        if activeCount == 0:
            return 0
        activeBuilders = activeQuery.fetch(limit=100)
        totalBuilders = activeBuilders
        deferCount= 0
        for builder in totalBuilders:
            try:
                builder.scheduleNext = DealBuilderProcessor._get_schedule_next()
                builder.put()
                deferred.defer(self.__class__._deferred_handler_execute_one, dealBuilderId=builder.id, queueName='dealbuilder')
                deferCount += 1
            except:
                logging.exception("Failed to schedule deal builder '%s'." % builder.name)
        return deferCount
    
    BUILD_INTERVAL = 5400
    @classmethod
    def _get_schedule_next(cls):
        seconds = random.randint(cls.BUILD_INTERVAL, cls.BUILD_INTERVAL*2)
        return datetime.datetime.utcnow() + datetime.timedelta(seconds=seconds)

    @classmethod
    def _deferred_handler_execute_one(cls, dealBuilderId):
        context.set_deferred_context(deploy=deploysns)
        return cls()._executeOne(dealBuilderId)

    def _executeOne(self, dealBuilderId):
        builder = db.get(dealBuilderId)
        location = builder.keyNameStrip()
        if location in DealSourceApi.get_deal_cities():
            grouponDeals = GrouponApi.get_division_deals(location) 
        elif location in deal_const.DEAL_COUNTRIES:
            grouponDeals = GrouponApi.get_national_deals(location) 
        else:
            logging.error("Deal builder '%s' location '%s' is invalid." % (builder.name, location))
            return
#        affDeals = DealsurfApi.get_deals(location)[1]
#        affDeals = grouponDeals + affDeals
        affDeals = grouponDeals
        affDeals = deal_util.Deal.sort(affDeals)
        try:
            logging.info("Fetched %s affiliated deals for deal builder '%s'." % (len(affDeals), builder.name))
            all_deals = self._executeCatDealBuilders(location, affDeals)
            builder.updateDeals(all_deals).put()
            logging.info("Saved %s affiliated deals for deal builder '%s'." % (len(all_deals), builder.name))
        except:
            logging.exception("Unexpected error when saving deals for deal builder '%s'." % builder.name)

    def _executeCatDealBuilders(self, location, deals):
        dealsByTopicKey = {}
        for deal in deals:
            for topicKey in deal.cats:
                topicDeals = dealsByTopicKey.get(topicKey, [])
                topicDeals.append(deal)
                dealsByTopicKey[topicKey] = topicDeals
        builders = []
        for topicKey in deal_const.CATEGORY_TOPIC_KEYS:
            builder = CatDealBuilder.get_or_insert_by_location_cat(location, topicKey)
            if len(builder.items)==0 and not dealsByTopicKey.has_key(topicKey):
                continue
            builders.append(builder)
            if dealsByTopicKey.has_key(topicKey):
                cat_deals = dealsByTopicKey.get(topicKey)
                builder.updateDeals(cat_deals)
                if cat_deals:
                    TopDeal.get_or_insert_by_location_category(location, topicKey).update(deal=cat_deals[0])
            dstats = DealStats.get_or_insert_by_location_category(location, topicKey)
            DealStatsProcessor.update_current_deals(dstats, current_deals=len(builder.items)) 
        db.put(builders)
        feeds = [builder.feed().feed['link'] for builder in builders]
        all_deals = []
        for builder in builders:
            deals = builder.deals()
            if deals:
                all_deals.extend(deals)
        all_deals = deal_util.Deal.sort(all_deals)
        top_deal = DealFeedFetcher.predefined_groupon_top_deal_by_location(location)
        if top_deal is None and all_deals:
            top_deal = all_deals[0]
        if top_deal:
            top_deal = TopDeal.get_or_insert_by_location_category(location, deal_const.CATEGORY_KEY_GENERAL).update(deal=top_deal)
            logging.info("TopDeal: updated top deal for %s: %s" % (location, top_deal))
        logging.info("Total %d deals of %d categories for location '%s': \n%s" % (len(all_deals), len(feeds), location, '\n'.join(feeds)))
        return all_deals
        
    def execute_admin(self, params):
        op = params.get('op', None)
        if op:
            if op=='daily_deal_count_update':
                return DealStatsProcessor().daily_deal_count_update()
        return BaseProcessor.execute_admin(self, params)


class CatDealBuilderProcessor(BaseProcessor):
    def getModel(self):
        return CatDealBuilder

    def create(self, params):
        location = params['location']
        cat = params['cat']
        key_name = CatDealBuilder.key_name(location, cat)
        paramsCopy = params.copy()
        paramsCopy['key_name'] = key_name
        paramsCopy['name'] = "Deals - %s - %s" % (location, cat)
        return BaseProcessor.create(self, paramsCopy)


class DealStatsCounterProcessor(BaseProcessor):
    def getModel(self):
        return DealStatsCounter
        

class DealStatsProcessor(BaseProcessor):
    def __init__(self):
        BaseProcessor.__init__(self)
        
    def getModel(self):
        return DealStats

    @classmethod
    def update_current_deals(cls, dstats, counter=None, current_deals=None, now=None):
        now = now if now else ctz_util.uspacificnow()
        modified_time = ctz_util.to_uspacific(dstats.modifiedTime)
        if current_deals is None:
            current_deals = dstats.currentDeals if now.day == modified_time.day else 0  
        if now.day == modified_time.day and current_deals <= dstats.currentDeals:
            logging.debug(dstats.log_deal_counts())
            return
        update_list = [dstats]
        if now.day == modified_time.day:
            dstats.currentDeals = current_deals
        else:
            if counter is None:
                counter = dstats.get_or_insert_counter()
            counter.setDealCount(dstats.currentDeals, modified_time)
            dstats.deals = dstats.currentDeals
            dstats.totalDeals = counter.totalDeals()
            dstats.currentDeals = current_deals
            update_list.append(counter)
            logging.debug(dstats.log_deal_counts())
        db_base.txn_put(update_list)
            
    def daily_deal_count_update(self):
        now = ctz_util.uspacificnow()
        dstats_list = self.execute_query_all()
        counter_list = DealStatsCounterProcessor().execute_query_all()
        dstats_map = dict([(dstats.keyNameStrip(), dstats) for dstats in dstats_list]) 
        counter_map = dict([(counter.keyNameStrip(), counter) for counter in counter_list])

        total_by_location = {} 
        total_by_category = {}
        for key_name, dstats in dstats_map.items():
            counter = counter_map.get(key_name, None)
            if counter is None:
                counter = dstats.get_or_insert_counter()
                counter_map[key_name] = counter
            location, category = key_name.split('_')
            if not DealStats.is_special_key(key_name):
                self.update_current_deals(dstats, counter=counter, now=now)
                dstats_key_location_total = DealStats.location_total_key(location)
                dstats_key_category_total = DealStats.total_category_key(category)
                location_total = total_by_location.get(dstats_key_location_total, 0)
                category_total = total_by_category.get(dstats_key_category_total, 0)
                total_by_location[dstats_key_location_total] = location_total + dstats.currentDeals
                total_by_category[dstats_key_category_total] = category_total + dstats.currentDeals
        
        for key_name, current_deals in total_by_location.items():
            self._update_total(key_name, current_deals, dstats_map, counter_map, now)
        for key_name, current_deals in total_by_category.items():
            self._update_total(key_name, current_deals, dstats_map, counter_map, now)
        total_current_deals = sum(total_by_location.values())
        self._update_total(deal_const.LOCATION_CATEGORY_KEY_TOTAL_GENERAL, total_current_deals, dstats_map, counter_map, now)
        self._update_total(deal_const.LOCATION_CATEGORY_KEY_TOTAL, total_current_deals, dstats_map, counter_map, now)

        return dstats_map, counter_map

    def _update_total(self, key_name, current_deals, dstats_map, counter_map, now):
        location, category = key_name.split('_')
        dstats = dstats_map.get(key_name, None)
        if dstats is None:
            dstats = DealStats.get_or_insert_by_location_category(location, category)
            dstats_map[key_name] = dstats
        counter = counter_map.get(key_name, None)
        if counter is None:
            counter = dstats.get_or_insert_counter()
            counter_map[key_name] = counter
        self.update_current_deals(dstats, counter=counter, current_deals=current_deals, now=now)
        

def deal_builder_buffer_size(national=False):
    if national:
        if context.is_dev_mode():
            return deal_const.DEAL_BUILDER_BUFFER_SIZE_NATIONAL_DEBUG
        else:
            return deal_const.DEAL_BUILDER_BUFFER_SIZE_NATIONAL
    if context.is_dev_mode():
        return deal_const.DEAL_BUILDER_BUFFER_SIZE_DEBUG
    else:
        return deal_const.DEAL_BUILDER_BUFFER_SIZE            


class DealSourceApi:
    @classmethod
    def fetch(cls, api):
        retry = 1
        while retry <= 3:
            try:
                resp = url_util.fetch_url(api)
                return json.loads(resp)
            except:
                retry += 1
                if retry == 3:
                    logging.exception("Fetching deals API failed for %s times. %s" % (retry, api))
        return None

    @classmethod    
    def get_deal_cities(cls):
        return GrouponApi.get_city_2_division_map().keys()

    @classmethod    
    def get_all_deal_locations(cls):
        all_locations = GrouponApi.get_city_2_division_map().keys()
        all_locations.extend(deal_const.DEAL_COUNTRIES)
        return all_locations


class GrouponApi(DealSourceApi):
    @classmethod    
    def get_city_2_division_map(cls):
        deal_cities = TopicCacheMgr.get_all_deal_city_topics()
        c2d_map = {}
        for topic in deal_cities:
            groupon_code = topic.ext_get_attr('groupon_code')
            if groupon_code:
                groupon_code = groupon_code.split('|')[0]
                c2d_map[topic.keyNameStrip()] = groupon_code
        return c2d_map

    @classmethod    
    def get_city_2_top_deal_map(cls):
        deal_cities = TopicCacheMgr.get_all_deal_city_topics()
        c2d_map = {}
        for topic in deal_cities:
            groupon_top_deal_url = topic.ext_get_attr('groupon_top_deal_url')
            if groupon_top_deal_url:
                c2d_map[topic.keyNameStrip()] = groupon_top_deal_url
        return c2d_map

    @classmethod    
    def get_division_deals(cls, city):
        deals = []
        division = cls.get_city_2_division_map().get(city, None)
        if division is None:
            return deals
        try:
            params = {
                'division_id': division,
                'client_id': deal_const.GROUPON_CLIENT_ID,
                      }
            api = "https://api.groupon.com/v2/deals.json?%s" % urllib.urlencode(params)
            deals, onlineDeals = cls.get_deals(api)
            cls._cache_online_deals(division, onlineDeals) 
        except:
            logging.exception("Unexpected error when fetching groupon deals for city '%s'." % city)
        logging.info("Fetched groupon for city '%s': total %s deals, %s national." % (city, len(deals), len(onlineDeals)))
        return deals
    
    @classmethod    
    def get_national_deals(cls, country):
        channelDeals = []
        for cat, channel in deal_const.TOPIC_2_GROUPON_CHANNEL_MAP.items():
            if channel is not None:
                gdeals = GrouponApi.get_channel_deals(channel)
                for gdeal in gdeals:
                    gdeal.cats = [str_util.name_2_key(cat)]
                channelDeals = gdeals + channelDeals
        divisionOnlineDeals = cls.get_country_online_deals(country)
        logging.info("Total groupon online deals: %d channel and %d division." % (len(channelDeals), len(divisionOnlineDeals)))
        return channelDeals + divisionOnlineDeals

    @classmethod    
    def get_channel_deals(cls, channel):
        deals = []
        onlineDeals = []
        try:
            api = "https://api.groupon.com/v2/channels/%s/deals.json?client_id=%s" % (channel, deal_const.GROUPON_CLIENT_ID)
            deals, onlineDeals = cls.get_deals(api)
        except:
            logging.exception("Unexpected error when fetching groupon deals for channel '%s'." % channel)
        logging.info("Fetched groupon deals for channel '%s': total %s deals, %s national." % (channel, len(deals), len(onlineDeals)))
        return deals
                
    @classmethod    
    def get_division_online_deals(cls, division):
        key = cls.get_online_deals_cache_key(division)
        deals = memcache.get(key)
        if deals is None:
            logging.error("Groupon online deals cache is missing for division '%s'!" % division)
            deals = {}
        eligibleDeals = []
        for deal in deals:
            if deal.isEligible():
                eligibleDeals.append(deal)
        return eligibleDeals
    
    @classmethod    
    def get_country_online_deals(cls, country='us'):
        key = cls.get_online_deals_cache_key(country)
        deals = memcache.get(key)
        if deals is None:
            deals = []
            for city in DealSourceApi.get_deal_cities():
                division = cls.get_city_2_division_map().get(city, None)
                more = cls.get_division_online_deals(division)
                deals = deals + more
            memcache.set(key, deals, time=3600)
        return deals
    
    @classmethod    
    def get_deals(cls, api):
        data = cls.fetch(api)
        if data is None:
            return [], []
        deals = []
        onlineDeals = [] 
        for item in data['deals']:
            if item.get('isSoldOut', False):
                continue
            deal = deal_util.Deal()
            deal.title = str_util.strip_one_line(item.get('announcementTitle', None))
            deal.url = item.get("dealUrl", None)
            expireTime = item.get('endAt', None)
            if expireTime is None:
                deal.expireTime = datetime.datetime.utcnow() + datetime.timedelta(days=5)
                logging.warn("Groupon deal has no expire time, set expire time to 5 days later: %s" % deal.url)
            else:
                expireTime = expireTime.replace('T', ' ').replace('Z', ' ').strip()
                deal.expireTime = datetimeparser.parseDateTime(expireTime)
            deal.price = item['options'][0]['price']['amount']
            deal.bought = item.get('soldQuantity', 0)
            deal.national = item.get('redemptionLocation', None)=='online'
            deal.sourceKey = deal_const.DEAL_SOURCE_GROUPON
            try:
                tags = item.get('tags', [])
                if len(tags) >0:
                    cats = []
                    for tag in tags[0].values():
                        cs = deal_const.GROUPON_CATEGORY_2_TOPIC_MAP.get(str_util.name_2_key(tag), [])
                        if not cs:
                            logging.error("Unknown Groupon deal tag '%s'! %s %s" % (tag, deal.title, deal.url))
                            continue
                        for c in cs:
                            cats.append(c)
                    deal.cats = cats
            except:
                logging.exception("Error when fetching Groupon tags.")
            deal.addAffInfo2Url()
            deals.append(deal)
            if deal.national:
                onlineDeals.append(deal)
        for onlineDeal in onlineDeals:
            logging.debug("Groupon online deal: {%s} - %s - %s" % (', '.join(deal.cats), onlineDeal.title, onlineDeal.url))
        return deals, onlineDeals
                
    @classmethod    
    def get_online_deals_cache_key(cls, location):
        return "groupon_online_deals_%s" % location
    
    @classmethod    
    def _cache_online_deals(cls, location, deals):
        key = cls.get_online_deals_cache_key(location)
        memcache.set(key, deals, time=3600*6)
        cached_deals = memcache.get(key)
        if cached_deals is None:
            cached_deals = []
        if len(cached_deals) == len(deals):
            logging.debug("Cached %d deals for %s." % (len(deals), location))
        else:
            logging.error("Cached %d deals out of %d for %s." % (len(cached_deals), len(deals), location))
        return deals


class DealsurfApi(DealSourceApi):
    @classmethod
    def get_deals(cls, location):
        national = location in deal_const.DEAL_COUNTRIES  
        allDeals = []
        affDeals = []
        locationCode = deal_const.DEALSURF_LOCATION_MAP.get(location, None)
        if locationCode is None:
            return allDeals, affDeals
        try:
            params = {
                      'apikey': deal_const.DEALSURF_KEY,
                      'city': locationCode,
                      'local': 0 if national else 1,
                      }
            api = "http://api.dealsurf.com/deals/list.json?%s" % urllib.urlencode(params)
            data = cls.fetch(api)
            if data is None:
                return allDeals, affDeals
            try:
                items = data['response']['deals']
            except:
                logging.warn("Dealsurf API fetched empty deal data: %s" % api)
                items = []
            limit = deal_builder_buffer_size(national=national)
            parseErrorCount = 0
            for item in items:
                try:
                    sourceKey = str_util.upper_strip(item.get('provider_id', None))
                    if sourceKey in deal_const.DEAL_SOURCE_API_ENABLED:
                        continue
                    if item.get('expired', False):
                        continue
                    if item.get('national', False) and not national:
                        continue
                    deal = deal_util.Deal()
                    deal.title = str_util.strip_one_line(item.get('title', None))
                    deal.sourceKey = sourceKey
                    deal.expireTime = datetimeparser.parseDateTime(item.get('end_time').replace('/', '-'))
                    deal.price = int(item.get('value')*100)
                    popularity = item.get('popularity', 0)
                    deal.bought = cls.normalized_bought(popularity)
                    logging.debug("Dealsurf deal popularity info: popularity=%s; click=%s; priority=%s" % (item.get('popularity', 0), item.get('click', 0), item.get('priority', 0)))
                    deal.url = item.get('url', None)
                    deal.national = national
                    deal.cats = []
                    for category in item.get('category', []).values():
                        tag = str_util.name_2_key(category)
                        topicKeys = deal_const.DEALSURF_CATEGORY_2_TOPIC_MAP.get(tag, [])
                        deal.cats = deal.cats + topicKeys
                    if len(deal.cats)==0 and national:
                        deal.cats = [str_util.name_2_key(deal_const.DEAL_TOPIC_SHOPPING)]
                    cls.process_deal_link(deal)
                    if deal.url is None or deal.url.startswith("http://www.dealsurf.com/"):
                        parseErrorCount += 1
                        continue
                    allDeals.append(deal)
                    if deal.affiliated():
                        affDeals.append(deal)
                    logging.info("Fetched a dealsurf deal: {%s} %s" % (', '.join(deal.cats), deal.url))
                    if len(allDeals) >= limit:
                        break
                except:
                    logging.exception("Error when fetching a dealsurf deal!")
                    continue
            logging.info("Fetched %s deals (%s affiliated), skipped %s unparsed deals, from total %s dealsurf deal entries for location '%s'." % (len(allDeals), len(affDeals), parseErrorCount, len(items), location))
        except:
            logging.exception("Unexpected error when fetching dealsurf deals for location '%s'." % location)
        return allDeals, affDeals

    @classmethod
    def normalized_bought(cls, popularity):
        if popularity<2:
            popularity = 2
        return int(pow(popularity*10, 0.5)*10)
        
    @classmethod
    def process_deal_link(cls, deal):
        dealUrl = cls.parse_deal_link(deal.url)
        if dealUrl is not None:
            deal.url = dealUrl
            cls.normalize_deal_link(deal)
        return deal
        
    @classmethod
    def parse_deal_link(cls, url):
        memKey = 'DealUrl:' + url
        dealUrl = memcache.get(memKey)
        if dealUrl is None:
            data = url_util.fetch_url(url)
            fetcher = deal_util.DealSurfPageParser(url)
            fetcher.feed(data)
            dealUrl = fetcher.dealUrl
            memcache.set(memKey, dealUrl, time=86400)
        return dealUrl
    
    @classmethod
    def normalize_deal_link(cls, deal):
        if not deal_util.is_on_dealsurf(deal.sourceKey):
            return deal
        if deal_util.DealSurfUrlHandler.has_handler(deal.sourceKey):
            deal.url = deal_util.DealSurfUrlHandler(deal.sourceKey).handle(deal.url)
        else:
            actualUrl = url_util.fetch_redirect_url(deal.url).actualUrl()
            if actualUrl is not None:
                deal.url = deal_util.DealSurfUrlHandler(deal.sourceKey).handle(actualUrl)
        return deal
                
