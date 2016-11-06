import logging
import datetime
import random
from sets import ImmutableSet

from google.appengine.ext import db

import context
from common.utils import string as str_util, url as url_util
from common.content.trove import consts as trove_const
from common.content.trove import api as trove_api
from common.content import feedfetcher
from sns import limits as limit_const
from sns.core.core import ContentParent
from sns.core import base as db_base 
from sns.api import consts as api_const
from sns.api import errors as api_error
from sns.api import base as api_base
from sns.api.base import BaseProcessor
from sns.url.models import GlobalUrl
from sns.deal.api import DealFeedFetcher
from sns.cont import consts as cont_const
from sns.cont import utils as cont_util
from sns.cont.models import ContentPoly, Message, Feed, FeedCC, BaseFeed, MessageShort80, FeedSmall, \
    RawContent, TopicCSContent, CSTopicStats, Domain2CS, FeedFetchLog
from sns.cont.topic.api import TopicCacheMgr


MSG_LENGTH=120
MSG_LENGTH_60=60
MSG_LENGTH_80=80
MSG_LENGTH_100=100


class ContentProcessor(api_base.BaseProcessor):
    def getModel(self):
        return ContentPoly

    def query_base(self,showSmall=False, **kwargs):
        if showSmall:
            model = self.getSmallModel()
        else:
            model = self.getModel()
        q_base = model.all().ancestor(ContentParent.get_or_insert_parent()).filter('deleted', False)
        return q_base
        
        
class MessageProcessor(ContentProcessor):
    def getModel(self):
        return Message
    
    def getSmallModel(self):
        return MessageShort80
    
    @classmethod
    def supportedOperations(cls):
        """"
        Supported public API operations of this processor
        """
        return ImmutableSet([api_const.API_O_ADD_SHORT_MESSAGE]).union(BaseProcessor.supportedOperations())

    def create(self, params):
        if self.isAddLimited():
            raise api_error.ApiError(api_error.API_ERROR_USER_EXCEED_ADD_LIMIT, limit_const.LIMIT_ARTICLE_ADD_PER_USER, 'message') 
        if not params.has_key('parent'): 
            params['parent'] =  ContentParent.get_or_insert_parent()             
        return ContentProcessor.create(self, params)

    def _trans_create(self, params):
        self._trans_create_update(params)
        message = ContentProcessor._trans_create(self, params)
        messageSmall = self.getSmallModel()(msgShort80=str_util.slice_double_byte_character_set(message.msg,80), model=message, parent=message.parent(), deleted=message.deleted)
        messageSmall.put()
        message.smallModel = messageSmall
        message.put()
        return message
        

    def _trans_update(self, params):
        self._trans_create_update(params)
        message = ContentProcessor._trans_update(self, params)
        return message

    def _trans_create_update(self, params):
        params['msg'] = str_util.strip_one_line(params['msg'])
        info_list = ['msgShort60','msgShort80','msgShort100']
        for info in info_list:
            if params.has_key(info):
                params[info] = str_util.strip_one_line(params[info])
        api_base.addLowerProperty(params, "msg", "msgLower") 
        if params.has_key('url'): 
            url = str_util.strip(params.get('url'))
            params['url'] = url

    
    def defaultOrderProperty(self):
        return "msgLower"  

    def isAddLimited(self):        
        size = self.query_base().count(1000)
        if size<limit_const.LIMIT_ARTICLE_ADD_PER_USER:
            return False
        else:
            return True

    
class BaseFeedProcessor(ContentProcessor):
    def getModel(self):
        return BaseFeed
        
    def _trans_create(self, params):
        feed = ContentProcessor._trans_create(self, params)
        feedSmall = self.getSmallModel()(name=feed.name, model=feed, parent=feed.parent(), deleted=feed.deleted)
        feedSmall.put()
        feed.smallModel = feedSmall
        feed.put()
        return feed
    
    def _trans_update(self, params):
        feed = ContentProcessor._trans_update(self, params)
        feedSmall = feed.smallModel
        feedSmall.name = feed.name
        feedSmall.put()
        return feed
    
    @classmethod
    def get_feed_fetcher_by_url(cls, feed_url, parseFeedUrlFromPage=True):
        if DealFeedFetcher.is_deal_feed(feed_url):
            return DealFeedFetcher(feed_url, parseFeedUrlFromPage=parseFeedUrlFromPage)
        else:
            return feedfetcher.get_feed_fetcher(feed_url, parseFeedUrlFromPage=parseFeedUrlFromPage)

    @classmethod
    def is_dynamic_feed(cls, url):
        return DealFeedFetcher.is_deal_feed(url) or feedfetcher.is_dynamic_feed(url) 


class FeedProcessor(BaseFeedProcessor):
    def getModel(self):
        return Feed
    
    def getSmallModel(self):
        return FeedSmall
        
    @classmethod 
    def supportedOperations(cls):
        """"
        Supported public API operations of this processor
        """
        return ImmutableSet([api_const.API_O_QUERY_ALL]).union(BaseProcessor.supportedOperations())

    def create(self, params,check_limit=True):
        if check_limit and self.isAddLimited():
            raise api_error.ApiError(api_error.API_ERROR_USER_EXCEED_ADD_LIMIT, limit_const.LIMIT_FEED_ADD_PER_USER, 'feed') 
        if not params.has_key('parent'):
            user = params.get('user', None)
            uid = user.uid if user else None
            params['parent'] =  ContentParent.get_or_insert_parent(uid=uid)        
        return ContentProcessor.create(self, params)

    def create_dummy(self, user=None):
        params={'name': 'Dummy Feed %d' % random.randint(10000, 99999), 'url': 'http://dummy.dummy/rss'}
        if user: params['user'] = user
        return self.create(params, check_limit=False)

    def defaultOrderProperty(self):
        return "nameLower"  

    def isAddLimited(self):        
        size = self.query_base().count(1000)
        if size<limit_const.LIMIT_FEED_ADD_PER_USER:
            return False
        else:
            return True
        
    
class FeedClickCounterProcessor(BaseProcessor):
    def getModel(self):
        return FeedCC


class RawContentProcessor(api_base.BaseProcessor):
    def getModel(self):
        return RawContent

    @classmethod
    def supportedOperations(cls):
        return ImmutableSet([api_const.API_O_CRON_EXECUTE, 
                           ]).union(BaseProcessor.supportedOperations())
        
    @classmethod
    def get_feed_crawler_jobs(cls):
        return [cont_util.FeedCrawlerJob(cskey=job[0], feed_url=job[1], keywords=job[2]) for job in cont_const.FEED_CRAWLER_LIST] 
                           
    def cron_execute(self, params):
        time_start = datetime.datetime.utcnow()
        fcjs = self.get_feed_crawler_jobs()
        for fcj in fcjs:
            fetch_log = FeedFetchLog.get_or_insert_by_feed_url(fcj.feed_url)
            fetcher = cont_util.FeedCrawlerFeedFetcher(fcj.feed_url)
            entries = fetcher.fetch(history=fetch_log.feedEntries, limit=cont_util.FeedCrawlerFeedFetcher.FETCH_LIMIT, is_cmp=True)
            objs = []
            for fe in entries:
                fe.keywords.extend(fcj.keywords)
                objs.append({
                             'url': fe.url, 
                             'title': fe.title, 
                             'keywords': fe.keywords,
                             'publish_date': fe.updated,
                             'description': fe.summary, 
                             })
            if objs:
                raw_content = self.create({'cskey': fcj.cskey, 'contents': unicode(objs)})
                logging.info("RawContent %d created. Crawled %d articles for feed crawler job %s." % (raw_content.key().id(), len(objs), str(fcj)))
                db.put(fetch_log)
            else:
                logging.info("RawContent not created. Crawled 0 article for feed crawler job %s." % str(fcj))
        time_end = datetime.datetime.utcnow()
        logging.info("Finished executing %d feed crawler jobs in %s." % (len(fcjs), str(time_end - time_start)))
        return len(fcjs)

    
class TopicCSContentProcessor(api_base.BaseProcessor):
    def getModel(self):
        return TopicCSContent

    @classmethod
    def supportedOperations(cls):
        return ImmutableSet([api_const.API_O_CRON_EXECUTE, 
                           ]).union(BaseProcessor.supportedOperations())
                           
    def cron_execute(self, params):
        raw_contents = RawContent.all().fetch(limit=15)
        if len(raw_contents) == 0:
            return 0 
        utc_start = datetime.datetime.utcnow()
        all_topics = TopicCacheMgr.get_or_build_all_topics()
        topics_by_nl = dict([(topic.name.lower(), topic) for topic in all_topics]) 
        topics_by_key = dict([(topic.keyNameStrip(), topic) for topic in all_topics]) 
        for raw_content in raw_contents:
            try:
                cst_stats = CSTopicStats.get_or_insert_by_cskey(raw_content.cskey)
                stats_matched = eval(cst_stats.matched)
                stats_unmatched = eval(cst_stats.unmatched)
                contents_by_topic_cskey = {}
                contents_raw = eval(raw_content.contents)
                for content in contents_raw:
                    content = cont_util.ContentItem(content)
                    for keyword in content.keywords:
                        keyword = str_util.lower_strip(keyword)
                        if not keyword:
                            continue
                        if topics_by_nl.has_key(keyword):
                            if stats_unmatched.has_key(keyword):
                                stats_matched[keyword] = stats_unmatched.pop(keyword) + 1
                            elif stats_matched.has_key(keyword):
                                stats_matched[keyword] += 1
                            else:
                                stats_matched[keyword] = 1
                            topic = topics_by_nl[keyword]
                            for topic_key in topic.ancestors_plus_self():
                                topic_cskey = (topic_key, raw_content.cskey)
                                if contents_by_topic_cskey.has_key(topic_cskey):
                                    contents_tcs = contents_by_topic_cskey.get(topic_cskey)
                                    contents_tcs.append(content)
                                else:
                                    contents_by_topic_cskey[topic_cskey] = [content]
                        else:
                            if stats_unmatched.has_key(keyword):
                                stats_unmatched[keyword] += 1
                            else:
                                stats_unmatched[keyword] = 1
                cst_stats.update(stats_matched, stats_unmatched)
                topic_csc_objs = []
                for topic_cskey, contents_tcs in contents_by_topic_cskey.items():
                    topic_key, cskey = topic_cskey
                    topic = topics_by_key[topic_key]
                    topic_csc = TopicCSContent.get_or_insert_by_topic_cskey(topic_key, cskey)
                    topic_csc.add(contents_tcs)
                    topic_csc.topics = topic.ancestors_plus_self()
                    topic_csc_objs.append(topic_csc)
                db_base.put(topic_csc_objs)
                logging.info("Updated %d TopicCSContent objects." % len(topic_csc_objs))
                db.delete(raw_content)
                logging.info("Finished importing %d contents from RawContent %d of content source %d." % (len(contents_raw), raw_content.key().id(), raw_content.cskey))
                db.put(cst_stats)
                logging.info("Content importing stats for content source %d: %s" % (raw_content.cskey, cst_stats.summary()))
            except:
                logging.exception("Failed processing raw content %d." % raw_content.key().id())
        utc_end = datetime.datetime.utcnow()
        logging.info("Finished importing %d blocks of raw contents in %s." % (len(raw_contents), utc_end - utc_start))
        return len(raw_contents)
    

class Domain2CSProcessor(api_base.BaseProcessor):
    def getModel(self):
        return Domain2CS

    def get_cskey_by_url(self, url, skip_trove=False, context_sensitive=False):
        if not url: return None
        if url and url.find('click-5517529') != -1:
            return cont_const.CS_DEALS
        if context.is_trove_enabled() and not skip_trove:
            if context_sensitive:
                ctx = context.get_context()
                is_iphone, is_phone = ctx.is_iphone(), ctx.is_phone()
            else:
                is_iphone, is_phone = False, False
            global_url = GlobalUrl.get_by_url(url)
            if global_url and global_url.is_trove_ingested():
                if global_url.troveState == trove_const.URL_STATE_HOSTED:
                    return cont_const.CS_TROVE_HOSTED
                elif trove_api.is_url_eligible_for_visor(url, is_iphone=is_iphone, is_phone=is_phone):
                    return cont_const.CS_TROVE_UNHOSTED
                else:
                    return None
        domain = str_util.lower_strip(url_util.root_domain(url))
        return self.get_cskey_by_domain(domain)

    def get_cskey_by_domain(self, domain):
        if not domain:
            return None
        cskey = cont_const.DOMAIN_2_CS_MAP.get(domain, None)
        if cskey:
            return cskey
        domain_2_cs = Domain2CS.pull(domain)
        return domain_2_cs.cskey if domain_2_cs else domain


