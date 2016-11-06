import logging
import datetime
import urllib
from sets import ImmutableSet

from google.appengine.ext import db
import json

import context, deploysns
from common import consts as common_const
from common.utils import string as str_util
from common.utils import datetimeparser
from sns.serverutils import deferred, memcache
from sns.core.core import User, ContentParent, SystemStatusMonitor
from sns.core import core as db_core
from sns.api import consts as api_const
from sns.api.base import BaseProcessor
from sns.chan import consts as channel_const
from sns.chan.models import TAccount
from sns.chan.api import TAccountProcessor
from sns.cont import consts as cont_const
from sns.cont.models import Topic, NoChannelTopic
from sns.cont.feedsources import FeedSource
from sns.cont.api import FeedProcessor
from sns.cont.topic.api import TopicCacheMgr
from sns.url.models import GlobalUrl, GlobalUrlCounter
from sns.camp import consts as camp_const
from sns.camp.api import CampaignProcessor, SCHEDULE_EXPEDITE_FACTOR
from sns.post.models import FeedPostLog
from sns.post import api as post_api
from sns.mgmt.models import ContentCampaign, TopicContentCampaign
from sns.mgmt import consts as mgmt_const


class ContentCampaignProcessor(BaseProcessor):
    def getModel(self):
        return ContentCampaign
    
    def query_base(self, keys_only=False, **kwargs):
        return self.getModel().all(keys_only=keys_only).filter('deleted', False)
    
    def update(self,params):
        rule = db.get(params['id'])
        if rule.syncState == mgmt_const.CMP_RULE_STATE_PENDING:
            logging.error("Rule is in pending state, couldn't be updated!")
            raise Exception
        return BaseProcessor.update(self, params)

    @classmethod
    def deferred_sync(cls, cmp_camp_id):
        context.set_deferred_context(deploy=deploysns)
        cls().sync(cmp_camp_id)

    def sync(self, cmp_camp_id):
        cmp_camp = db.get(cmp_camp_id)
        cmp_camp.syncState = mgmt_const.CMP_RULE_STATE_PENDING
        cmp_camp.put()
        no_topic_count = 0
        wrong_topic_count = 0
        failed = 0
        matched = 0
        channels = TAccountProcessor().execute_query_all(params={'isContent': True})
        logging.info("Started syncing CMP campaign, looping through %d channels." % len(channels)) 
        progress = 0
        for channel in channels:
            progress += 1
            if progress % 1000 == 0:
                logging.info("Progress of syncing CMP campaign: %d." % progress) 
            tags = str_util.split_strip(User.get_by_id(channel.parent().uid).tags, ',')
            if not self._match_cmp_campaign(tags, cmp_camp) or channel.contentCampaign and cmp_camp.priority < channel.contentCampaign.priority:
                continue
            topics = channel.topics
            if len(topics) == 0:
                no_topic_count += 1
                logging.info("None topic for channel %s of user %s." % (channel.name, str(channel.parent().uid)))
                continue
            elif Topic.get_by_topic_key(topics[0]) is None:
                wrong_topic_count += 1
                logging.error("Wrong topic %s for channel %s of user %s!" % (topics[0], channel.name, str(channel.parent().uid)))
                continue
            matched += 1
            if not self._sync_channel_campaign(channel ,cmp_camp):
                failed += 1
        cmp_camp.syncState = mgmt_const.CMP_RULE_STATE_NORMAL
        cmp_camp.put()
        logging.info("Finished syncing CMP campaign '%s' for %d channels: %d no topics, %d wrong topics, %d failures." % (cmp_camp.name, matched, no_topic_count, wrong_topic_count, failed))
            
    def update_channel_campaign(self, channel, keywords):
        topicKeys = []
        for keyword in keywords:
            if not keyword:
                continue
            topic = Topic.get_by_name(keyword)
            if topic is None:
                return False 
            topicKeys.append(topic.keyNameStrip())
        if channel.topics and not topicKeys:
            return self._delete_channel_campaign(channel)
        channel.topics = topicKeys
        tags = str_util.split_strip(User.get_by_id(channel.parent().uid).tags, ',')
        cmp_camps = ContentCampaignProcessor().query_base().order('-priority').fetch(limit=100)
        matched = False
        for cmp_camp in cmp_camps:
            if self._match_cmp_campaign(tags, cmp_camp):
                matched = True
                break
        if not matched:
            return False
        channel.isContent = True
        channel.contentCampaign = cmp_camp
        if channel.cmpFeedCampaign is None:
            feed = FeedProcessor().create_dummy()
            feedRule = post_api.FeedCampaignProcessor().create_dummy()
            feedRule.contents = [feed.key()]
            channel.cmpFeedCampaign = feedRule
        if self._sync_channel_campaign(channel, cmp_camp):
            channel.put()
            return True
        else:
            return False
            
    def _delete_channel_campaign(self, channel):
        try:
            feed_campaign = channel.cmpFeedCampaign
            if feed_campaign.contents:
                feed = db_core.normalize_2_model(channel.cmpFeedCampaign.contents[0])
            else:
                feed = FeedProcessor().create_dummy()
                feed_campaign.contents = [feed.key()]  
            feed_campaign.deleted = True
            feed.deleted = True
            db.put([feed_campaign, feed])
            channel.topics = []
            channel.cmpFeedCampaign = None
            channel.put()
            return True
        except:
            return False 

    def _match_cmp_campaign(self, tags, contentRule):
        if contentRule.filterType == mgmt_const.CMP_RULE_FILTER_TYPE_EXCLUDED_USER:
            etags = str_util.split_strip(contentRule.excludedTags,',')
            for t in tags:
                if t!= '' and t.lower() in etags:
                    return False
            return True
        elif contentRule.filterType == mgmt_const.CMP_RULE_FILTER_TYPE_INCLUDED_USER:
            itags = str_util.split_strip(contentRule.includedTags,',')
            for t in tags:
                if t!= '' and t.lower() in itags:
                    return True
            return False
#        elif contentRule.filterType == mgmt_const.CMP_RULE_FILTER_TYPE_TOPIC:
#            filters = contentRule.filters.strip()
#            filters = str_util.split_strip(filters,',')
#            for f in filters:
#                if keyword.lower() == f.lower():
#                    return True
#            return False
        else:
            return False
    
    def _sync_channel_campaign(self, channel, cmp_camp):
        try:
            channel.contentCampaign = cmp_camp
            if channel.cmpFeedCampaign is None:
                logging.error("Channel '%s' of user %s doesn't have CMP feed campaign!" % (channel.name, channel.parent().uid))
                return False
            feedRule = db_core.normalize_2_model(channel.cmpFeedCampaign)
            for attr in cmp_camp.camp_attrs():
                setattr(feedRule, attr, getattr(cmp_camp, attr))
            keywords = []
            for topic in channel.topics:
                keywords.append(Topic.get_by_topic_key(topic).name)
            keywordStr = '|'.join(keywords)
            fsid, feed_url = cmp_camp.getFeedInfo(keywords)
            fs_name = FeedSource.get_name(fsid)
            feed_name = "CMP - %s - %s" % (keywordStr, fs_name)
            feed = db.get(feedRule.contents[0])
            if feed.name != feed_name or feed.url != feed_url or feed.deleted != channel.deleted: 
                uid = channel.parent().uid
                feedParent = ContentParent.get_or_insert_parent(uid)
                feed = FeedProcessor().update({'parent':feedParent,'name':feed_name,'id':feed.id,'url':feed_url,'encoding':'utf-8','deleted':channel.deleted,'topics':channel.topics})
            feedRule.name = "CMP - %s - %s - %s" % (cmp_camp.name, channel.name, keywordStr) 
            feedRule.nameLower = feedRule.name.lower()
            feedRule.contents = [feed.key()]
            feedRule.channels = [channel.key()]
            feedRule.prefixTitle = False
            feedRule.suffixTitle = False
            feedRule.deleted = channel.deleted
            feedRule.state = camp_const.CAMPAIGN_STATE_ACTIVATED if channel.state == channel_const.CHANNEL_STATE_NORMAL else camp_const.CAMPAIGN_STATE_SUSPENDED
            feedRule.put()
            return True
        except:
            logging.exception("Unexpected error when syncing CMP content channel '%s':" % channel.name)
            return False


class TopicCampaignProcessor(CampaignProcessor):
    @classmethod
    def supportedOperations(cls):
        return ImmutableSet([api_const.API_O_QUERY, api_const.API_O_QUERY_ALL, api_const.API_O_CRON_EXECUTE])
    
    def getModel(self):
        return TopicContentCampaign
    
    def query_base(self, **kwargs):
        return self.getModel().all().filter('deleted', False)
    
    def create(self,params):
        if self.query_base().count()>0:
            raise Exception
        params['scheduleNext'] = datetime.datetime(year=2000,month=1,day=1)
        return BaseProcessor.create(self, params)
    
    def cron_execute(self, params):
        utcnow = datetime.datetime.utcnow()
        instagramMonitor = SystemStatusMonitor.get_system_monitor(cont_const.MONITOR_INSTAGRAM_FETCH)
        if instagramMonitor.work and utcnow.minute%30==0:
            deferred.defer(_deferred_fetch_popular_photos_from_instagram)
        topics = TopicCacheMgr.get_or_build_all_topics()
        rules = TopicCampaignProcessor().query_base().filter('state =', camp_const.CAMPAIGN_STATE_ACTIVATED).filter('scheduleNext <= ', utcnow).order('scheduleNext').fetch(limit=1)
        if len(rules) > 0:
            rule = rules[0]
            interval = datetimeparser.parseInterval(rule.scheduleInterval, memcache.get(SCHEDULE_EXPEDITE_FACTOR))
            rule.scheduleNext = utcnow + interval
            rule.put()
            offset = 0
            noChannels = NoChannelTopic.all().fetch(limit=1000)
            for noChannel in noChannels:
                topicKey = noChannel.key().name()
                topic = Topic.get_by_key_name(Topic.keyName(topicKey))
                if topic is None:
                    db.delete(noChannel)
            try:
                for topic in topics:
                    offset += 1
                    topic_key = topic.keyNameStrip()
                    channels = TAccount.all().filter('topics',topic_key )
                    noChannel = NoChannelTopic.get_by_key_name(topic_key)
                    if channels.count()>0:
                        if noChannel is not None:
                            db.delete(noChannel)
                        logging.debug('Content channel for topic %s'%topic.name)
                    else:
                        if noChannel is None:
                            noChannel = NoChannelTopic(key_name=topic_key,name=topic.name)
                            db.put(noChannel)
                        logging.debug('No content channel for topic %s'%topic.name)
#                        if noChannel.priority != 4:
#                            deferred.defer(_deferred_fetch_content_for_topic, topic, rule.maxMessagePerFeed, rule.feedSources)
            except Exception:
                logging.exception('Unexpected error when set topic content')        


def _deferred_fetch_content_for_topic(topic, maxMessagePerFeed, feedSources):
    context.set_deferred_context(deploysns)
    now = datetime.datetime.utcnow()
    for feedSource in feedSources:
        try:
            feedUrl = FeedSource(feedSource).get_feed_by_topic_names([topic.name])
            record = FeedPostLog.get_or_insert_by_feed_source(topic, feedSource)
            feed_entries = FeedProcessor.get_feed_fetcher_by_url(feedUrl, parseFeedUrlFromPage=False).fetch(
                history=record.feedEntries, 
                limit=maxMessagePerFeed, 
                is_cmp=True, 
                extra={'blacklist_func': post_api.StandardCampaignProcessor.on_cs_blacklist,
                       'topics': [topic.keyNameStrip()],
                       })
            for entry in feed_entries:
                globalUrl = GlobalUrl.get_or_insert_by_feed_entry(entry)
                params = dict(topics=[topic.keyNameStrip()])
                GlobalUrlCounter.get_or_insert_by_url(globalUrl.url(), params=params, clickTime=now)
                record.feedEntries.append(entry.id)
            record.put()    
        except Exception :
            logging.exception("Unexpected error when getting feed URLs for topic %s!" % topic.name)
            

def _deferred_fetch_popular_photos_from_instagram():
    context.set_deferred_context(deploysns)
    logging.info("Begin to fetch instagram popular photos...")
    popularUrl = "https://api.instagram.com/v1/media/popular?client_id=%s" % common_const.INSTAGRAM_CLIENT_ID
    data = urllib.urlopen(popularUrl).read()
    data = json.loads(data)
    for info in data['data']:
        try:
            if info['caption'] is None:
                return
            title = str_util.strip_one_line(info['caption'].get('text', None))
            if title is None:
                return
            url = info['images']['standard_resolution']['url']
            globalUrl = GlobalUrl.get_by_url(url)
            if globalUrl is not None:
                continue
            title = str_util.slice(title, "0:%d" % str_util.DB_STRING_PROTECTIVE_LENGTH)
            globalUrl = GlobalUrl.get_or_insert_by_url(url, params=dict(mediaUrl=url, title=title))
            instagramId = info['id']
            GlobalUrlCounter.get_or_insert_by_url(url, params={'instagramId':instagramId}, clickTime=datetime.datetime.utcnow())
            logging.debug("Finished _deferred_fetch_content_from_instagram() for %s" % url)
        except Exception:
            logging.exception("Unexpected error when fetching instagram content:")


