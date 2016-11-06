from urllib import quote_plus, quote
import logging
import re
import csv

from google.appengine.ext import db

from common import consts as common_const
from common.utils import url as url_util, string as str_util
from common.content.googlenews import api as googlenews_api
from common.content import feedfetcher
from sns.serverutils import memcache
from sns.core.core import KeyName
from sns.cont import consts as cont_const
from sns.cont import utils as cont_util
from sns.cont.models import Topic, Domain2CS
from sns.cont.topic.api import TopicCacheMgr
from sns.feedbuilder.models import TroveFeedBuilder


class FeedSource(object):
    def __init__(self, fsid):
        self.fsid = int(fsid)
        self.name = cont_const.FEED_SOURCE_MAP[self.fsid]
        self.standardUrlPattern = cont_const.FEED_SOURCE_STANDARD_URL_PATTERN_MAP.get(self.fsid, None)
        
    def _getStandardFeed(self, topics):
        if len(topics) != cont_util.get_topic_number_by_fsid(self.fsid):
            logging.error("Topic length invalid!")
            return None
        if not self.standardUrlPattern: return None
        topic_name = topics[0].strip()
        if self.fsid == cont_const.FEED_SOURCE_CATEGORY_DEAL:
            firstTopic = Topic.get_by_name(topic_name).keyNameStrip()
            secondTopic = Topic.get_by_name(topics[1]).keyNameStrip()
            if firstTopic is None or secondTopic is None:
                logging.error("Incomplete topics for category deal: %s" % str(topics))
                return None
            return self.standardUrlPattern % (firstTopic, secondTopic)
        if self.fsid == cont_const.FEED_SOURCE_TROVE:
            return TroveFeedBuilder.get_feed_url(topic_name)
        else:
            if self.fsid == cont_const.FEED_SOURCE_REDDIT or self.fsid== cont_const.FEED_SOURCE_DEAL:
                keywords = Topic.get_by_name(topic_name).keyNameStrip()
            elif self.fsid == cont_const.FEED_SORCE_VIMEO or self.fsid == cont_const.FEED_SOURCE_INSTAGRAM:
                if topic_name.find(' ')!= -1 and self.fsid == cont_const.FEED_SOURCE_INSTAGRAM:
                    logging.error("Unsupported keyword for Instagram: %s" % topic_name)
                    raise Exception
                topic_name = topic_name.encode('utf-8')
                topic_name = quote(topic_name)
                keywords = topic_name
            else:
                keywords_map = FeedSourceConfig.get_custom_feed_map(cont_const.FEED_SOURCE_SEARCH_KEYWORD)
                custom_keywords = keywords_map.get(topic_name, None)
                keywords = googlenews_api.SearchKeywordsHandler(topic_name, custom_keywords=custom_keywords).keywords
                keywords = quote_plus(str_util.encode_utf8_if_ok(keywords))
            return self.standardUrlPattern % keywords
        
    def get_feed_by_topic_keys(self, topic_keys):
        topics = []
        for topic_key in topic_keys:
            topic = Topic.get_by_topic_key(topic_key)
            if topic: topics.append(topic.name)
        return self.get_feed_by_topic_names(topics) if topics else None

    def get_feed_by_topic_names(self, topics):
        """ Use topic names not topic keys. """
        custom_feed = self.customFeedMap().get(self.getCustomFeedKey(topics), None)
        if custom_feed and self.fsid == cont_const.FEED_SOURCE_GOOGLE_NEWS:
            topic_name = topics[0]
            return TroveFeedBuilder.get_feed_url(topic_name)
        return custom_feed if custom_feed else self._getStandardFeed(topics)     

    def customFeedMap(self):
        return FeedSourceConfig.get_custom_feed_map(self.fsid)
    
    def getCustomFeedKey(self,topics):
        return '|'.join(topics)
        
    @classmethod
    def get_name(cls, fsid):
        return cont_const.FEED_SOURCE_MAP[int(fsid)]

    @classmethod
    def is_valid_type(cls, fsid):
        return int(fsid) in cont_const.FEED_SOURCE_MAP.keys()


class FeedSourceConfig(db.Model, KeyName):
    customFeedMap = db.TextProperty()
    
    @classmethod
    def keyNamePrefix(cls):
        return "FeedSourceConfig:"    
    
    @classmethod
    def get_or_insert_by_type(cls, fsid):
        return cls.get_or_insert(cls.keyName(FeedSource.get_name(fsid)))
    
    @classmethod
    def memcache_key(cls, fsid):
        return "%sCustomFeed:%s" % (cls.keyNamePrefix(), FeedSource.get_name(fsid))
    
    @classmethod
    def memcache_delete(cls, fsid):
        memcache.delete(cls.memcache_key(fsid))
    
    @classmethod
    def deferred_set_custom_feed(cls, fsid, data):
        all_topic_names = set(TopicCacheMgr.get_all_topic_names())
        _map = {}
        rows = csv.reader(data)
        count = 0
        while True:
            count +=1
            try:
                obj = rows.next()
            except:
                break
            if count == 1:
                continue
            topic_name = str_util.strip(obj[0])
            if topic_name is None or topic_name not in all_topic_names and not cls.has_wild_card(topic_name):
                logging.error("FeedSource: Invalid topic name '%s' at line #%d!" % (topic_name, count))
                continue
            _map[topic_name] = obj[1]
        cusFeed = FeedSourceConfig.get_or_insert_by_type(fsid)
        cusFeed.customFeedMap = str(_map)
        cusFeed.put()
        FeedSourceConfig.memcache_delete(fsid)

    @classmethod
    def get_custom_feed_map(cls, fsid):
        if not FeedSource.is_valid_type(fsid):
            return {}
        memcacheKey = FeedSourceConfig.memcache_key(fsid)
        dbKey = FeedSourceConfig.keyName(FeedSource.get_name(fsid))
        _map = memcache.get(memcacheKey)
        if _map is None:
            cusFeed = cls.get_or_insert(dbKey)
            if cusFeed.customFeedMap is None:
                _map = {}
            else:
                _map = eval(cusFeed.customFeedMap) 
            memcache.set(memcacheKey, _map)
        return _map

    @classmethod
    def get_matched_custom_feed(cls, fsid, topic_name):
        """ Do wild card match if no exact match. Returning a tuple of (required_keywords, feed_url). """ 
        custom_feed_map = cls.get_custom_feed_map(fsid)
        if not custom_feed_map:
            return [], None
        if custom_feed_map.has_key(topic_name):
            return [], custom_feed_map.get(topic_name)
        wc_topic_name, required_keywords = cls.to_bracket_wild_card(topic_name)
        if wc_topic_name and custom_feed_map.has_key(wc_topic_name):
            return required_keywords, custom_feed_map.get(wc_topic_name)
        return [], None 
            
    @classmethod
    def to_bracket_wild_card(cls, topic_name):
        """ 
            Sample input: 'Arizona Wildcats (Football)' 
            Sample output: 'Arizona Wildcats (*)', ['Football'] 
        """ 
        tokens = re.split('\(|\)', topic_name)
        if len(tokens) != 3:
            return None, []
        else:
            return "%s(%s)%s" % (tokens[0], '*', tokens[2]), [tokens[1]]

    @classmethod
    def has_wild_card(cls, topic_name):
        return topic_name.find('(*)') != -1
        
        
class CSFSFeedEntry(feedfetcher.FeedEntry):
    @classmethod
    def preprocess_url_wo_fetch(cls, url):
        return url_util.remove_analytics_params(url)


class CSFSFeedFetcher(feedfetcher.DynamicFeedFetcher):
    def __init__(self, cskey, fsid, required_keywords, urlFileStreamOrString, parseFeedUrlFromPage=False):
        feedfetcher.DynamicFeedFetcher.__init__(self, urlFileStreamOrString, parseFeedUrlFromPage=parseFeedUrlFromPage)
        self.cskey = cskey
        self.fsid = fsid
        self.required_keywords = required_keywords
        
    @classmethod
    def get_feed_fetcher(cls, cskey, fsid, topic_keys):
        """ Only consider a single topic match for now. """
        if len(topic_keys) != 1:
            return None
        topic_key = topic_keys[0]
        topic = Topic.get_by_topic_key(topic_key)
        required_keywords, feed_url = FeedSourceConfig.get_matched_custom_feed(fsid, topic.name)  
        return cls(cskey, fsid, required_keywords, feed_url) if feed_url else None
    
    @classmethod
    def entry_model(cls):
        return CSFSFeedEntry
        
    @classmethod
    def max_history(cls):
        return 100
    
    @classmethod
    def fetch_content_by_default(cls):
        return True

    def entry_domain_always_diff(self):
        return True

    def on_blacklist(self, url):
        return False

    def fetch(self, history, limit=common_const.FEED_FETCHER_HISTORY_LIMIT_DEFAULT):
        entries = feedfetcher.DynamicFeedFetcher.fetch(self, history, limit=limit, is_cmp=True)
        for entry in entries:
            if entry.error:
                continue
            domain = url_util.root_domain(entry.url)
            domain_2_cs = Domain2CS.pull(domain, insert=True, cskey=self.cskey)
            if domain_2_cs:
                logging.info("Marked domain %s as content source %s." % (domain, self.cskey))
            else:
                logging.error("Failed to mark domain %s as content source %s." % (domain, self.cskey))
        return entries

                
    