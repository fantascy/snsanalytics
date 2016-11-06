import datetime
import logging
import math
import random

from google.appengine.ext import db
from search.core import SearchIndexProperty, porter_stemmer

import context
from common import consts as common_const
from common.utils import string as str_util
from common.utils import datetimeparser
from common.content import consts as common_cont_const
from common.content.trove import consts as trove_const
from common.content.trove import api as trove_api
from common.content import feedfetcher
from sns.core.core import KeyName
from sns.core.base import ModifiedTimeBaseModel
from sns.camp import consts as camp_const
from sns.cont.models import BaseFeed, ContentPolySmall, Topic
from sns.cont import consts as cont_const


class FeedBuilderSmall(ContentPolySmall):
    name = db.StringProperty(required=True)


class FeedBuilder(BaseFeed, KeyName):
    feeds = db.ListProperty(db.Key)
    uri = db.StringProperty()
    scheduleNext = db.DateTimeProperty(default=common_const.EARLIEST_TIME)
    state = db.IntegerProperty(default=camp_const.CAMPAIGN_STATE_ACTIVATED, choices=camp_const.CAMPAIGN_STATES)
    items = db.ListProperty(db.Text)
    searchIndex = SearchIndexProperty(('name','uri'), indexer=porter_stemmer,relation_index=False)
    
    """ Execution interval seconds. """
    EXECUTION_INTERVAL = 3600

    """ Maximum feed entry to fetch per feed per execution. """
    MAXIMUM_ENTRY_PER_FEED = 1 
                                       
    @classmethod
    def keyNamePrefix(cls):
        return "FeedBuilder:"

    def feedUrl(self):
        return  'http://' + context.get_context().feedbuilder_domain()+'/rss/'+ self.uri
    

class BaseTopicFeedBuilder(ModifiedTimeBaseModel, KeyName):
    """ Key name strip is topic key. """
    troveitems = db.TextProperty()
    gnewsitems = db.TextProperty()
    trovesearchurl = db.StringProperty(indexed=False)
    gnewssearchurl = db.StringProperty(indexed=False)
    count = db.IntegerProperty(default=0, required=True, indexed=False)
    NEWS_FEED_PATTERN = None
    TROVE_ENABLED = True
    GNEWS_ENABLED = True
    SKIP_BLACKLIST = False
    CONTENT_CUTOFF_HOURS = common_const.CONTENT_CUTOFF_HOURS
    MINIMUM_FETCH_INTERVAL = datetime.timedelta(minutes=15)
    MAXIMUM_ENTRIES = 50
    TIMELY_RANDOMIZED = False
    
    def __init__(self,
               parent=None,
               key_name=None,
               **kwds):
        ModifiedTimeBaseModel.__init__(self, parent=parent, key_name=key_name, **kwds)
        self.updated_trove = False
        self.updated_gnews = False
                                          
    @classmethod
    def get_by_topic_key(cls, topic_key):
        return cls.get_by_key_name_strip(str_util.lower_strip(topic_key))

    @classmethod
    def get_or_insert_by_topic_key(cls, topic_key):
        keyname = cls.keyName(str_util.lower_strip(topic_key))
        return cls.get_or_insert(keyname)  

    @classmethod
    def get_feed_url(cls, topic_key):
        return cls.NEWS_FEED_PATTERN % (context.get_context().feedbuilder_domain(), topic_key)
        
    @classmethod
    def is_trove_enabled(cls):
        return cls.TROVE_ENABLED and context.is_trove_enabled()
        
    @classmethod
    def is_gnews_enabled(cls):
        return cls.GNEWS_ENABLED
        
    def trove_oldest(self):
        return self.troveitems[-1].updated_time if self.troveitems else None
    
    def gnews_oldest(self):
        return self.gnewsitems[-1].updated_time if self.gnewsitems else None
    
    def fetch(self):
        try:
            troveitems = self.fetch_troveitems() if self.is_trove_enabled() else []
            gnewsitems = self.fetch_gnewsitems() if self.is_gnews_enabled() else []
            self.count = len(troveitems) + len(gnewsitems)
            if self.updated_trove or self.updated_gnews:
                self.put()
            if self.TIMELY_RANDOMIZED:
                self.timely_randomize_items(troveitems)
                self.timely_randomize_items(gnewsitems)
            return troveitems + gnewsitems
        except:
            logging.exception("Error fetching topic feed! %s" % self.keyNameStrip())
            return []

    def fetch_troveitems(self):
        old_troveitems = trove_api.TroveItem.text_to_items(self.troveitems)
        if old_troveitems and self.modifiedTime > datetime.datetime.utcnow() - self.MINIMUM_FETCH_INTERVAL:
            return old_troveitems
        self.updated_trove = True
        topic_key = self.keyNameStrip()
        topic = Topic.get_by_topic_key(topic_key)
        if not topic:
            logging.warn("Invaid topic key %s!" % topic_key)
            return []
        if trove_api.is_topic_key_in_blacklist(topic_key):
            new_troveitems = []
        else:
            normalize_search_keywords = trove_api.normalize_search_keywords(topic.name)
            trovesearchurl = trove_api.get_search_url_by_keywords(normalize_search_keywords, limit=self.MAXIMUM_ENTRIES)
            if not trovesearchurl == self.trovesearchurl:
                self.trovesearchurl = trovesearchurl
                old_troveitems = []
            new_troveitems = trove_api.search_and_filter(normalize_search_keywords, contcutoffhours=self.CONTENT_CUTOFF_HOURS, limit=self.MAXIMUM_ENTRIES)
            new_troveitems = trove_api.filter_search_results(new_troveitems, contcutoffhours=self.CONTENT_CUTOFF_HOURS, usage_rights_set=set([trove_const.USAGE_RIGHTS_FULL,]))
        troveitems = self._merge_items(old_troveitems, new_troveitems)
        self.troveitems = trove_api.TroveItem.items_to_text(troveitems)
        self.handle_troveitems(troveitems)
        return troveitems

    def fetch_gnewsitems(self):
        topic_key = self.keyNameStrip()
        old_gnewsitems = trove_api.TroveItem.text_to_items(self.gnewsitems)
        if old_gnewsitems and self.modifiedTime > datetime.datetime.utcnow() - self.MINIMUM_FETCH_INTERVAL:
            return old_gnewsitems 
        self.updated_gnews = True
        from sns.cont.feedsources import FeedSource
        gnewssearchurl = FeedSource(cont_const.FEED_SOURCE_GOOGLE_NEWS).get_feed_by_topic_keys([topic_key])
        if not gnewssearchurl: return []
        gnewssearchurl = self.handle_gnewssearchurl(gnewssearchurl)
        if not gnewssearchurl == self.gnewssearchurl:
            self.gnewssearchurl = gnewssearchurl
            old_gnewsitems = []
        googlenews_fetcher = feedfetcher.GoogleFeedFetcher(gnewssearchurl, parseFeedUrlFromPage=False, contcutoffhours=self.CONTENT_CUTOFF_HOURS)
        new_gnewsitems = googlenews_fetcher.fetch(history=[], limit=self.MAXIMUM_ENTRIES, is_cmp=True, extra=dict(skip_trove_check=True))
        new_gnewsitems = [item.to_trove_item() for item in new_gnewsitems]
        gnewsitems = self._merge_items(old_gnewsitems, new_gnewsitems)
        self.gnewsitems = trove_api.TroveItem.items_to_text(gnewsitems)
        self.handle_gnewsitems(gnewsitems)
        return gnewsitems

    def handle_troveitems(self, troveitems):
        pass
        
    def handle_gnewsitems(self, gnewsitems):
        pass
        
    def handle_gnewssearchurl(self, gnewssearchurl):
        return gnewssearchurl

    def timely_randomize_items(self, items):
        if not items: return
        items.sort(key=lambda item: self._timely_randomization_score(item))

    def _timely_randomization_score(self, item):
        seconds = datetimeparser.timedelta_in_seconds(datetime.datetime.utcnow() - item.updated_time)
        if seconds < 0: seconds = 0
        num5secs = seconds / 300 + 1
        logged_time_factor = int(math.ceil(math.log(num5secs, 2)))
        random_score = logged_time_factor * 100 + random.randint(0, 99)
        return random_score
    
    def _merge_items(self, old, new):
        items = trove_api.TroveItem.merge_entries(old, new)
        items = trove_api.filter_search_results(items, contcutoffhours=self.CONTENT_CUTOFF_HOURS, skip_blacklist=self.SKIP_BLACKLIST)
        items = items[:self.MAXIMUM_ENTRIES]
        return items
    

class TopicScoreFeedBuilder(BaseTopicFeedBuilder):
    trovescore = db.IntegerProperty(default=0, required=True, indexed=False)
    gnewsscore = db.IntegerProperty(default=0, required=True, indexed=False)
    NEWS_FEED_PATTERN = common_cont_const.TOPIC_SCORE_NEWS_FEED_PATTERN
    SKIP_BLACKLIST = True
    CONTENT_CUTOFF_HOURS = 24 * 365
    MINIMUM_FETCH_INTERVAL = datetime.timedelta(minutes=180)
    MAXIMUM_ENTRIES = 100
        
    @classmethod
    def keyNamePrefix(cls):
        return "TopicScoreFeedBuilder:"

    def handle_troveitems(self, troveitems):
        self.trovescore = self._calculate_score(troveitems)
        
    def handle_gnewsitems(self, gnewsitems):
        self.gnewsscore = self._calculate_score(gnewsitems)
        
    def handle_gnewssearchurl(self, gnewssearchurl):
        return gnewssearchurl.replace("num=15", "num=%d" % self.MAXIMUM_ENTRIES)

    @property
    def score(self):
        return self.trovescore + self.gnewsscore/5
        
    def _calculate_score(self, items):
        if not items: return 0
        size = len(items)
        if size < self.MAXIMUM_ENTRIES: return size
        seconds = datetimeparser.timedelta_in_seconds(datetime.datetime.utcnow() - items[-1].updated_time)
        days = seconds / 86400 + 1
        time_decay_factor = int(math.floor(math.log(days, 2))) + 1
        return size * 10 / time_decay_factor
        
    @classmethod
    def get_feed_url(self, topic_key):
        return common_cont_const.TOPIC_SCORE_NEWS_FEED_PATTERN % (context.get_context().feedbuilder_domain(), topic_key)
        

class ComboFeedBuilder(BaseTopicFeedBuilder):
    NEWS_FEED_PATTERN = common_cont_const.COMBO_NEWS_FEED_PATTERN
    TIMELY_RANDOMIZED = True

    @classmethod
    def keyNamePrefix(cls):
        return "ComboFeedBuilder:"

    def handle_troveitems(self, troveitems):
        if troveitems:
            from sns.url.models import GlobalUrl
            for item in troveitems:
                global_url = GlobalUrl.get_or_insert_by_url(item.link, resolve_trove_url=False)
                if global_url and global_url.troveState != trove_const.URL_STATE_HOSTED:
                    global_url.mark_trove_hosted(item.trove_url, item.full_image)
        

class TroveFeedBuilder(BaseTopicFeedBuilder):
    NEWS_FEED_PATTERN = trove_const.NEWS_FEED_PATTERN
    GNEWS_ENABLED = False

    @classmethod
    def keyNamePrefix(cls):
        return "TroveFeedBuilder:"


