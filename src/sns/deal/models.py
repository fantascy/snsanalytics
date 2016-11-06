import datetime

from google.appengine.ext import db
from search.core import SearchIndexProperty, porter_stemmer
from django.utils import feedgenerator

import deploysns
import context
from common import consts as common_const
from common.utils import datetimeparser
from sns.serverutils import memcache
from sns.core.core import KeyName
from sns.core.base import SoftDeleteNoIndexNamedBaseModel, BaseModel, DailyStatsCounterIF, DailyStatsIF
from sns.camp import consts as camp_const
from sns.deal import consts as deal_const
from sns.deal import utils as deal_util


class BaseDealBuilder(SoftDeleteNoIndexNamedBaseModel, KeyName):
    items = db.ListProperty(db.Text)
    
    def updateDeals(self, newDeals):
        oldDeals = self.deals()
        deals = deal_util.Deal.dedupe_sort(newDeals + oldDeals)
        self.items = []
        for deal in deals:
            if deal.isEligible():
                self.items.append(db.Text(deal.text()))
        return self

    def deals(self):
        deals = []
        for item in self.items:
            item = eval(item)
            deals.append(deal_util.Deal(
                    url=item.get('url'),
                    title=item.get('title'), 
                    sourceKey=item.get('sourceKey'),
                    price=item.get('price'),
                    bought=item.get('bought'),
                    expireTime=item.get('expireTime', None),
                              ))
        return deal_util.Deal.filter_expiring(deals)
        
    def feed(self, channel_type=deal_const.CHANNEL_DEAL_TWITTER_ACCOUNTS):
        return self._rss2_feed(channel_type)

    def _rss2_feed(self, channel_type=deal_const.CHANNEL_DEAL_TWITTER_ACCOUNTS):
        feed = feedgenerator.Rss201rev2Feed(title=self.name, description=self.name, link=self.feedUrl())
        for deal in self.deals():
            if channel_type == deal_const.CHANNEL_DEAL_TWITTER_ACCOUNTS:
                link = deal.url
                description = unicode({
                    'sourceKey': deal.sourceKey,
                    'price': deal.price,
                    'bought': deal.bought,
                    'expireTime': deal.expireTime,
                    })
            else:
                link = deal_util.DealUrlHandler.cj_twitter_2_mobile(deal.url)
                description = "%d people have bought." % deal.bought  
            feed.add_item(title=deal.title, link=link, pubdate=datetime.datetime.now(), description=description)
        return feed


class DealBuilder(BaseDealBuilder):
    location = db.StringProperty()
    uid = db.IntegerProperty()
    scheduleNext = db.DateTimeProperty(default=common_const.EARLIEST_TIME)
    state = db.IntegerProperty(default=camp_const.CAMPAIGN_STATE_ACTIVATED, choices=camp_const.CAMPAIGN_STATES)
    searchIndex = SearchIndexProperty(('name'), indexer=porter_stemmer, relation_index=False)
    
    @classmethod
    def keyNamePrefix(cls):
        return "DealBuilder:"
    
    def feedUrl(self):
        return "http://%s%s%s" % (deploysns.DOMAIN_MAP[context.get_context().application_id()], deal_util.DealFeedUtilFetcher.DEAL_FEED_STUB, self.keyNameStrip())
    

class CatDealBuilder(BaseDealBuilder):
    @classmethod
    def keyNamePrefix(cls):
        return "CatDealBuilder:"
    
    @classmethod
    def key_name(cls, location, cat):
        return KeyName.keyName("%s_%s" % (location, cat))
    
    @classmethod
    def get_or_insert_by_location_cat(cls, location, cat, name=None):
        name = "Deals - %s - %s" % (location, cat)
        return cls.get_or_insert(cls.key_name(location, cat), name=name, nameLower=name.lower())

    def location(self):
        return self.keyNameStrip().split('_')[0]
    
    def cat(self):
        return self.keyNameStrip().split('_')[1]
    
    def feedUrl(self):
        return "http://%s%s%s/%s" % (deploysns.DOMAIN_MAP[context.get_context().application_id()], deal_util.DealFeedUtilFetcher.DEAL_FEED_STUB, self.location(), self.cat())
    
    
class DealStatsCounter(DailyStatsCounterIF, KeyName):
    dealCounts = db.TextProperty()  
    clickCounts = db.TextProperty()  
    followerCounts = db.TextProperty()  

    @classmethod
    def keyNamePrefix(cls):
        return "DealStatsCounter:"
    
    def setDealCount(self, count, date):
        self.setCount('dealCounts', count, date, padding=DailyStatsCounterIF.PADDING_ZERO)
    
    def setClickCount(self, count, date):
        self.setCount('clickCounts', count, date, padding=DailyStatsCounterIF.PADDING_ZERO)
    
    def setFollowerCount(self, count, date):
        self.setCount('followerCounts', count, date, padding=DailyStatsCounterIF.PADDING_OLD_VALUE)
    
    def getDealCounts(self):
        return self.getCounts('dealCounts')

    def getClickCounts(self):
        return self.getCounts('clickCounts')

    def getFollowerCounts(self):
        return self.getCounts('followerCounts')

    def totalDeals(self, days=30):
        return self.totalCounts('dealCounts', days)
    
    def totalClicks(self, days=30):
        return self.totalCounts('clickCounts', days)
    
    
class DealStats(DailyStatsIF, KeyName):
    modifiedTime = db.DateTimeProperty(auto_now=True)
    category = db.StringProperty(required=True)
    location = db.StringProperty(required=True)
    currentDeals = db.IntegerProperty(default=0)
    deals = db.IntegerProperty(default=0)
    clicks = db.IntegerProperty(default=0)
    totalDeals = db.IntegerProperty(default=0)
    totalClicks = db.IntegerProperty(default=0)
    followers = db.IntegerProperty(default=0)
    channels = db.StringListProperty(indexed=False)
    searchIndex = SearchIndexProperty(('category', 'location', 'channels'), indexer=porter_stemmer, relation_index=False)
    
    @classmethod
    def keyNamePrefix(cls):
        return "DealStats:"
    
    @classmethod
    def counter_model(cls):
        return DealStatsCounter

    @classmethod
    def location_total_key(cls, location):
        return "%s_total" % location 
        
    @classmethod
    def total_category_key(cls, category):
        return "total_%s" % category

    @classmethod
    def location_total_2_general_key(cls, location_total_key):
        return '_'.join([location_total_key.split('_')[0], deal_const.CATEGORY_KEY_GENERAL])
        
    @classmethod
    def is_special_key(cls, key_name):
        return len((set(key_name.split('_')).intersection(deal_const.SPECICAL_KEY_TOKENS))) > 0
        
    @classmethod
    def get_or_insert_by_location_category(cls, location, category):
        return cls.get_or_insert(cls.keyName('_'.join([location, category])), location=location, category=category)

    def reset(self):
        DailyStatsIF.reset(self)
        self.currentDeals = 0
        self.deals = 0
        self.clicks = 0
        self.totalDeals = 0
        self.totalClicks = 0
        self.followers = 0

    def log_deal_counts(self):
        return "%s - active today %d; 30 days active %d." % (self.key().name(), self.currentDeals, self.totalDeals)

    def has_channel(self):
        return True if self.channels else False

    def first_channel(self):
        return self.channels[0] if self.channels else None

    
class TopDeal(BaseModel, KeyName):
    MEMCACHE_DURATION = 18000
    title = db.TextProperty()
    url = db.TextProperty()
    expire = db.DateTimeProperty(indexed=False)
    extra = db.TextProperty()
    tweetId = db.IntegerProperty(indexed=False)
    
    @classmethod
    def keyNamePrefix(cls):
        return "TopDeal:"

    @classmethod
    def is_valid_key_name_strip(cls, key_name_strip):
        if key_name_strip is None:
            return False
        return key_name_strip.split('_')
            
    @classmethod
    def key_name_by_location_category(cls, location, category):
        return cls.keyName("%s_%s" % (location, category))
    
    @classmethod
    def get_or_insert_by_location_category(cls, location, category):
        top_deal = cls.get_or_insert(cls.key_name_by_location_category(location, category))
        memcache.set(top_deal.key().name(), top_deal, time=cls.MEMCACHE_DURATION)
        return top_deal

    @classmethod
    def get_by_location_category(cls, location, category=deal_const.CATEGORY_KEY_GENERAL):
        if location is None:
            return None
        key_name = cls.key_name_by_location_category(location, category)
        top_deal = memcache.get(key_name)
        if top_deal is None:
            top_deal = cls.get_by_key_name(key_name)
            if top_deal:
                memcache.set(top_deal.key().name(), top_deal, time=cls.MEMCACHE_DURATION)
        return top_deal
    
    def is_expiring(self, now=datetime.datetime.utcnow()):
        if self.expire:
            return datetimeparser.timedelta_in_hours(self.expire - now) <= deal_const.DEAL_EXPIRE_CUTOFF_HOURS
        else:
            return False 
    
    def update(self, deal=None, tweet_id=None, insert=True):
        if deal:
            if self.title != deal.title or self.url != deal.url:
                self.tweetId = None
            self.title = deal.title
            self.url = deal.url
            self.extra = str({'rank': deal.rank(), 'price': deal.price, 'bought': deal.bought})
            self.expire = deal.expireTime
        if tweet_id:
            self.tweetId = tweet_id
        self.put()
        memcache.set(self.key().name(), self, time=self.MEMCACHE_DURATION)
        return self
