import time, datetime
from sets import ImmutableSet
import logging

from google.appengine.ext import db
import feedparser

import context, deploysns
from common.utils import string as str_util
from common.utils import url as url_util
from common.utils import django as django_util
from common.content import feedfetcher
from sns.core.core import ContentParent, SystemStatusMonitor 
from sns.api import consts as api_const
from sns.api.base import BaseProcessor
from sns.serverutils import deferred
from sns.feedbuilder.models import FeedBuilder, FeedBuilderSmall, ComboFeedBuilder, TopicScoreFeedBuilder, TroveFeedBuilder
from sns.camp import consts as camp_const
from sns.cont import consts as cont_const
from sns.cont.models import Topic
from sns.cont.api import BaseFeedProcessor


def _deferredExecuteOneHandler(processorClass):
    context.set_deferred_context(deploy=deploysns)
    return processorClass().execute()


class FeedBuilderProcessor(BaseFeedProcessor):
    def getModel(self):
        return FeedBuilder
    
    def getSmallModel(self):
        return FeedBuilderSmall
    
    @classmethod
    def supportedOperations(cls):
        return ImmutableSet([api_const.API_O_EXECUTE, 
                           api_const.API_O_CRON_EXECUTE, 
                           ]).union(BaseProcessor.supportedOperations())

    def create(self, params):
        key_name = FeedBuilder.keyName(params['uri'])
        paramsCopy = params.copy()
        paramsCopy['key_name'] = key_name
        paramsCopy['parent'] =  ContentParent.get_or_insert_parent()   
        return BaseProcessor.create(self, paramsCopy)
            
    def execute(self, params):
        if SystemStatusMonitor.is_locked(cont_const.MONITOR_FEED_BUILDER_SWITCH):
            logging.info("Turned off feed builder execution.")
            return
        deferred.defer(self.__class__.deferred_execute, queueName='feedbuilder')
        return
    
    def cron_execute(self, params):
        return self.execute(params)
    
    @classmethod
    def deferred_execute(cls):
        context.set_deferred_context(deploy=deploysns)
        return cls()._execute()

    def _execute(self):
        if not SystemStatusMonitor.acquire_lock(cont_const.MONITOR_FEED_BUILDER_EXECUTE, preempt=300):
            return 0
        utcnow = datetime.datetime.utcnow()
        activeQuery = self.getModel().all().filter('deleted',False).filter('state', camp_const.CAMPAIGN_STATE_ACTIVATED).filter('scheduleNext <= ',utcnow).order('scheduleNext')
        builders = activeQuery.fetch(limit=10)
        if len(builders)>0:
            self.logScheduleDelayStatus(builders[0].scheduleNext)
        logging.info("Kicked off %d active feed builders." % len(builders))
        for builder in builders:
            try:
                self._executeOne(builder)
            except:
                logging.exception("Error when executing feed builder '%s'." % builder.name)
        SystemStatusMonitor.release_lock(cont_const.MONITOR_FEED_BUILDER_EXECUTE)
        return len(builders)
    
    def _executeOne(self, builder):
        logging.info("Start building %d entries for the feed builder." % len(builder.feeds)*FeedBuilder.MAXIMUM_ENTRY_PER_FEED)
        old_items = {}
        for it in builder.items:
            its = eval(it)
            if its.has_key('oLink'):
                old_items[its['oLink']] = it
        items = []
        links = []
        for feedId in builder.feeds:
            order = 0
            fetched = 0
            skipped = 0
            feed = db.get(feedId)
            self._reddit_sleep()
            parsed = feedparser.parse(feed.feedUrl())
            entries = parsed.entries[:5]
            while fetched < FeedBuilder.MAXIMUM_ENTRY_PER_FEED and order < len(entries)-1:
                order += 1
                e = entries[order]
                link = e.get("link","")
                if link != "" and link not in links:
                    if old_items.has_key(link):
                        logging.debug("Link already exists, skipping url fetch!")
                        items.append((old_items[link],order))
                    else:
                        self._reddit_sleep()
                        oLink = link
                        link = feedfetcher.RedditFeedEntry.preprocess_url_with_fetch(link)
                        if url_util.root_domain(link) == "reddit.com" or not link:
                            skipped += 1
                            continue
                        links.append(oLink)
                        item = {}
                        item['oLink'] = oLink
                        item['link'] = link
                        item['title'] = e.get('title', '')
                        item['description'] =  e.get('summary', '')
                        items.append((str(item),order))
                        fetched += 1
            logging.info("Fetched %d and skipped %d out of total %d entries from feed %s" % (fetched, skipped, len(parsed.entries), feed.feedUrl()))
            if skipped>0 and fetched==0:
                logging.warning("Invalid feed %s for feed builder %s of user %s" % (feed.feedUrl(), builder.name, feed.parent().keyNameStrip()))
        if len(items) == 0:
            pass
        else:
            items.sort(lambda y,x: cmp(x[1], y[1]),reverse=True)
            builder.items = []
            for i in items:
                builder.items.append(db.Text(i[0]))
        totalTime = datetime.datetime.utcnow() - builder.createdTime
        t = (totalTime.days*24*3600+totalTime.seconds)/FeedBuilder.EXECUTION_INTERVAL
        builder.scheduleNext = builder.createdTime + (t+1)*datetime.timedelta(seconds=FeedBuilder.EXECUTION_INTERVAL)
        builder.put()
        
    def _reddit_sleep(self):
        time.sleep(3)

    @classmethod
    def get_feed_fetcher_by_feed(cls, feed, parseFeedUrlFromPage=True):
        feed_url = feed.feedUrl()
        topic_key = feed.topics[0] if feed.topics else None
        if topic_key and feedfetcher.is_googlenews_feed(feed_url):
            feed_content = ComboFeedBuilderProcessor().fetch_content_by_topic_key(topic_key)
            return feedfetcher.ComboFeedFetcher(feed_content, parseFeedUrlFromPage=False)
        else:
            return cls.get_feed_fetcher_by_url(feed_url, parseFeedUrlFromPage=parseFeedUrlFromPage)
    

class BaseFeedBuilderProcessor(BaseProcessor):
    FEED_TITLE_PATTERN = None
    FEED_DESCRIPTION_PATTERN = None
    
    def getModel(self):
        pass
    
    def fetch_content_by_topic_key(self, topic_key):
        topic_key = str_util.lower_strip(topic_key)
        builder = self.getModel().get_or_insert_by_topic_key(topic_key)
        entries = builder.fetch()
        if not builder:
            return None
        topic = Topic.get_by_topic_key(topic_key)
        topic_name = topic.name if topic else topic_key
        feed_title = self.FEED_TITLE_PATTERN % topic_name
        feed_description = self.FEED_DESCRIPTION_PATTERN % topic_name
        f = django_util.SNSFeed(title=feed_title, description=feed_description, link=self.getModel().get_feed_url(topic_key))
        for entry in entries:
            f.add_item(title=entry.title, link=entry.link, description=entry.description, pubdate=entry.published_time, 
                       unique_id=entry.trove_id, item_copyright=entry.usage_rights, full_image=entry.full_image)
        info = f.writeString('utf-8')
        return info


class ComboFeedBuilderProcessor(BaseFeedBuilderProcessor):
    FEED_TITLE_PATTERN = "SNS News - %s"
    FEED_DESCRIPTION_PATTERN = "SNS news feed for the topic - %s"
    
    def getModel(self):
        return ComboFeedBuilder


class TopicScoreFeedBuilderProcessor(BaseFeedBuilderProcessor):
    FEED_TITLE_PATTERN = "SNS Topic Score - %s"
    FEED_DESCRIPTION_PATTERN = "SNS topic score news feed - %s"
    
    def getModel(self):
        return TopicScoreFeedBuilder

    @classmethod
    def supportedOperations(cls):
        return ImmutableSet([api_const.API_O_CRON_EXECUTE, 
                           ]).union(BaseProcessor.supportedOperations())

    def cron_execute(self, params):
        context.set_deferred_context(deploy=deploysns)
        try:
            topics = Topic.all().order('modifiedTime').fetch(limit=20)
            for topic in topics:
                topic_key = topic.keyNameStrip()
                builder = TopicScoreFeedBuilder.get_or_insert_by_topic_key(topic_key)
                builder.fetch()
                topic.scoreupdated = datetime.datetime.utcnow()
            db.put(topics)
            logging.info("Finished refreshing scores for 20 topics!")
        except:
            logging.exception("Unexpected error when refreshing topic scores!")


class TroveFeedBuilderProcessor(BaseFeedBuilderProcessor):
    FEED_TITLE_PATTERN = "Trove News - %s"
    FEED_DESCRIPTION_PATTERN = "Trove news feed - %s"
    
    def getModel(self):
        return TroveFeedBuilder


    
