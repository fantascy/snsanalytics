import logging
import urllib
from datetime import datetime
import random
import string
from math import floor

from google.appengine.ext import db
from google.appengine.api.images import NotImageError, BadImageError
import json
from gdata.youtube.service import YouTubeService

import deploysoup
import context
from common import consts as common_const
from common.utils import string as str_util, url as url_util
from common.s3 import upload
from common.utils import datetimeparser
from common.content import pageparser
from common.content.trove import consts as trove_const
from common.content.trove import api as trove_api
from sns.serverutils import memcache
from sns.core import core as db_core
from sns.core.base import BaseModel, CreatedTimeBaseModel, ClickCounter, RatingCounter, DatedBaseModel
from sns.cont.models import Topic
from sns.post import consts as post_const
from sns.post.models import SPost
from sns.url import consts as url_const


class ShortUrlGenerator(db.Model, db_core.KeyName):
    cursor = db.IntegerProperty(required=True, default=0)

    @classmethod
    def keyNamePrefix(cls):
        return "ShortUrlGenerator:"

    @classmethod
    def get_by_first_char(cls, first_char):
        return ShortUrlGenerator.get_or_insert(key_name=ShortUrlGenerator.keyName(first_char))


class ShortUrlReserve(db.Model):
    resvBlock = db.ListProperty(long,indexed=False)
    resvBlockSize = db.ListProperty(int,indexed=False)
    firstCharacter = db.StringProperty(indexed=False)

    def totalSize(self):
        total_size = 0
        for size in self.resvBlockSize :
            total_size += size
        return total_size

    def status(self):
        idResv = ','.join([str(v) for v in self.resvBlock]) 
        sizeResv = ','.join([str(v) for v in self.resvBlockSize])
        return "User '%s' short URL reserve status: [%s] [%s]" % (self.key().name(), idResv, sizeResv) 
    
    def save(self, resv_blocks):
        """
        Always append the new reserve blocks to the end of the list.
        There should never be overlap between blocks.
        """
        for i in range(0, len(resv_blocks)) :
            self.resvBlock.append(resv_blocks[i][0])
            self.resvBlockSize.append(resv_blocks[i][1])
        
    def consume(self, size):
        """
        Always consume from the beginning of the list, and always consume a whole reserve block
        """
        size_sum = 0
        ret_blocks = []
        cut_index = -1
        for i in range(0, len(self.resvBlockSize)) :
            size_sum += self.resvBlockSize[i]
            ret_blocks.append((self.resvBlock[i], self.resvBlockSize[i]))
            cut_index = i
            if size_sum >= size :
                break
        self.resvBlock = self.resvBlock[cut_index+1:]
        self.resvBlockSize = self.resvBlockSize[cut_index+1:]
        return ret_blocks, size_sum

    
class ShortUrlKeyName(db_core.KeyName):
    @classmethod
    def keyNamePrefix(cls):
        return "ShortUrl:"


class GlobalShortUrl(BaseModel , ShortUrlKeyName):
    campaignParent = db.ReferenceProperty(db_core.CampaignParent, required=True, indexed=False)
    
    @classmethod
    def get_by_surl(cls, surl):
        if len(surl) != 6:
            logging.warning("Short URL %s length is invalid!" % surl)
            return None
        if surl in url_const.BLACKLISTED_URL_HASHS:
            logging.error("Blacklisted short URL! %s" % surl)
            return None
        key_name = cls.keyName(surl)
        return GlobalShortUrl.get_by_key_name(key_names=key_name)

    @classmethod
    def get_post_by_surl(cls, surl):
        globalShortUrl = cls.get_by_surl(surl)
        if not globalShortUrl: return None
        return SPost.get_by_key_name(SPost.keyName(surl), globalShortUrl.campaignParent)

    @classmethod
    def get_tweet_id_by_surl(cls, surl):
        post = cls.get_post_by_surl(surl)
        return int(post.tweetId) if post and post.tweetId else None

    @classmethod
    def is_number_or_lower(cls, char):
        return cls._is_number(char) or cls._is_lower(char)                
    
    @classmethod
    def _is_number(cls, char):
        code = ord(char)
        return code<=57 and code>=48
    
    @classmethod
    def _is_lower(cls, char):
        code = ord(char)
        return code<=122 and code>=97

    
class ShortUrlClickCounter(ClickCounter, ShortUrlKeyName):
    uid = db.IntegerProperty()
    
    @classmethod
    def getClickCounter(cls,info):
        if type(info) == str or type(info) == unicode:
            urlHash = info
            post = GlobalShortUrl.get_post_by_surl(urlHash)
        else:
            post = info
        url = post.url
        if url is None:
            return None
        urlHash = post.urlHash
        batch = UrlClickCounter.getUrlHash(url)
        uid = post.parent().uid
        parent = db_core.UserUrlClickParent.get_or_insert_parent(batch,uid=uid)
        shortUrlClickCounter = ShortUrlClickCounter.get_or_insert(key_name=ShortUrlClickCounter.keyName(urlHash),uid=uid,
                                                                  parent=parent)
        return shortUrlClickCounter
    
    def url(self):
        return self.post().url
    
    def msg(self):
        return self.post().msg
    
    def post(self):
        urlHash = self.keyNameStrip()
        return GlobalShortUrl.get_post_by_surl(urlHash)

    
class UrlKeyName(db_core.KeyName):
    @classmethod
    def keyNamePrefix(cls):
        return "Url:"

    @classmethod
    def normalizedName(cls, url):
        return url
    
    @classmethod
    def urlFromKey(cls, dbKey):
        dbKey = db_core.normalize_2_key(dbKey)
        return dbKey.name()[len(cls.keyNamePrefix()):]

    def url(self):
        return self.key().name()[len(UrlKeyName.keyNamePrefix()):]
    
    def root_domain(self):
        return url_util.root_domain(self.url())


class TitleUrlMap(db.Model, db_core.KeyName):
    url = db.StringProperty(indexed=False)
    
    @classmethod
    def keyNamePrefix(cls):
        return "TitleUrlMap:"


class GlobalUrl(CreatedTimeBaseModel, UrlKeyName):
    encoding = db.StringProperty(indexed=False)
    tags = db.StringProperty(indexed=False)
    titleKey = db.StringProperty(indexed=False)
    title = db.StringProperty(indexed=False)
    totalClick = db.IntegerProperty(default=0, indexed=False)
    description = db.TextProperty()
    mediaUrl = db.TextProperty()
    soupImg = db.StringProperty(indexed=False)
    videoSrc = db.TextProperty()
    toSoup = db.BooleanProperty(default=False, indexed=False)
    postId = db.StringProperty(indexed=False)
    troveState = db.IntegerProperty(choices=trove_const.URL_STATES)
    troveUrl = db.StringProperty(indexed=False) # Store the time if not ingested
    troveHandle = db.StringProperty(indexed=False)
    
    @classmethod
    def get_by_url(cls, url):
        if not url: return None
        url = cls.normalize(url)
        key_name = cls.keyName(url)
        globalUrl = cls.get_by_key_name(key_name)
        return globalUrl  

    @classmethod
    def get_or_insert_by_url(cls, url, params={}, resolve_trove_url=True, published_time=None):
        url = cls.normalize(url)
        key_name = cls.keyName(url)
        globalUrl = cls.get_or_insert(key_name=key_name, **params)
        if resolve_trove_url: globalUrl.resolve_trove_url(published_time=published_time)
        return globalUrl

    @classmethod
    def get_or_insert_by_feed_entry(cls, entry, title_decorator=None):
        return cls._get_or_insert_by_common_attributes(entry.url, entry.title, entry.full_image, title_decorator=title_decorator)
    
    @classmethod
    def get_or_insert_by_page_parser(cls, url, title_decorator=None):
        page_content = url_util.fetch_url(url)
        parser = pageparser.SPageParser()
        parser.feed(page_content)
        title = parser.get_title()
        full_image = parser.headerImg if parser.headerImg else parser.theOne
        return cls._get_or_insert_by_common_attributes(url, title, full_image, title_decorator=title_decorator)
    
    @classmethod
    def _get_or_insert_by_common_attributes(cls, url, title, full_image, title_decorator=None):
        title = str_util.strip_one_line(title)
        if title_decorator: title = title_decorator(title)
        if len(title) > 500: title = title[:500]
        globalUrl = GlobalUrl.get_or_insert_by_url(url, params=dict(title=title, mediaUrl=full_image))
        if globalUrl and globalUrl.mediaUrl != full_image:
            globalUrl.mediaUrl = full_image
            globalUrl.put()
        return globalUrl
    
    def resolve_trove_url(self, published_time=None):
        try:
            if not self.should_trove_resolve(published_time): return
            url = self.url()
            trove_state, trove_url, trove_handle = None, None, None
            if context.is_trove_enabled():
                if not trove_api.is_url_eligible_for_visor(url, is_iphone=False, is_phone=False):
                    return
                trove_item = trove_api.TroveItem.get_by_url(url)
                if trove_item:
                    trove_state = trove_const.URL_STATE_HOSTED if trove_item.is_hosted else trove_const.URL_STATE_UNHOSTED
                    trove_url = trove_item.trove_url
                    trove_handle = trove_item.curator_handle
                else:
                    trove_state = trove_const.URL_STATE_UNINGESTED
                    trove_url = datetime.utcnow().strftime(common_const.COMMON_DATETIME_FORMAT)
            if trove_state is not None:
                self.troveState = trove_state
                self.troveUrl = trove_url
                self.troveHandle = trove_handle
                self.put()
        except:
            logging.exception("Unexpected error inside GlobalUrl.resolve_trove_url()!")
        
    def mark_trove_hosted(self, trove_url, media_url):
        self.troveState = trove_const.URL_STATE_HOSTED
        self.troveUrl = trove_url
        self.mediaUrl = media_url
        self.put()

    def is_trove_ingested(self):
        return self.troveState and self.troveUrl and not trove_api.is_url_in_unhosted_blacklist(self.url())

    def is_trove_hosted(self):
        return self.troveUrl and self.troveState and self.troveState == trove_const.URL_STATE_HOSTED
    
    def is_trove_unhosted(self):
        return self.troveUrl and self.troveState and self.troveState == trove_const.URL_STATE_UNHOSTED
    
    def is_trove_hosted_or_curated(self):
        if self.is_trove_hosted(): return True
        if not self.is_trove_ingested(): return False
        return self.troveHandle is not None
#         return url_util.get_params(self.troveUrl).has_key('chid')

    def is_trove_smartpicked(self):
        return self.is_trove_ingested() and self.troveHandle is not None

    def is_trove_unhosted_and_curated(self):
        return self.troveHandle is not None and self.is_trove_unhosted()

    def should_trove_resolve(self, published_time):
        if self.troveState is None: return True
        if self.troveState != trove_const.URL_STATE_UNINGESTED: return False
        last_resolution_time = self.last_trove_resolution_time()
        if not last_resolution_time: return True
        if not published_time: return False
        url = self.url()
        if not trove_api.is_url_in_ingested_whitelist(url): return False 
        utcnow = datetime.utcnow()
        delta_published_time = datetimeparser.timedelta_in_minutes(utcnow - published_time)
        delta_last_resolution_time = datetimeparser.timedelta_in_minutes(utcnow - last_resolution_time)
        retry = delta_last_resolution_time > delta_published_time * 0.382
        if retry:
            logging.info("Trove ingestion log. Time to test again for URL published %d minutes ago. Last tried %d minutes ago. %s" % 
                         (delta_published_time, delta_last_resolution_time, url))
        return retry

    def last_trove_resolution_time(self):
        if self.troveState == trove_const.URL_STATE_UNINGESTED and self.troveUrl:
            return datetime.strptime(self.troveUrl, common_const.COMMON_DATETIME_FORMAT)
        else:
            return None
        
    @classmethod
    def get_by_title_key(cls, titleKey):
        titleKey = urllib.unquote_plus(urllib.unquote_plus(titleKey.encode('utf-8'))).decode('utf-8')
        titleMap = TitleUrlMap.get_by_key_name(TitleUrlMap.keyName(titleKey))
        if titleMap is None:
            return None
        url = titleMap.url
        globalUrl = GlobalUrl.get_by_key_name(GlobalUrl.keyName(url))
        if globalUrl is None:
            logging.error("GlobalUrl model is not initialized for url %s!" % url)
        return globalUrl

    @classmethod
    def normalize(cls, url):
        url = url_util.strip_url(url)
        url = url_util.remove_utm(url)
#         url = Website.filter_url_params(url)
        url = url_util.normalize_url(url)
        try:
            url = url.decode('utf-8')
        except:
            pass
        url = SuperLongUrlMapping.filterSuperLongUrl(url)
        return url

    def getThumbnail(self):
        if self.soupImg is not None:
            return url_const.GLOBAL_URL_THUMBNAIL_URL % (context.get_context().amazon_bucket(), self.soupImg)
        else:
            return self.mediaUrl
        
    def getFullImage(self):
        return self.mediaUrl


class GlobalUrlCounter(RatingCounter, UrlKeyName):
    """
    postDate - Date when the URL is first posted. Format sample: '20110331'
    ratingCount - Number of users who have rated this URL. 0 and none are equivalent.
    ratingScore - Total rating scores.
    """
    uid = db.IntegerProperty()
    postDate = db.IntegerProperty()
    shared = db.BooleanProperty(default=True, indexed=False)
    userName = db.StringProperty(indexed=False)
    mediaType = db.IntegerProperty(default=common_const.MEDIA_TYPE_NORMAL)
    topics = db.StringListProperty()
#    topicsForNew = db.StringListProperty()
    ratingCount = db.IntegerProperty(default=0,indexed=False)
    ratingScore = db.IntegerProperty(default=0,indexed=False)
    commentCount = db.IntegerProperty(default=0,indexed=False)
    deleted = db.BooleanProperty(default=False)
    sharedCount = db.IntegerProperty(default=0, indexed=False)
    instagramId = db.StringProperty(indexed=False)
    
    @classmethod
    def get_or_insert_by_url(cls, url, params={}, clickTime=None):
        if context.is_dev_mode() :
            clickTime = datetime.utcnow()
        url = GlobalUrl.normalize(url)
        keyName = GlobalUrlCounter.keyName(url)
        globalUrlCounter = GlobalUrlCounter.get_by_key_name(keyName)
        dbPut = clickTime is not None or globalUrlCounter is None
        if globalUrlCounter is None :
            globalUrl = GlobalUrl.get_or_insert_by_url(url)
            if globalUrl is None:
                logging.error('Global URL is not initialized: %s' % url)
                return None
            if str_util.strip(globalUrl.title) is None :
                globalUrl.title = url[url.find('//'):][:str_util.DB_STRING_PROTECTIVE_LENGTH]
                globalUrlModified = True
            if globalUrl.videoSrc is not None and globalUrl.videoSrc!= '':
                mediaType = common_const.MEDIA_TYPE_VIDEO
            elif globalUrl.mediaUrl == globalUrl.keyNameStrip() :
                mediaType = common_const.MEDIA_TYPE_IMAGE
            else:
                mediaType = common_const.MEDIA_TYPE_NORMAL
            globalUrlModified = False
            if globalUrl.titleKey is None:
                titleKey = str_util.title_2_key(globalUrl.title) 
                titleMap = TitleUrlMap.get_by_key_name(TitleUrlMap.keyName(titleKey)) 
                if titleMap is not None: 
                    while True: 
                        ran = random.randint(0,10000) 
                        ranUrlName = titleKey + '_'+str(ran) 
                        titleMap = TitleUrlMap.get_by_key_name(TitleUrlMap.keyName(ranUrlName)) 
                        if titleMap is None: 
                            titleKey = ranUrlName 
                            break 
                titleMap = TitleUrlMap(key_name=TitleUrlMap.keyName(titleKey),url=url) 
                titleMap.put() 
                globalUrl.titleKey = titleKey 
                globalUrlModified = True
#            if globalUrl.mediaUrl is not None and globalUrl.mediaUrl != '':
#                globalUrl = setGlobalSoupImage(globalUrl)
#                globalUrlModified = True
            if globalUrlModified:
                globalUrl.put() 
            now = datetime.utcnow()
            params['key_name'] = keyName
            params['postDate'] = datetimeparser.intDay(now)
            params['mediaType'] = mediaType
            globalUrlCounter = GlobalUrlCounter(**params)
            globalUrlCounter.sharedCount = cls.get_shared_count(globalUrlCounter)
        if globalUrlCounter is not None and dbPut:
            if clickTime is not None:
                globalUrlCounter.increment(size=1, clickTime=clickTime)
            globalUrlCounter.put()
        return globalUrlCounter
    
    @classmethod
    def get_or_insert_by_surl(cls, surl):
        if surl in url_const.BLACKLISTED_URL_HASHS:
            logging.error("Blacklisted short URL! %s" % surl)
            return None
        params = {}
        post = GlobalShortUrl.get_post_by_surl(surl)
        content = post.content
        topic = content.getFirstTopic()
        if not topic: return None 
        params['topics'] = content.getTopics()
#        params['topicsForNew'] = Topic.get_topics_for_new(topic)
        params['shared'] = False
        globalUrlCounter =  GlobalUrlCounter.get_or_insert_by_url(post.url, params=params)
        if globalUrlCounter.uid is None:
            from soup.user.models import SoupUser
            channel = post.get_channel()
            if channel:
                soupUser = SoupUser.get_or_insert_by_sns_channel(channel)
                globalUrlCounter.uid = soupUser.key().id()
                globalUrlCounter.userName = soupUser.name
                soupUserCounter = soupUser.getCounter()
                soupUserCounter.postCount += 1
                soupUserCounter.put()
                globalUrlCounter.put()
        return globalUrlCounter

    @classmethod
    def get_shared_count(cls, globalUrlCounter):
        return 0
        dataStr = "{}"
        shared = 0
        try:
            if globalUrlCounter.instagramId is not None:
                url = 'https://api.instagram.com/v1/media/'+ globalUrlCounter.instagramId +'?client_id='+common_const.INSTAGRAM_CLIENT_ID
                data = urllib.urlopen(url).read()
                data = json.loads(data)
                shared = data['data']['likes']['count']
            elif url.find('youtube.com') != -1:
                yid = url_util.get_youtube_id(url)
                if yid is not None:
                    yt_service = YouTubeService(developer_key=common_const.YOUTUBE_API_KEY)
                    entry = yt_service.GetYouTubeVideoEntry(video_id=yid)
                    shared = int(entry.statistics.favorite_count)
            else:
                api = "http://api.sharedcount.com/"
                p = {}
                p['url'] = url.encode('utf-8')
                api = api + '?' + urllib.urlencode(p)
                dataStr = urllib.urlopen(api).read()
                data = json.loads(dataStr)
                shared = data.get('Twitter', 0) + data.get('GooglePlusOne', 0) + data.get('LinkedIn', 0)
                facebookCount = data.get('Facebook', 0)
                if not type(facebookCount)==int :
                    facebookCount = facebookCount.get('total_count', 0)
                shared += facebookCount
            logging.debug("Get shared count %d for %s" % (shared, url))
        except Exception, ex :
            if str(ex).find('ApplicationError: 5') != -1:
                logging.warn("App Error 5: Get shared count for %s: %s" % (url, dataStr))
            else :
                logging.exception("Unexpected error: Get shared count for %s: %s" % (url, dataStr))
        return shared

    def globalUrl(self):
        url = self.url()
        globalUrl = GlobalUrl.get_or_insert_by_url(url)
        if globalUrl is None: logging.error("GlobalUrl is none for counter! %s" % url)
        return globalUrl
    
    def soupLink(self):
        globalUrl = self.globalUrl()
        if globalUrl.titleKey is None:
            logging.error('Missing titlekey for globalurl %s'%globalUrl.keyNameStrip())
            return 'http://' + deploysoup.DOMAIN_MAP[context.get_context().application_id()]
        return 'http://' + deploysoup.DOMAIN_MAP[context.get_context().application_id()] + '/soup/'+globalUrl.titleKey
    
    def firstTopicKey(self):
        if len(self.topics)==0 :
            logging.warn("Topic is empty for user '%s' URL: %s" % (self.uid, self.url()))
            return Topic.TOPIC_KEY_FRONTPAGE
        else :
            return self.topics[0]
        
    def rating(self):
        if self.ratingCount is None or self.ratingCount==0:
            return 0
        else:
            return round(1.0*self.ratingScore/self.ratingCount, 1)
        
    def count(self):
        return self.c365d
    
    HALF_DECAY_SECONDS = 3600*6
    @classmethod
    def hot_score(cls, baseScore, time):
        seconds = datetimeparser.timedelta_in_seconds(datetime.utcnow() - time)
        timeDecayFactor = 1.0/pow(2, 1.0*seconds/cls.HALF_DECAY_SECONDS)
        adjustedBase = pow(baseScore, 0.5)
        return int(floor(adjustedBase*timeDecayFactor*1000))
    
    def hotScore(self):
        return GlobalUrlCounter.hot_score(self.baseScore(), self.createdTime)
    
    def baseScore(self):
        self.setDay()
        if self.shared:
            base = 1
        else:
            base = 0
        totalScore = base + 2*self.ratingCount + self.c24h/10.0 + self.commentCount*4
        if self.sharedCount is not None :
            totalScore += self.sharedCount 
        return totalScore
    
    def topScore(self, base, max_value):
        if self.ratingCount == 0:
            rating = 2.0*3 + 5
        else:
            rating = 2.0*self.ratingScore/self.ratingCount + 5
        if max_value == 0:
            count = 0
        else:
            count = base
        return int(floor(rating*count))
    

class HotArticleCache:
    def __init__(self, globalUrlCounter):
        self.createdTime = globalUrlCounter.createdTime
        self.counterId = globalUrlCounter.id
        self.mediaType = globalUrlCounter.mediaType 
        self.uid = globalUrlCounter.uid
        self.topicKeys = globalUrlCounter.topics
        self.sharedCount = globalUrlCounter.sharedCount
        self.hotScore = globalUrlCounter.hotScore()
    
    def recalculateHotScore(self):
        self.hotScore = GlobalUrlCounter.hot_score(self.sharedCount, self.createdTime)
        
    def updateSharedCount(self, sharedCount):
        self.sharedCount = sharedCount
        self.recalculateHotScore()
        

class SiteMap(DatedBaseModel, db_core.KeyName):
    content = db.TextProperty()
    number = db.IntegerProperty()
    
    @classmethod
    def keyNamePrefix(cls):
        return "SiteMap:"
    
    @classmethod
    def get_by_date(cls,datetime,hashValue=0):
        keyName = SiteMap.keyName(datetimeparser.intDay(datetime))+ '_'+str(hashValue)
        return SiteMap.get_or_insert(keyName)
    
    @classmethod
    def get_index(cls):
        keyName = SiteMap.keyName('index')
        return SiteMap.get_or_insert(keyName)
    
    def location(self):
        return 'http://' + deploysoup.DOMAIN_MAP[context.get_context().application_id()] + '/sitemap/' + self.keyNameStrip() +'/'
    

class UrlClickCounter(ClickCounter, UrlKeyName):
    msg = db.TextProperty(default = ' ')
    uid = db.IntegerProperty()

    @classmethod
    def getClickCounter(cls,post):
        url = post.url
        if url is None:
            return None
        batch = UrlClickCounter.getUrlHash(url)
        uid = post.parent().uid
        parent = db_core.UserUrlClickParent.get_or_insert_parent(batch,uid=uid)
        urlClickCounter = cls.get_by_key_name(cls.keyName(url), parent)
        if urlClickCounter is None :
            if isinstance(post, SPost):
                if post.type == post_const.POST_TYPE_MESSAGE:
                    globalUrl = GlobalUrl.get_by_url(url)
                    if globalUrl and globalUrl.title:
                        urlMsg = globalUrl.title
                    else:
                        urlMsg = post.origMsg
                else:                    
                    urlMsg = post.origMsg
                urlClickCounter= UrlClickCounter(key_name=UrlClickCounter.keyName(url), uid=uid, parent=parent, msg=urlMsg)
            else:
                urlClickCounter= UrlClickCounter(key_name=UrlClickCounter.keyName(url), uid=uid, parent=parent)
            db.put(urlClickCounter)
        return urlClickCounter 
    
    @classmethod
    def getUrlHash(cls,url):
        hashCode = hash(url)
        return hashCode%url_const.USER_URL_CLICK_COUNTER_HASH_SIZE
       

class SuperLongUrlMappingKeyName(db_core.KeyName):
    @classmethod
    def keyNamePrefix(cls):
        return "SuperLongUrlMapping:"
    

class SuperLongUrlMapping(BaseModel, SuperLongUrlMappingKeyName):
    superLongUrl = db.TextProperty()

    @classmethod
    def getSuperLongUrlPrefix(cls):
        return 'http://' + context.get_context().long_domain() +'/superlongurl/'
    
    @classmethod
    def getSuperLongUrl(cls, url, parent):
        temp_url = unicode(url)
        if temp_url.startswith(cls.getSuperLongUrlPrefix()):
            key = temp_url[len(cls.getSuperLongUrlPrefix()):]
            temp = SuperLongUrlMapping.get_by_key_name(SuperLongUrlMapping.keyName(key), parent)
            if not temp == None and (not temp.superLongUrl == None):
                return temp.superLongUrl
        return url
        
    @classmethod
    def filterSuperLongUrl(cls, url):
        if len(url) > str_util.DB_STRING_PROTECTIVE_LENGTH:
            short_url_hash = cls._url_hash_str2Long(url)
            SLUM = None
            while True:
                SLUM = SuperLongUrlMapping.get_by_key_name(SuperLongUrlMapping.keyName(short_url_hash))
                if SLUM == None:
                    SLUM = SuperLongUrlMapping(key_name=SuperLongUrlMapping.keyName(short_url_hash),superLongUrl=url)
                    SLUM.put()
                    temp = SuperLongUrlMapping.get(SLUM.id)
                    if not temp == None and (not temp.superLongUrl == url):
                        short_url_hash = cls._increment_sub_hash_code(short_url_hash)
                    else:
                        break
                elif SLUM.superLongUrl == url:
                    break
                else:
                    short_url_hash = cls._increment_sub_hash_code(short_url_hash)
            return cls.getSuperLongUrlPrefix() + short_url_hash
        else:
            return url 

    @classmethod
    def _url_hash_str2Long(cls, url):
        return unicode(hash(url))+"_0"
    
    @classmethod
    def _increment_sub_hash_code(cls, slumHash):
        temp = unicode(slumHash)
        if temp.find("_"):
            return temp[0:temp.find("_")+1] + unicode(string.atol(temp[temp.find("_")+1:]) + 1) 
        else:
            return temp + '_1'
        

class TimeZoneModel(db.Model):
    timeZone  = db.StringProperty()

    
class SoupPost(db.Model):
    url = db.TextProperty()
    

WEBSITE_PARAMS_KEY = 'website_parmas'    
class Website(BaseModel, db_core.KeyName):
    includedKeys = db.TextProperty(default='')
    excludedKeys = db.TextProperty(default='')
    
    @classmethod
    def keyNamePrefix(cls):
        return "WebsiteUrl:"
    
    @classmethod
    def get_all(cls, cache_if_missing=False):
        webs = memcache.get(WEBSITE_PARAMS_KEY)
        if cache_if_missing and webs is None:
            webs = {}
            sites = Website.all().fetch(limit=1000)
            for site in sites:
                if site.includedKeys == '':
                    include = []
                else:
                    include = str_util.split_strip(site.includedKeys,';')
                if site.excludedKeys == '':
                    exclude = []
                else:
                    exclude = str_util.split_strip(site.excludedKeys,';')
                siteKey = site.keyNameStrip()
                webs[siteKey] = (include,exclude)
                if siteKey.count('.') == 1:
                    webs['www.'+siteKey] = (include,exclude)
                elif siteKey.startswith('www.') :
                    webs[siteKey.replace('www.','')] = (include,exclude)
            memcache.set(WEBSITE_PARAMS_KEY, webs, time=3600)
        return webs
        
    @classmethod
    def filter_url_params(cls, url):
        domain = url_util.full_domain(url)
        web_params = cls.get_all()
        if web_params and web_params.has_key(domain):
            index = url.find('?')
            if index==-1:
                pass
            else:
                query = url[index+1:]
                path = url[:index]
                values=query.split('&')
                params=[]
                for value in values:
                    key, item = urllib.splitvalue(value)
                    params.append((key,item)) 
                temp = []
                if len(web_params[domain][0]) > 0:
                    for k,v in params: 
                        if k is not None and v is not None and k in web_params[domain][0]:
                            temp.append(k+'='+v)
                elif len(web_params[domain][1]) > 0:
                    for k,v in params: 
                        if k is not None and v is not None and k not in web_params[domain][1]:
                            temp.append(k+'='+v)
                if len(temp) > 0:
                    params = '&'.join(temp)
                    url = path + '?' + params 
                else:
                    url = path
        return url


def isImageUrl(url):
    url = GlobalUrl.normalize(url)
    url = url.split('?')[0]
    for imgExt in common_const.IMAGE_URL_EXTENSIONS:
        if url.endswith(imgExt): return True
    return False


def hashUrl(shortUrlId):
    """ Translate a short URL id to short URL. """
    hash_in = shortUrlId
    pool = len(url_const.HASH_MAPPING)
    index = hash_in % 10
    hash_in = ( hash_in - index ) / 10
    hash_out = url_const.HASH_MAPPING[index]
    digit = 1
    while hash_in > 0:
        index = hash_in % pool
        hash_in = ( hash_in - index ) / pool
        adjusted_index = (index+url_const.HASH_INDEX_DELTA[digit]) % pool
        hash_out = url_const.HASH_MAPPING[adjusted_index] + hash_out
        digit += 1
    if len(hash_out)==5 :
        return hash_out[3] + hash_out[1] + hash_out[2] + hash_out[0] + hash_out[4]
    return hash_out


def uploadSoupImg(imageUrl):
    now = datetime.utcnow()
    generator = ShortUrlGenerator.get_or_insert('imgGenerator')
    urlHash = hashUrl(generator.cursor+url_const.SHORT_URL_GENERATOR_CURSOR_START)
    key = str(datetimeparser.intDay(now))+'/'+ urlHash
    generator.cursor += 1
    generator.put()
    status = upload.uploadImg(imageUrl, key)
    if status == 200:
        logging.debug('Finished img upload.')
        return key
    else:
        logging.error('Image upload failed: %s' % str(status))
        return None
    

def setGlobalSoupImage(globalUrl):
    try:
        imgUrl = globalUrl.mediaUrl
        soupImg = uploadSoupImg(imgUrl)
        if soupImg is not None:
            globalUrl.soupImg = soupImg
    except Exception,e:
        if type(e)==BadImageError or type(e)==NotImageError:
            logging.warning('Unexpected error when generate soup img : %s'%imgUrl)
        elif str(e).find('ApplicationError: 5') != -1 or str(e).find('ApplicationError: 2') != -1 or str(e).find('No such file or directory') != -1:
            logging.warning('Unexpected error when generate soup img : %s'%imgUrl)
        else:
            logging.exception('Unexpected error when generate soup img : %s'%imgUrl)
    return globalUrl
    
    
    