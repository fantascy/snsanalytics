import logging
import datetime
import urllib

from google.appengine.ext import db
from google.appengine.ext.db import polymodel

from search import core as search

import context
from common.utils import string as str_util, url as url_util
from common.utils import topic as topic_util
from sns.serverutils import memcache
from sns.core import core as db_core
from sns.core.base import SoftDeleteBaseModelPoly, SoftDeleteModelPolySmall, ClickCounterNoIndex, NamedBaseModel, \
    CreatedTimeBaseModel, ModifiedTimeBaseModel, DatedNoIndexBaseModel
from sns.cont import consts as cont_const
from sns.cont import utils as cont_util


class ContentPolySmall(polymodel.PolyModel, SoftDeleteModelPolySmall):
    pass


class ContentPoly(polymodel.PolyModel, SoftDeleteBaseModelPoly, url_util.UrlIF):
    smallModel = db.ReferenceProperty(ContentPolySmall)
    
    def getTopics(self):
        return []

    def getFirstTopic(self):
        topics = self.getTopics()
        if len(topics)==0 :
            return None
        else :
            return topics[0]


class Message(ContentPoly):
    msg = db.StringProperty(required=True, indexed=False)
    msgLower = db.StringProperty(required=True)       
    msgShort60 = db.StringProperty(indexed=False)
    msgShort80 = db.StringProperty(indexed=False)
    msgShort100 = db.StringProperty(indexed=False)
    type = db.IntegerProperty(default=0) 
    url = db.StringProperty(indexed=False)
    searchIndex = search.SearchIndexProperty(('msg','url'), indexer=search.porter_stemmer,relation_index=False)
    
    def __unicode__(self):
        return "%s %s" % (self.msg, self.url)


class MessageShort80(ContentPolySmall):
    msgShort80 = db.StringProperty()

    @classmethod
    def syncAttributes(cls):
        return ["msgShort80"]


class BaseFeed(ContentPoly):
    name = db.StringProperty(required=True)
    nameLower = db.StringProperty(required=True)


class Feed(BaseFeed):
    url = db.StringProperty(required=True)
    encoding = db.StringProperty(indexed=False)
    topics = db.StringListProperty()
    searchIndex = search.SearchIndexProperty(('name','url'), indexer=search.porter_stemmer,relation_index=False)

    @classmethod
    def uniqueness_properties(cls) :
        return []
    
    def feedUrl(self):
        return self.url
        
    def __unicode__(self):
        return "%s %s %s" % (self.feedUrl(), self.name, self.originalUrl())
    
    def getTopics(self):
        return self.topics


class FeedSmall(ContentPolySmall):
    name = db.StringProperty(required=True)

    @classmethod
    def syncAttributes(cls):
        return ["name"]


class FeedCC(ClickCounterNoIndex, db_core.KeyName):
    @classmethod
    def keyNamePrefix(cls):
        return "FeedCC:"

    @classmethod
    def normalizedName(cls, url):                            
        return url_util.normalize_url(url)

    @classmethod
    def key_name_by_feed(cls, feed):
        keyNameStrip = str(feed.key().id())
        contentParent = feed.parent()
        if contentParent is not None :
            parentKey = db_core.normalize_2_key(contentParent)
            keyNameStrip = "%s:%s" % (parentKey.id_or_name(), keyNameStrip)
        return cls.keyName(keyNameStrip)

    @classmethod
    def get_or_insert_update_by_feed(cls, feed, parent=None):
        if parent is None :
            parent = db_core.UserClickParent.get_or_insert_parent()
        ccKeyName = cls.key_name_by_feed(feed)
        return FeedCC.get_or_insert_update(ccKeyName, parent=parent)

    @classmethod
    def get_or_insert_by_feed(cls, feed, parent=None):
        if parent is None :
            parent = db_core.UserClickParent.get_or_insert_parent()
        ccKeyName = cls.key_name_by_feed(feed)
        return FeedCC.get_or_insert(ccKeyName, parent=parent)



class TopicKeyName(db_core.KeyName):
    @classmethod
    def keyNamePrefix(cls):
        return "Topic:"


class Topic(NamedBaseModel, TopicKeyName):
    """ 
    TODO: Each topic should save both child topics and parent topics to save time.
    API update/create logic should make sure all child topics, parent topics, related topics are in sync.  
    """
    description = db.TextProperty()
    image = db.TextProperty()
    fbTopic = db.StringProperty(indexed=False)
    ancestorTopics = db.StringListProperty()
    parentTopics = db.StringListProperty()
    childTopics = db.StringListProperty(indexed=False)
    relatedTopics = db.StringListProperty()
    isLevel1 = db.BooleanProperty(default=False)
    treeSizeP1 = db.IntegerProperty(indexed=False)
    c24h = db.IntegerProperty()
    tags = db.StringListProperty()
    ext = db.TextProperty() #Any extended info  
    searchIndex = search.SearchIndexProperty(('name', 'tags'), indexer=search.porter_stemmer,relation_index=False)

    TOPIC_KEY_FRONTPAGE = "frontpage"
    TOPIC_KEY_PHOTOS = "photos"
    TOPIC_KEY_VIDEOS = "videos"
    SPECIAL_TOPIC_KEYS = (TOPIC_KEY_FRONTPAGE, TOPIC_KEY_PHOTOS, TOPIC_KEY_VIDEOS)

    @classmethod
    def is_special_topic_key(cls, topicKey):
        return topicKey in cls.SPECIAL_TOPIC_KEYS
    
    @classmethod
    def get_by_name(cls, name):
        default_topic_key = str_util.name_2_key(name)
        topic = cls.get_by_topic_key(default_topic_key)
        if topic and topic.name == name: return topic
        topics = Topic.all().filter('nameLower', str_util.lower_strip(name)).fetch(limit=1)
        return topics[0] if topics else None
    
    def fbTopicSelf(self):
        if self.fbTopic is None or self.fbTopic=="self":
            return True
        else :
            return False

    def fbTopicObj(self):
        if self.isFbTopicSelf() :
            return self
        else :
            return Topic.get_by_name(self.fbTopic)

    def add_tag(self, tag):
        tag = str_util.lower_strip(tag)
        if tag and tag not in self.tags:
            self.tags.append(tag)
        
    def remove_tag(self, tag):
        tag = str_util.lower_strip(tag)
        if tag and tag in self.tags:
            self.tags.remove(tag)

    def ext_get_attr(self, attr):
        ext = eval(self.ext) if self.ext else {}
        return ext.get(attr, None)
        
    def ext_set_attr(self, attr, value):
        ext = eval(self.ext) if self.ext else {}
        ext[attr] = value
        self.ext = str(ext)
        
    def ancestors_plus_self(self):
        return [self.keyNameStrip()] + self.ancestorTopics
            
    @classmethod
    def cake_frontpage_topic(cls):
        return CAKE_FRONTPAGE_TOPIC

    @classmethod
    def soup_frontpage_topic(cls):
        return SOUP_FRONTPAGE_TOPIC

    @classmethod
    def get_frontpage_topic(cls):
        """ Make sure context is initialized before this function is called. """
        return FRONTPAGE_TOPIC_MAP.get(context.get_context().app(), None)

    @classmethod
    def get_photos_topic(cls):
        return CAKE_TOPIC_PHOTOS

    @classmethod
    def get_videos_topic(cls):
        return CAKE_TOPIC_VIDEOS

    @classmethod
    def _get_topic_info(cls, topicKey):
        return memcache.get(cont_const.TOPIC_MEM_KEY_PREFIX + topicKey)
    
    @classmethod
    def get_by_topic_key(cls, topicKey):
        topicKey = str_util.lower_strip(topicKey)
        if topicKey is None or topicKey == Topic.TOPIC_KEY_FRONTPAGE :
            return cls.get_frontpage_topic()
        if topicKey==Topic.TOPIC_KEY_PHOTOS :
            return cls.get_photos_topic()
        if topicKey==Topic.TOPIC_KEY_VIDEOS :
            return cls.get_videos_topic()
        topic = memcache.get(cont_const.TOPIC_MEM_KEY_PREFIX + topicKey)
        if topic is None:
            topic = Topic.get_by_key_name(Topic.keyName(topicKey))
            if topic is not None :
                memcache.set(cont_const.TOPIC_MEM_KEY_PREFIX + topicKey, topic)
            else :
                logging.info("Topic key '%s' doesn't exist!" % topicKey)
        return topic
    
    @classmethod
    def get_child_topic_keys(cls, topicKey):
        topic = cls.get_by_topic_key(topicKey)
        if topic is None or topic.childTopics is None :
            return []
        return topic.childTopics

    @classmethod
    def get_topics_for_new(cls,key):
        if key is None :
            return []
        new = [key]
        topic = cls.get_by_topic_key(key)
        if topic is not None and len(topic.parentTopics) > 0:
            for t in topic.parentTopics:
                new.append(t)
        return new

    @classmethod
    def keys_2_objs(cls, keys):
        if not keys: return []
        topics = []
        for key in keys:
            topic = cls.get_by_topic_key(key)
            if topic is not None:
                topics.append(topic)
        return topics

    @classmethod
    def key_2_name(cls, key):
        if not key: return None
        topic = cls.get_by_topic_key(key)
        return topic.name if topic else None
        
    @classmethod
    def name_2_key(cls, name):
        if not name: return None
        topic = Topic.get_by_name(name)
        return topic.keyNameStrip() if topic else None
    
    @classmethod
    def canonical_name(cls, name):
        return topic_util.canonical_name(name)


class TopicTargets(ModifiedTimeBaseModel, TopicKeyName):
    targets = db.TextProperty()
    
    @classmethod
    def get_targets(cls, topic_key):
        obj = cls.get_by_key_name(cls.keyName(topic_key))
        if not obj: return None
        return eval(obj.targets)
    
    @classmethod
    def set_targets(cls, topic_key, id_handle_list):
        """ id_handle_list in the format of [(id1, 'handle1'), (id2, 'handle2'), ...] """
        obj = cls.get_or_insert(cls.keyName(topic_key))
        targets = str([(new_target[0], new_target[1]) for new_target in id_handle_list])
        if obj.targets != targets:
            obj.targets = targets
            obj.put()

    @classmethod
    def add_targets(cls, topic_key, id_handle_list):
        """ id_handle_list in the format of [(id1, 'handle1'), (id2, 'handle2'), ...] """
        obj = cls.get_or_insert(cls.keyName(topic_key))
        targets = eval(obj.targets) if obj.targets else []
        existing_len = len(targets)
        user_ids = set([target[0] for target in targets])
        for new_target in id_handle_list:
            if new_target[0] in user_ids: continue
            targets.append((new_target[0], new_target[1]))
        if len(targets) > existing_len:
            obj.targets = str(targets)
            obj.put()
            
    @classmethod
    def has_target(cls, topic_key, user_id):
        targets = cls.get_targets(topic_key)
        return dict(targets).has_key(int(user_id)) if targets else False

    @classmethod
    def get_next_target(cls, topic_key, current_user_id, current_user_id_active=True):
        targets = cls.get_targets(topic_key)
        if not targets: return (None, None)
        current_user_id_valid = False
        for i in xrange(len(targets)):
            if targets[i][0] == current_user_id: 
                current_user_id_valid = True
                break
        if not current_user_id_valid: return targets[0]
        if current_user_id_active: 
            return targets[i]
        elif len(targets)==1:
            return (None, None)
        else:
            return targets[(i + 1) % len(targets)]


class NoChannelTopic(db.Model):
    name = db.StringProperty()
    priority = db.IntegerProperty(default=0)
    searchIndex = search.SearchIndexProperty(('name',), indexer=search.porter_stemmer,relation_index=False)


SOUP_FRONTPAGE_TOPIC = Topic(
                         name="All",
                         nameLower="all",
                         description="Socially curated news, pictures, videos, and comments.",
                         key_name = Topic.keyName(Topic.TOPIC_KEY_FRONTPAGE),
                         fbTopic=None,
                         twitter = "allnewsoup",
                         parentTopics = [],
                         ancestorTopics = [],
                         childTopics = [],
                         relatedTopics = [],
                    )


CAKE_FRONTPAGE_TOPIC = Topic(
                         name="All Topics",
                         nameLower="all topics",
                         description="Socially curated news, pictures, videos, and comments.",
                         key_name = Topic.keyName(Topic.TOPIC_KEY_FRONTPAGE),
                         fbTopic=None,
                         twitter = "rippleone",
                         parentTopics = [],
                         ancestorTopics = [],
                         childTopics = [],
                         relatedTopics = [],
                    )

FRONTPAGE_TOPIC_MAP = {
                        "soup" : SOUP_FRONTPAGE_TOPIC,
                        "cake" : CAKE_FRONTPAGE_TOPIC,
                        }

CAKE_TOPIC_PHOTOS = Topic(
                         name="Photos",
                         nameLower="photos",
                         description="Socially curated photos and comments.",
                         key_name = Topic.keyName(Topic.TOPIC_KEY_PHOTOS),
                         fbTopic=None,
                         twitter = "rippleone",
                         parentTopics = [],
                         ancestorTopics = [],
                         childTopics = [],
                         relatedTopics = [],
                    )

CAKE_TOPIC_VIDEOS = Topic(
                         name="Videos",
                         nameLower="videos",
                         description="Socially curated videos and comments.",
                         key_name = Topic.keyName(Topic.TOPIC_KEY_VIDEOS),
                         fbTopic=None,
                         twitter = "rippleone",
                         parentTopics = [],
                         ancestorTopics = [],
                         childTopics = [],
                         relatedTopics = [],
                    )


class RawContent(CreatedTimeBaseModel):
    cskey = db.IntegerProperty()
    contents = db.TextProperty()


class TopicCSContent(DatedNoIndexBaseModel, db_core.KeyName):
    """
    Store contents based on a combined key of topic and content source.
    Store no more than LIMIT_PER_TOPIC_CS pieces of contents per key.
    """
    CONTENT_LIMIT_DEFAULT = 500
    CONTENT_LIMIT_BY_CS = {cont_const.CS_EXAMINER: 100}  
    cskey = db.IntegerProperty()
    topics = db.StringListProperty()
    contents = db.TextProperty(default='[]')

    @classmethod
    def keyNamePrefix(cls):
        return "TopicCSC:"
    
    @classmethod
    def key_name_by_topic_cskey(cls, topic, cskey):
        return "%s%s_%d" % (cls.keyNamePrefix(), topic, cskey)
    
    @classmethod
    def get_or_insert_by_topic_cskey(cls, topic, cskey):
        return cls.get_or_insert(cls.key_name_by_topic_cskey(topic, cskey), cskey=cskey)
    
    def get_content_limit(self):
        self.CONTENT_LIMIT_BY_CS.get(self.cskey, self.CONTENT_LIMIT_DEFAULT)
        
    def add(self, contents):
        old_contents = eval(self.contents) if self.contents else []
        old_contents = [cont_util.ContentItem(content) for content in old_contents]
        merged = cont_util.ContentItem.merge_sort(old_contents, contents)
        merged = merged[:self.get_content_limit()]
        merged = [item.to_dict() for item in merged]
        self.contents = unicode(merged)

    def get_contents(self, contcutoffhours=0):
        try:
            if self.contents: 
                contents = eval(self.contents)
                if not contcutoffhours:
                    return contents
                cutoff_time = datetime.datetime.utcnow() - datetime.timedelta(hours=contcutoffhours)
                start = 0
                end = len(contents) - 1
                index = (start + end) / 2
                while index > start and index < end and start < end:
                    if contents[index]['publish_date'] == cutoff_time:
                        break 
                    elif contents[index]['publish_date'] > cutoff_time:
                        start = index + 1
                    else:
                        end = index - 1
                    index = (start + end) / 2
                if index < end:
                    logging.info("TopicCSC: Cutoff at %d out of %d contents. Cutoff time is %s. Cutoff at %s. Previous entry time is %s." % (index, len(contents), str(cutoff_time), str(contents[index]['publish_date']), str(contents[index+1]['publish_date']))) 
                return contents[:index + 1]
            else:
                return []
        except:
            logging.exception("Invalid content! %s %s" % (self.key().name(), self.contents))
            return []


class CSTopicStats(DatedNoIndexBaseModel):
    matched = db.TextProperty(default="{}")
    unmatched = db.TextProperty(default="{}")
    content_count = db.IntegerProperty(default=0, indexed=False)
    matched_content_count = db.IntegerProperty(default=0, indexed=False)
    topic_count = db.IntegerProperty(default=0, indexed=False)
    matched_topic_count = db.IntegerProperty(default=0, indexed=False)
    
    @classmethod
    def get_or_insert_by_cskey(cls, cskey):
        return cls.get_or_insert(cskey)
    
    def cskey(self):
        return int(self.key().name())

    def update(self, matched, unmatched):
        self.matched_topic_count = len(matched)
        self.topic_count = self.matched_topic_count + len(unmatched)
        self.matched_content_count = sum(matched.values()) if matched else 0
        unmatched_content_count = sum(unmatched.values()) if matched else 0
        self.content_count = self.matched_content_count + unmatched_content_count
        self.matched = unicode(matched)
        self.unmatched = unicode(unmatched)
            
    def summary(self):
        return "Total %d topics, matched %d, unmatched %d. Total %d contents, matched %d, unmatched %d." % (
                self.topic_count, self.matched_topic_count, (self.topic_count - self.matched_topic_count), 
                self.content_count, self.matched_content_count, (self.content_count - self.matched_content_count)) 


class Domain2CS(DatedNoIndexBaseModel, db_core.MemcachedIF):
    cskey = db.StringProperty()

    @classmethod
    def keyNamePrefix(cls):
        return "Domain2CS:"


class FeedFetchLog(DatedNoIndexBaseModel, db_core.KeyName):
    feedEntries = db.StringListProperty(indexed=False)
    
    @classmethod
    def keyNamePrefix(cls):
        return "FeedFetchLog:"

    @classmethod
    def key_name_by_feed_url(cls, feed_url):
        return cls.keyName(urllib.quote_plus(url_util.normalize_url(feed_url)))

    @classmethod
    def get_or_insert_by_feed_url(cls, feed_url):
        return cls.get_or_insert(cls.key_name_by_feed_url(feed_url))




