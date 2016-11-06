# -*- coding: utf-8 -*-
import re
from sets import Set
import calendar
from datetime import datetime, timedelta
import logging
import urllib
import urllib2
import feedparser

from gdata.youtube.service import YouTubeService

from common import consts as common_const
from common.utils import string as str_util, url as url_util, timezone as ctz_util
from common.utils import datetimeparser
from common.content import pageparser
from common.content.trove import consts as trove_const
from common.content.trove import api as trove_api
import context


COMBO_FEEDS = ['http://%s/newsfeed' % context.get_context(raiseErrorIfNotFound=False).feedbuilder_domain(), ]
TROVE_FEEDS = ['http://%s/troverss' % context.get_context(raiseErrorIfNotFound=False).feedbuilder_domain(), ]
GOOGLE_FEEDS = ['http://news.google.com/news', 'https://news.google.com/news', 'http://news.google.com.\w*/news', 'https://news.google.com.\w*/news']
BING_FEEDS = ['http://api.bing.com/rss']
YOUTUBE_FEEDS = ['http://www.youtube.com/rss', 'http://gdata.youtube.com/feeds']
YAHOO_PIPES = ['http://pipes.yahoo.com/pipes']
DYNAMIC_FEEDS = COMBO_FEEDS + TROVE_FEEDS + GOOGLE_FEEDS + BING_FEEDS + YOUTUBE_FEEDS + YAHOO_PIPES
YOUTUBE_FEED_ENTRY_QUALITY_THRESHOLD = 500
MIN_REPEAT_FREQ_BY_DOMAIN = {'wetpaint.com': 1000, }
MIN_REPEAT_FREQ_TROVE = (21, 7, 14)


def _match_feed_pattern(url, pattern):
    matched = False
    for feed in pattern:
        p = re.compile(feed)
        if p.match(url) != None:
            matched = True
            break
    return matched


def is_dynamic_feed(url):
    return _match_feed_pattern(url, DYNAMIC_FEEDS)


def is_combo_feed(url):
    return _match_feed_pattern(url, COMBO_FEEDS)


def is_trove_feed(url):
    return _match_feed_pattern(url, TROVE_FEEDS)


def is_googlenews_feed(url):
    return _match_feed_pattern(url, GOOGLE_FEEDS)


def is_bing_feed(url):
    return _match_feed_pattern(url, BING_FEEDS)


def is_youtube_feed(feed):
    isYoutube = False
    for f in YOUTUBE_FEEDS:
        if feed.startswith(f):
            isYoutube =  True
            break
    return isYoutube


def is_googlenews_url(url):
    return url and (url.startswith("http://news.google") or url.startswith("https://news.google"))
        

AFFIX_UTF8_CODE = {'()':'����',
                   '[]':'����',
                   ':':'��'}
PREFIX_REGULAR_EXPRESSION = {'()':r'^\((.(?!\)))*.\)',
                             '[]':r'^\[(.(?!\]))*.\]',
                             '{}':r'^\{(.(?!\}))*.\}',
                             '-':r'^(.(?!\-))*.\-',
                             ':':r'^(.(?!\:))*.\:',
                             '_':r'^(.(?!\_))*.\_',
                             '����':r'^\��(.(?!\��))*.\��',
                             '����':r'^\��(.(?!\��))*.\��',
                             '��':r'^(.(?!\��))*.\��'}
SUFFIX_REGULAR_EXPRESSION = {'()':r'\((.(?!\)))*.\)$',
                             '[]':r'\[(.(?!\]))*.\]$',
                             '{}':r'\{(.(?!\}))*.\}$',
                             '-':r'\-.(.(?<!\-))*$',
                             ':':r'\:.(.(?<!\:))*$',
                             '_':r'\_.(.(?<!\_))*$',
                             '����':r'\��(.(?!\��))*.\��$',
                             '����':r'\��(.(?!\��))*.\��$',
                             '��':r'\��.(.(?<!\��))*$'}


def feed_message_prefix_strip(msg,symbol):        
    if symbol in PREFIX_REGULAR_EXPRESSION:                
        msg_strip=re.sub(PREFIX_REGULAR_EXPRESSION[symbol],'',msg)
        if symbol in ['()','[]',':']:
            if len(msg)==len(msg_strip):
                msg_strip=re.sub(PREFIX_REGULAR_EXPRESSION[AFFIX_UTF8_CODE[symbol]],'',msg)
        return msg_strip
    else:
        return re.sub('^(.(?!\\'+symbol+'))*.\\'+symbol,'',msg)   
    

def feed_message_suffix_strip(msg,symbol):
    if symbol in SUFFIX_REGULAR_EXPRESSION: 
        msg_strip=re.sub(SUFFIX_REGULAR_EXPRESSION[symbol],'',msg)
        if symbol in ['()','[]',':']:
            if len(msg)==len(msg_strip):
                msg_strip=re.sub(SUFFIX_REGULAR_EXPRESSION[AFFIX_UTF8_CODE[symbol]],'',msg)
        return msg_strip
    else:
        return re.sub('\\'+symbol+'.(.(?<!\\'+symbol+'))*$','',msg)


class FeedEntry:
    RETURN_ORIGINAL_URL_DOMAINS = ("anrdoezrs.net", )
    SINGLE_KEYWORD_DELIMITERS = "\(|\)|\.|\||\/|-|\,|\;|\:|\<|\>|\=|\ |\'|\""

    def __init__(self, feid, feed_fetcher=None, oe=None, url=None, title=None, keywords=[], updated=None, summary=None, extra={}):
        self.id = feid
        self.feed_fetcher = feed_fetcher
        self.oe = oe
        self.url = url if url else self.parse_url()
        self.title = title if title else self.parse_title()
        self.keywords = keywords if keywords else self.parse_keywords_from_entry()
        self.updated = updated if updated else self.parse_updated_time()
        self.summary = summary if summary else self.parse_summary()
        self.picture = extra.get('picture', None)
        self.htmlText = extra.get('htmlText', None)
        self.contentType = extra.get('contentType', None)
        self.fetch_status = False
        self.globalUrl = extra.get('globalUrl', None)
        self.rank = extra.get('rank', None)
        self.published = extra.get('published', False)
        self.error = False
        self.extra = extra
        
    def __str__(self):
        return "%s %s" % (str_util.encode_utf8_if_ok(self.id), self.url)
        
    def matched_keywords(self, keywords):
        """ Match against multiple text fields: keywords, url, title, summary, picture. """  
        keywords = str_util.normalize(keywords) 
        tokens = str_util.normalize(self.keywords)
        tokens.extend(self._keyword_tokens(self.url))
        tokens.extend(self._keyword_tokens(self.title))
        tokens.extend(self._keyword_tokens(self.summary))
        tokens.extend(self._keyword_tokens(self.picture))
        tokens = Set(tokens)
        matched = []
        for keyword in keywords:
            keyword = str_util.normalize(keyword)
            if keyword and keyword in tokens:
                matched.append(keyword)
        return matched

    def _keyword_tokens(self, text):
        if not text:
            return []
        tokens = re.split(self.SINGLE_KEYWORD_DELIMITERS, text)
        return str_util.normalize(tokens)

    @property
    def full_image(self):
        return self.oe.get('full_image', None) if self.oe else None
        
    def parse_url(self):
        url = self.preprocess_url_wo_fetch(url_util.normalize_url(self.oe.get("link", None))) if self.oe else None
        if not url and self.feed_fetcher and self.oe:
            logging.error("Bad feed entry from feed %s! %s" % (self.feed_fetcher.urlFileStreamOrString, str(self.oe)))
        return url

    def parse_title(self):
        if self.oe:
            title = self.oe.get('title', None)
            if title is None :
                title = self.oe.get('subtitle', '')
                index = title.find('<')
                if index!=-1:
                    title = title[:index]
        else:
            title = None
        if self.feed_fetcher and self.feed_fetcher.is_cmp:
            title = self.feed_fetcher.normalizedEntryTitle(title)
        return title

    def parse_updated_time(self):
        if not self.oe:
            return None
        try:
            return ctz_util.timestamp_2_utc(calendar.timegm(self.oe.updated_parsed))
        except:
            return None

    def parse_summary(self):
        return self.oe.get("summary", None) if self.oe else None

    def parse_keywords_from_entry(self):
        if self.oe and self.oe.has_key("tags"):
            keywords = []
            for tag in self.oe.tags: 
                term = tag.get('term', None)
                if term:
                    keywords.append(term)
            return keywords
        else:
            return []

    def parse_keywords_from_content(self):
        if not self.htmlText:
            return []
        parser = pageparser.SPageParser(self.url)
        parser.feed(self.htmlText)
        return parser.get_keywords()

    def parse_picture(self):
        if self.oe is None:
            return None
        summary = self.oe.get("summary", "")
        s_parser = pageparser.FeedEntryParser()
        s_parser.feed(summary)
        picture = s_parser.img
        if picture is None and self.oe.has_key("content"):
            contents = self.oe['content']
            for content in contents:
                if content['type'] == 'text/html':
                    s_parser = pageparser.FeedEntryParser()
                    s_parser.feed(content['value'])
                    if s_parser.img is not None:
                        picture = s_parser.img
                        break
        if picture is None and self.oe.has_key('media_content') and len(self.oe['media_content'])>0:
            media_content = self.oe['media_content'][0]
            if media_content.has_key('url'):
                picture = media_content['url']
        if picture is None:
            for key in self.oe.keys():
                if key.find('thumbnail') != -1 :
                    try:
                        if self.oe[key].startswith('http'):
                            picture = self.oe[key]
                        else:
                            s_parser = pageparser.FeedEntryParser()
                            s_parser.feed(self.oe[key])
                            if s_parser.img is not None:
                                picture = s_parser.img
                    except:
                        pass
        return picture

    def fetch_content(self):
        self.fetch_status = False
        self.contentType = None
        self.htmlText = None
        if not self.feed_fetcher:
            return
        orig_url = self.url
        self.url = self.preprocess_url_with_fetch(self.url)
        if self.feed_fetcher and self.feed_fetcher.on_blacklist(self.url):
            return
        if not self.url:
            logging.warn("Feed entry URL becomes none! Original URL is %s" % orig_url)
            return
        result = url_util.fetch_redirect_url(self.url)
        self.fetch_status = True
        actual_url = result.actualUrl()
        if not actual_url:
            self.error = True
            return
        actual_url = self.remove_analytics_params(actual_url)
        if self.feed_fetcher.entry_domain_always_diff() and actual_url.decode('utf-8', 'ignore').find(url_util.full_domain(self.feed_fetcher.urlFileStreamOrString)) != -1:
            return
        self.url = orig_url if url_util.root_domain(orig_url) in self.RETURN_ORIGINAL_URL_DOMAINS else actual_url
        self.contentType = result.contentType 
        self.htmlText = result.content

    def populate_heavy_attributes(self):
        """ Disable unnecessary fetches for now. """
        return
        self.picture = self.parse_picture()
        self.keywords.extend(self.parse_keywords_from_content())
        self.keywords = list(set(self.keywords))
                
    @classmethod
    def preprocess_url_wo_fetch(cls, url):
        if is_googlenews_url(url):
            params = url_util.get_params(url)
            return urllib.unquote(params['url']) if params.has_key('url') else url
        else:
            return url

    @classmethod
    def preprocess_url_with_fetch(cls, url):
        return url

    @classmethod
    def remove_analytics_params(cls, url):
        return url_util.remove_ga_params(url)

        
class FeedFetcher:
    DEFAULT_CONTENT_CUTOFF_HOURS = common_const.CONTENT_CUTOFF_HOURS
    def __init__(self, urlFileStreamOrString, parseFeedUrlFromPage=True, contcutoffhours=None):
        self.is_valid = False
        self.urlFileStreamOrString = urlFileStreamOrString
        self.parseFeedUrlFromPage = parseFeedUrlFromPage
        self.contcutoffhours = contcutoffhours if contcutoffhours else self.DEFAULT_CONTENT_CUTOFF_HOURS
        try:
            self.parser = feedparser.parse(urlFileStreamOrString)
            if not self._isParserValid() and parseFeedUrlFromPage:
                pageFeedUrl = pageparser.PageFeedUrlParser(urlFileStreamOrString).findFeedUrl()
                if pageFeedUrl is not None :
                    self.urlFileStreamOrString = pageFeedUrl
                    self.parser = feedparser.parse(self.urlFileStreamOrString)
            if self._isParserValid() :
                self.is_valid = True
                self.feed = self.parser.feed
                self.title = self.feed.get('title', '')
                if self.title=='':
                    self.title = 'Undefined'
                self.encoding = self.parser['encoding']
        except:
            logging.exception("Invalid feed: %s" % urlFileStreamOrString.encode('utf-8', 'ignore'))
        if not self.is_valid:        
            self.parser = None
            self.feed = None
            self.title = None
            self.encoding = None
        self.history = []
        self.feid_history = []
        self.url_history = []
        self.limit = 10
        self.freq = 60
        self.is_cmp = False
        self.blacklist_func = None
        self.ads_func = None
        self.topics = []
        self.channel = None
        self.user = None
        self.required_keywords = []
        self.entry_map = {}
        self.skip_trove_check = False
        
    @classmethod
    def entry_model(cls):
        return FeedEntry
    
    @classmethod
    def max_history(cls):
        return 5
    
    @classmethod
    def fetch_content_by_default(cls):
        return False

    def fetch_content(self):
        return self.fetch_content_by_default() or self.required_keywords

    def normalize_history(self):
        for i in xrange(len(self.history)):
            item = self.history[i]
            try:
                tup = eval(item)
                if isinstance(tup, tuple):
                    if len(tup) == 3:
                        continue
                    elif len(tup) == 2:
                        self.history[i] = unicode((tup[0], tup[1], True))
                        continue
            except:
                pass
            self.history[i] = unicode((item, None, True))
        self.feid_history = [eval(item)[0] for item in self.history]
        self.url_history = []
        for item in self.history:
            item = eval(item)
            if item[2]:
                self.url_history.append(item[1])
            
    def append_history(self, feid, url, good=True):
        url = url_util.normalize_url(url)
        self.history.append(unicode((feid, url, good)))
        self.feid_history.append(feid)
        if good:
            self.url_history.append(url)

    def trim_history(self):
        if self.history:
            limit = self.max_history()
            while len(self.history) > limit:
                self.history.pop(0)
    
    def set_context(self, history=[], limit=common_const.FEED_FETCHER_HISTORY_LIMIT_DEFAULT, freq=60, is_cmp=False, extra={}):
        self.history = history
        self.normalize_history() 
        self.limit = limit
        self.freq = freq
        self.is_cmp = is_cmp
        self.blacklist_func = extra.get('blacklist_func', None)
        self.ads_func = extra.get('ads_func', None)
        self.topics = extra.get('topics', [])
        self.channel = extra.get('channel', None)
        self.user = extra.get('user', None)
        self.skip_trove_check = extra.get('skip_trove_check', False)
        return self

    def _isParserValid(self):
        return self.parser is not None
        
    def url(self):
        return self.urlFileStreamOrString
       
    def init_entry_map(self):
        orig_entries = self.parser.entries
        logging.debug("Total %d original entries for feed url %s" % (len(orig_entries), self.urlFileStreamOrString))
        rank = 1
        for oe in orig_entries:
            feid = self.get_feid(oe)
            fe = self.entry_model()(feid, feed_fetcher=self, oe=oe)
            fe.rank = rank
            rank += 1
            self.entry_map[feid] = fe

    def fetch(self, history, limit=common_const.FEED_FETCHER_HISTORY_LIMIT_DEFAULT, freq=None, is_cmp=False, extra={}):
        """
        limit - maximum entries to return
        freq - feed fetch frequency in minutes
        """
        if not self.is_valid:
            return []
        self.set_context(history, limit, freq, is_cmp, extra)
        entries = self.execute_fetch()
        self.trim_history()
        return entries

    def execute_fetch(self):
        self.init_entry_map()
        orig_entries = self.parser.entries
        fetch_times = 0
        entries = []
        entries.extend(self.get_ads_entries())
        extra_fetch = self.extra_fetch_limit()
        for oe in orig_entries: 
            if len(entries) >= self.limit:
                break
            fetch_times += 1
            if fetch_times >= self.limit + extra_fetch:
                break
            feid = self.get_feid(oe)
            fe = self.entry_map.get(feid, None)
            if fe is None:
                logging.critical("Unexpected feed entry id not found! Must be coding error! %s" % feid)
                continue
            if self.skip_entry_on_quality(fe):
#                 if fe.id not in self.feid_history:
#                     self.append_history(fe.id, fe.url, good=False)
                logging.debug("Skipped post on quality. %s" % fe.url)
                continue
            if self.skip_entry_on_history(fe):
                if self.stop_if_skip_entry_on_history():
                    break
                else:
                    continue
            if self.fetch_content():
                fe.fetch_content()                 
            fe.populate_heavy_attributes()
            if self.skip_entry_on_required_keywords(fe):
                continue
            entries.append(fe)
            self.append_history(feid, fe.url)
        entries.reverse()
        return entries

    def normalizedEntryTitle(self, title):
        return title
  
    def extra_fetch_limit(self):
        return 10

    def entry_domain_always_diff(self):
        return False
    
    def on_blacklist(self, url):
        return self.is_cmp and self.blacklist_func is not None and self.blacklist_func(url, topics=self.topics, channel=self.channel)

    def get_ads_entries(self):
        entries = []
        if self.ads_func:
            ads_entries = self.ads_func(topics=self.topics, channel=self.channel, user=self.user, history=self.history, limit=self.limit)
            for ads_entry in ads_entries:
                self.append_history(ads_entry.id, ads_entry.url)         
                if not ads_entry.published:
                    entries.append(ads_entry)
        return entries

    def skip_entry_on_history(self, fe):
        url_state = trove_const.URL_STATE_UNINGESTED
        if context.is_trove_enabled() and not self.skip_trove_check and not trove_api.is_url_in_unhosted_blacklist(fe.url):
            if context.is_client():
                if trove_api.is_url_in_hosted_whitelist(fe.url):
                    url_state = trove_const.URL_STATE_HOSTED
                else: 
                    url_state = trove_const.URL_STATE_UNHOSTED
            else:
                from sns.url.models import GlobalUrl
                global_url = GlobalUrl.get_or_insert_by_url(fe.url, published_time=fe.updated)
                if global_url and global_url.is_trove_ingested(): 
                    url_state = global_url.troveState
                    logging.debug("Trove ingestion log. Article is ingested with state %d. %s" % (url_state, fe.url))
                else:
                    if trove_api.is_url_in_ingested_whitelist(fe.url):
                        """ The article is expected to be ingested later. Skip for now as if in history. """
                        minutes = datetimeparser.timedelta_in_minutes(datetime.utcnow()- fe.updated) if fe.updated else trove_const.MAX_INGESTION_LATENCY
                        if minutes < trove_const.MAX_INGESTION_LATENCY:
                            logging.info("Trove ingestion log. Article updated %d minutes ago is expected to be ingested later. %s" % (minutes, fe.url))
                            return True
                        else:
                            logging.debug("Trove ingestion log. Article updated %d minutes ago is not expected to be ingested later. %s" % (minutes, fe.url))
                    else:
                        logging.debug("Trove ingestion log. Article is not expected to be ingested. %s" % fe.url)
        if fe.id not in self.feid_history: return False
        domain = url_util.root_domain(fe.url)
        history_limit = self.max_history()
        history_limit = MIN_REPEAT_FREQ_BY_DOMAIN.get(domain, history_limit)
        history_limit = min(history_limit, MIN_REPEAT_FREQ_TROVE[url_state])
        skip = fe.id in self.feid_history[-history_limit:]
        if not skip and fe.id in self.feid_history:
            interval = len(self.feid_history) - self.feid_history.index(fe.id)
            logging.info("Repeating a post with interval of %02d. url_state=%d. %s" % (interval, url_state, fe.url))
        return skip

    def stop_if_skip_entry_on_history(self):
        return True

    def skip_entry_on_quality(self, fe):
        return fe.error or fe.url is None or fe.url == '/' or self.on_blacklist(fe.url)

    def skip_entry_on_required_keywords(self, fe):
        return self.required_keywords and not fe.matched_keywords(self.required_keywords)

    def get_feid(self, oe):
        feid = oe.get('id', None)
        if feid is None or not isinstance(feid, basestring):
            feid = oe.get('link', None)
        if feid is None or not isinstance(feid, basestring):
            return None
        return feid.replace('\n', '')
    

class DynamicFeedFetcher(FeedFetcher):
    def __init__(self, urlFileStreamOrString, parseFeedUrlFromPage=True, contcutoffhours=None):
        FeedFetcher.__init__(self, urlFileStreamOrString, parseFeedUrlFromPage=parseFeedUrlFromPage, contcutoffhours=contcutoffhours)
        
    @classmethod
    def max_history(cls):
        return common_const.FEED_FETCHER_HISTORY_LIMIT_DEFAULT
    
    def get_feid(self, oe):
        title = oe.get("title", "")
        index = title.rfind('-')
        if index != -1:
            title = title[:index]
        return title.replace('\n', '')

    def stop_if_skip_entry_on_history(self):
        return False
    
    def is_good_entry(self, fe):
        return True

    """ For each tuple (x, y), fetch top y entries maximumly x times. """
    REPEAT_TIMES_BY_RANK = ((1, 10), )
    
    """ For each tuple (x, y), fetch x times only if there are at least y entries. """
    REPEAT_TIMES_BY_COUNT = ((2, 20), )

    """ For each tuple (x, y), the same entry can be repeated every x fetches if there are at least y entries.
        Tuples are matched in order. The first matched one is picked.
        Never repeat an entry if it is the only entry available.
    """
    REPEAT_INTERVALS_BY_COUNT = ((20, 20), )
    
    """ All hours are in US/Pacific time. """
    HOUR_WEIGHTS = {
        0: 1,
        1: 1,
        2: 1,
        3: 1,
        4: 1,
        5: 2,
        6: 2,
        7: 2,
        8: 3,
        9: 3,
        10: 3,
        11: 3,
        12: 3,
        11: 3,
        12: 3,
        13: 3,
        14: 3,
        15: 3,
        16: 3,
        17: 2,
        18: 2,
        19: 2,
        20: 1,
        21: 1,
        22: 1,
        23: 1,
        }

    HOUR_RANKS = None
    @classmethod
    def calculate_hour_ranks(cls):
        """ Calculate the hour rank based on weight. Result is a tuple of 24 elements. 
            Top hour is ranked 1. Hours of equal weights are ranked the same.
        """
        weights = cls.HOUR_WEIGHTS.items()
        weights.sort(lambda x,y: cmp(x[1], y[1]), reverse=True)
        ranks = [(weights[0][0], 1)]
        weight = weights[0][1]
        for i in range(1, 24):
            if weights[i][1]==weight:
                ranks.append((weights[i][0], ranks[-1][1]))
            else:
                ranks.append((weights[i][0], len(ranks)+1))
                weight = weights[i][1]
        ranks.sort(lambda x,y: cmp(x[0], y[0]))
        cls.HOUR_RANKS = tuple([item[1] for item in ranks])    

    @classmethod
    def repeat_interval(cls, count):
        for config in cls.REPEAT_INTERVALS_BY_COUNT:
            if count >= config[1]:
                return config[0]
        return None
    
    @classmethod
    def max_repeat_times(cls, count):
        for threshold in cls.REPEAT_TIMES_BY_COUNT:
            if count >= threshold[1]:
                return threshold[0]
        return 1
    
    @classmethod
    def entry_repeat_times(cls, rank, count):
        times = 1
        for tier in cls.REPEAT_TIMES_BY_RANK:
            if rank <= tier[1]:
                times = tier[0]
                break
        max_times = cls.max_repeat_times(count)
        return times if times <= max_times else max_times


DynamicFeedFetcher.calculate_hour_ranks()


class TroveFeedEntry(FeedEntry):
    pass


class TroveFeedFetcher(DynamicFeedFetcher):
    def __init__(self, urlFileStreamOrString, parseFeedUrlFromPage=True, contcutoffhours=None):
        FeedFetcher.__init__(self, urlFileStreamOrString, parseFeedUrlFromPage=True, contcutoffhours=contcutoffhours)

    @classmethod
    def entry_model(cls):
        return TroveFeedEntry
    
    def entry_domain_always_diff(self):
        return True
    
    def extra_fetch_limit(self):
        return 50

    def skip_entry_on_quality(self, fe):
        return DynamicFeedFetcher.skip_entry_on_quality(self, fe) or self.is_cmp and not self.is_good_entry(fe)

    def is_good_entry(self, fe):
        if fe.updated and fe.updated > datetime.utcnow() - timedelta(hours=self.contcutoffhours):
            return True
        else:
            logging.debug("Skipped an old feed entry updated at %s for %s" % (fe.updated, self.urlFileStreamOrString))
            return False


class ComboFeedEntry(FeedEntry):
    def is_trove_hosted(self):
        return self.rights == trove_const.USAGE_RIGHTS_FULL
    
#     def trove_url(self):
#         if not self.is_trove_hosted(): return None
#         trove_id = self.id[len(self.feed.link):]
#         return trove_api.TroveItem.get_trove_url_by_id(trove_id)


class ComboFeedFetcher(TroveFeedFetcher):
    @classmethod
    def entry_model(cls):
        return ComboFeedEntry
    

class GoogleFeedEntry(FeedEntry):
    def to_trove_item(self):
        updated_str = datetime.strftime(self.updated, trove_const.DATETIME_FORMAT)
        return trove_api.TroveItem(trove_id=None, title=self.title, link=self.url, 
                                     updated=updated_str, published=updated_str, usage_rights=trove_const.USAGE_RIGHTS_TBD,
                                     description=None, thumbnail=None, full_image=None)
        

class GoogleFeedFetcher(DynamicFeedFetcher):
    def __init__(self, urlFileStreamOrString, parseFeedUrlFromPage=True, contcutoffhours=None):
        FeedFetcher.__init__(self, urlFileStreamOrString.replace('output=rss', 'output=RSS'), parseFeedUrlFromPage=True, contcutoffhours=contcutoffhours)

    @classmethod
    def entry_model(cls):
        return GoogleFeedEntry
    
    def entry_domain_always_diff(self):
        return True
    
    def normalizedEntryTitle(self, title):
        return feed_message_suffix_strip(title, '-')

    def extra_fetch_limit(self):
        return 20

    def skip_entry_on_quality(self, fe):
        return DynamicFeedFetcher.skip_entry_on_quality(self, fe) or self.is_cmp and not self.is_good_entry(fe)

    def is_good_entry(self, fe):
        if fe.updated and fe.updated > datetime.utcnow() - timedelta(hours=self.contcutoffhours):
            return True
        else:
            logging.debug("Skipped an old feed entry updated at %s for %s" % (fe.updated, self.urlFileStreamOrString))
            return False

    def append_history(self, feid, url, good=True):
        DynamicFeedFetcher.append_history(self, feid, url, good=good)
        self.report_unparsed_googlenews_entry(url)

    def report_unparsed_googlenews_entry(self, url):
        if is_googlenews_url(url):
            logging.error("%s has unparsed Google News url! %s" % (self.__class__.__name__, url))


class BingFeedFetcher(DynamicFeedFetcher):
    def entry_domain_always_diff(self):
        return True
    
    def normalizedEntryTitle(self, title):
        return feed_message_suffix_strip(title, '-')


class RedditFeedEntry(FeedEntry):
    @classmethod
    def preprocess_url_with_fetch(cls, url):
        if url_util.root_domain(url) != "reddit.com":
            return url
        retry = 0
        RETRY_LIMIT = 3
        while retry < RETRY_LIMIT:
            retry += 1
            try:
                try :
                    url = url.encode('utf-8')
                except:
                    pass
                usock = urllib2.urlopen(url)
                info = usock.read()
                parser = pageparser.RedditPageParser(url)
                parser.feed(info)
                if parser.title is not None and parser.title == "service temporarily unavailable":
                    logging.info("Retry on service temporarily unavailable!")
                    continue
                if parser.title and parser.title == "gonewild: over 18?":
                    logging.info("Got 18 content, break!")
                    break
                if parser.reddit:
                    url = parser.reddit
                else:
                    logging.error("Could not get reddit URL for %s with title: %s" % (url, parser.title))
                return url
            except Exception, (errorMsg):
                if str(errorMsg).find('ApplicationError: 5') != -1 or str(errorMsg).find('HTTP Error 503: Service Unavailable') != -1 and retry < RETRY_LIMIT:
                    continue
                else:
                    if str(errorMsg).find('HTTP Error 503') != -1 or str(errorMsg).find('HTTP Error 429') != -1:
                        logging.warning("Reddit redirect error - %s: %s" % (url, errorMsg))
                    else:
                        logging.error("Reddit redirect error - %s: %s" % (url, errorMsg))
                    break
        return url
    

class RedditFeedFetcher(DynamicFeedFetcher):
    @classmethod
    def entry_model(cls):
        return RedditFeedEntry
    
    @classmethod
    def fetch_content_by_default(cls):
        return True

    def entry_domain_always_diff(self):
        return True


class YoutubeFeedFetcher(DynamicFeedFetcher):
    def extra_fetch_limit(self):
        return 50

    def skip_entry_on_quality(self, fe):
        return DynamicFeedFetcher.skip_entry_on_quality(self, fe) or self.is_cmp and not self.is_good_entry(fe)

    def is_good_entry(self, fe):
        vid = url_util.get_youtube_id(fe.url)
        if vid is None:
            return False
        score = self._quality_score(self._get_video_entry(vid))
        if score> YOUTUBE_FEED_ENTRY_QUALITY_THRESHOLD:
            return True
        else:
            logging.debug("Filtered YouTube video with quality score of %d: %s" % (score, fe.url))
            return False

    def _get_video_entry(self, vid):
        try:
            return YouTubeService(developer_key=common_const.YOUTUBE_API_KEY).GetYouTubeVideoEntry(video_id=vid)
        except Exception, ex:
            logging.debug("Failed when fetching YouTube video entry %s. %s" % (vid, str(ex)))
            return None
        
    def _quality_score(self, v_entry):
        if v_entry is None or v_entry.statistics is None:
            return 0
        return int(v_entry.statistics.favorite_count)*100 + int(v_entry.statistics.view_count)        


def get_feed_fetcher(urlFileStreamOrString, parseFeedUrlFromPage=True):
    if is_combo_feed(urlFileStreamOrString):
        return ComboFeedFetcher(urlFileStreamOrString, parseFeedUrlFromPage)
    elif is_googlenews_feed(urlFileStreamOrString):
        return GoogleFeedFetcher(urlFileStreamOrString, parseFeedUrlFromPage)
    elif is_trove_feed(urlFileStreamOrString):
        return TroveFeedFetcher(urlFileStreamOrString, parseFeedUrlFromPage)
    elif is_bing_feed(urlFileStreamOrString):
        return BingFeedFetcher(urlFileStreamOrString, parseFeedUrlFromPage)
    elif is_youtube_feed(urlFileStreamOrString):
        return YoutubeFeedFetcher(urlFileStreamOrString, parseFeedUrlFromPage)
    elif is_dynamic_feed(urlFileStreamOrString):
        return DynamicFeedFetcher(urlFileStreamOrString, parseFeedUrlFromPage)
    else :
        return FeedFetcher(urlFileStreamOrString, parseFeedUrlFromPage)

