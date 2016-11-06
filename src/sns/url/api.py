import random
import logging
import deploysoup
import datetime
import urllib
import string
from sets import ImmutableSet

from google.appengine.api import users
from google.appengine.ext import db

import context, deploysns
from common import consts as common_const
from common.utils import string as str_util
from common.utils import datetimeparser
from sns.serverutils import memcache
from sns.core.core import StandardCampaignParent 
from sns.core.taskdaemonnowait import BackendTaskDaemonNoWait
from sns.usr.models import UserClickCounter
from sns.log import consts as log_const
from sns.log.api import getPatternValue
from sns.chan.models import ChannelClickCounter
from sns.camp.models import CampaignClickCounter
from sns.post import consts as post_const
from sns.post.models import SPost
from sns.email.models import MPost, EmailList, EmailListClickCounter
from sns.api import consts as api_const, errors as api_error
from sns.api.base import BaseProcessor
from sns.cont.models import FeedCC
from sns.core.core import RawClickCursor, UserClickParent,User
from sns.serverutils import deferred
from google.appengine.ext.db import Query
import consts as url_const
from models import ShortUrlGenerator, GlobalShortUrl, ShortUrlClickCounter,UrlClickCounter,\
                GlobalUrlCounter,SiteMap, Website, hashUrl, GlobalUrl


def _deferredExecutionHandler(processorClass):
    context.set_deferred_context(deploy=deploysns)
    return processorClass().execute()


class ShortUrlProcessor(BaseProcessor):
    def getModel(self):
        return ShortUrlClickCounter
    
    @classmethod
    def supportedOperations(cls):
        return ImmutableSet([api_const.API_O_GET,  api_const.API_O_QUERY, api_const.API_O_REFRESH,api_const.API_O_CRON_EXECUTE])
    
    @classmethod
    def randomFirstCharacter(cls):
        return url_const.HASH_MAPPING[random.randint(0,len(url_const.HASH_MAPPING)-1)] 
        
    @classmethod
    def incrementCursor(cls, modelUser, firstCharacter, increment=1):
        def _txn(shortUrlGenerator, increment):
            newCursor = shortUrlGenerator.cursor + increment
            shortUrlGenerator.cursor = newCursor
            shortUrlGenerator.put()
            return url_const.SHORT_URL_GENERATOR_CURSOR_START + newCursor
        shortUrlGenerator=ShortUrlGenerator.get_by_first_char(firstCharacter)
        resv_block = db.run_in_transaction(_txn, **dict(shortUrlGenerator=shortUrlGenerator, increment=increment))
        shortUrlIndices = []
        for i in range(resv_block, resv_block-increment, -1) :
            shortUrlIndices.append(GlobalShortUrl(
                                                 key_name=GlobalShortUrl.keyName(firstCharacter + hashUrl(i)),
                                                 campaignParent=modelUser))
        db.put(shortUrlIndices)
        return resv_block
        
    @classmethod
    def consumeShortUrlReserve(cls, surid, resvSize):
        """
        Return a list of tuples of reserved block and size.
        """
        def txn_resv_existing(surid, resvSize):
            shortUrlResv = db.get(surid)
            logging.debug("Start ShortUrlReserve.consume(%s). %s" % (resvSize, shortUrlResv.status())) 
            consume_resv, consume_size  = shortUrlResv.consume(resvSize)
            if consume_size > 0 :
                shortUrlResv.put()
            return consume_resv, consume_size, shortUrlResv
        ret_resv, existing_resv_size, shortUrlResv = db.run_in_transaction(txn_resv_existing, surid, resvSize)
        if existing_resv_size < resvSize :
            new_resv_block_size = resvSize - existing_resv_size
            if new_resv_block_size < 50 :
                new_resv_block_size = 50
            new_resv_block = cls.incrementCursor(shortUrlResv.parent(), shortUrlResv.firstCharacter,  new_resv_block_size)
            ret_resv.append((new_resv_block, new_resv_block_size))
        logging.debug("End ShortUrlReserve.consume(%s). %s" % (resvSize, shortUrlResv.status())) 
        return ret_resv
    
    @classmethod
    def saveShortUrlReserve(cls, surid, unused_resv_blocks):
        """
        Save any unused reserves back to the user object.
        """
        def txn_resv_save(surid, resv_blocks):
            shortUrlResv = db.get(surid)
            logging.debug("Start ShortUrlReserve.save(%s). %s" % (unused_resv_blocks, shortUrlResv.status())) 
            shortUrlResv.save(resv_blocks)
            shortUrlResv.put()
            logging.debug("End ShortUrlReserve.save(%s). %s" % (unused_resv_blocks, shortUrlResv.status())) 
        if unused_resv_blocks is None or len(unused_resv_blocks)==0 or unused_resv_blocks[0][1] == 0: 
            return
        db.run_in_transaction(txn_resv_save, surid, unused_resv_blocks)
        
    @classmethod
    def extractShortUrlIdFromResv(cls, resv_blocks):
        if resv_blocks is None or len(resv_blocks) == 0 :
            raise api_error.ApiError(api_error.API_ERROR_UNKNOWN, "Invalid short URL reserve block input!")
        urlMappingId = resv_blocks[0][0]
        remaining_block_size = resv_blocks[0][1] - 1
        if remaining_block_size < 0 :
            raise api_error.ApiError(api_error.API_ERROR_UNKNOWN, "Invalid short URL reserve block input!")
        if remaining_block_size > 0 :
            resv_blocks[0] = (urlMappingId-1, remaining_block_size)
        else :
            resv_blocks.pop(0)
        return urlMappingId
    
    @classmethod
    def extractShortUrlFromResv(cls, resv_blocks):
        urlMappingId = cls.extractShortUrlIdFromResv(resv_blocks)
        return hashUrl(urlMappingId)
    
    def _trans_refresh_turn(self,user,filter_date,limit_number=200):
        objects= self.getModel().all().filter('createdTime >=', filter_date).order('createdTime').ancestor(user).fetch(limit=limit_number)
        for obj in objects:
            try:
                obj.urlHash = obj.keyNameStrip() 
            except:
                logging.error("ShortUrlClickCounter created at %s has no key name." % obj.createdTime)
        db.put(objects)
        num=len(objects)
        if len(objects)==limit_number:
            filter_date = objects[limit_number-1].createdTime
            return True,filter_date,num
        else:
            return False,filter_date,num
        
    def cron_execute(self,params):
        return ClickCountDaemon(workers=url_const.RAW_CLICK_HASH_SIZE).execute()
    

class ClickCountDaemon(BackendTaskDaemonNoWait):
    def __init__(self, workers=url_const.RAW_CLICK_HASH_SIZE):
        BackendTaskDaemonNoWait.__init__(self, workers=workers)
        context.set_deferred_context(deploy=deploysns)
        
    def pre_execute(self):
        logging.info("Count Clicks: started counting using %d threads..." % (len(self.workers), ))
        self.add_tasks(range(url_const.RAW_CLICK_HASH_SIZE))

    def run_impl(self, task):
        userHashCode = task
        start_time = datetime.datetime.utcnow() 
        logging.info("Count Clicks: Started click counting for user hash %d..." % userHashCode)
        cursor = RawClickCursor.get_rawclick_cursor(userHashCode)
        filterMinute = cursor.lastUpdateMinute
        now = datetime.datetime.utcnow()
        buckets = []
        for i in range(-url_const.RAW_CLICK_CACHE_MINUTES, 0):
            bucketTime = now + datetime.timedelta(minutes=i)
            intTime = datetimeparser.intMinute(bucketTime)
            if intTime > filterMinute:
                bucket_key = get_rawclick_bucket_key(bucketTime, userHashCode)
                bucket = get_rawclick_bucket(bucketTime,userHashCode)
                if len(bucket)>0:
                    logging.info("Count Clicks: Executing raw click bucket '%s' with %d clicks..." % (bucket_key, len(bucket)))
                buckets.append(bucket)
                cursor.lastUpdateMinute = intTime
        cursor.put()
        rawClicks = []
        for bucket in buckets:
            for click in bucket:
                rawClicks.append(click)
            
        if len(rawClicks) == 0:
            return
        user_map = {}
        soup_clicks = []
        for click in rawClicks:
            if click.has_key('uid'):
                if not user_map.has_key(click['uid']) :
                    user_map[click['uid']] = [click]
                else:
                    ids = user_map[click['uid']]
                    ids.append(click)
                    user_map[click['uid']] = ids
            else:
                soup_clicks.append(click)
        for uid in user_map.keys():
            clickIds = user_map[uid]
            self._countClicks(uid, clickIds)
        for soupClick in soup_clicks:
            self._countSoupClick(soupClick)
        running_time = datetimeparser.timedelta_in_seconds(datetime.datetime.utcnow() - start_time)
        logging.info("Count Clicks: Finished click counting for user hash %d in %d seconds." % (userHashCode, running_time))
    
    def _countSoupClick(self, soupClick):
        url = soupClick['url']
        try:
            globalUrlCounter = GlobalUrlCounter.get_by_key_name(GlobalUrlCounter.keyName(url))
            clickTime = soupClick['createdTime']
            globalUrlCounter.increment(size=1,clickTime=clickTime)
            db.put(globalUrlCounter)
            logging.debug("Count Clicks: Finished counting soup click successfully for url %s" % url)
        except:
            logging.exception("Count Clicks: Error when counting soup click for url %s : %s" % url)
    
    def _countClicks(self, uid, clickIds):
        try:
            self._countClicksImpl(uid, clickIds)
        except:
            logging.exception("Count Clicks: Error when counting clicks for user %s: " % uid)

    def _countClicksImpl(self, uid, clickIds):
        def _increaseClickCounters(user, click_info):
            for counter in click_info.keys():
                infos = click_info[counter]
                counter = db.get(counter)
                for info in infos:
                    counter.incrementByReferrerAndCountry(user,referrer=info[0],country=info[1],clickTime=info[2])
                db.put(counter)
                
        click_info = {}
        parent = UserClickParent.get_or_insert_parent(uid=uid)
        user = User.get_by_id(uid)
        clicks = clickIds
        for click in clicks:
            counters = []
            post = click['post']
            clickTime = click['createdTime']
            referrer = click['referrer']
            country = click['country']
            userClickCounter = UserClickCounter.get_or_insert(UserClickCounter.keyName(uid),parent=parent)
            counters.append(userClickCounter.id)
            try:
                postingCampaignClickCounter = CampaignClickCounter.get_or_insert(CampaignClickCounter.keyName(post.campaign.id),parent=parent)
                counters.append(postingCampaignClickCounter.id)
            except:
                pass
            if isinstance(post, SPost):
                channel= post.get_channel()
                if channel:
                    channelClickCounter = ChannelClickCounter.get_or_insert(channel.key().name(), parent=parent)
                    counters.append(channelClickCounter.id)
                if post.type == post_const.POST_TYPE_FEED:
                    feedClickCounter = FeedCC.get_or_insert_by_feed(post.content, parent=parent)
                    counters.append(feedClickCounter.id)
            if isinstance(post, MPost):
                campaign = post.campaign  
                modelUser = campaign.parent()
                
                mid = click['mid'] 
                if unicode(mid).startswith(EmailList.keyNamePrefix()):
                    mailList = EmailList.get_by_key_name(mid, modelUser)
                else:
                    mailList = EmailList.get_by_id(string.atoi(mid), modelUser)                          
                mailListCCKN = EmailListClickCounter.keyName(unicode(mailList.key().id_or_name()))
                mailListCC = EmailListClickCounter.get_or_insert(mailListCCKN, parent=parent)
                counters.append(mailListCC.id)
                                
            for counter in counters:
                if not click_info.has_key(counter):
                    click_info[counter] = [(referrer,country,clickTime)]
                else:
                    click_info[counter].append((referrer,country,clickTime))
        retry = 0
        while retry < 2:
            retry += 1
            try:
                db.run_in_transaction(_increaseClickCounters, user, click_info)
                logging.debug("Count Clicks: Increased user clicks successfully for user %d." % uid)
                break
            except:
                if retry == 2:
                    logging.error("Count Clicks: Error when increase user click for user %d: " % uid)
            
        allShortUrlCounters = []
        for click in clicks :
            post = click['post']
            shortUrlClickCounter = ShortUrlClickCounter.getClickCounter(post)
            if shortUrlClickCounter in allShortUrlCounters:
                shortUrlClickCounter = allShortUrlCounters[allShortUrlCounters.index(shortUrlClickCounter)]
            click_info = {}
            clickTime = click['createdTime']
            referrer = click['referrer']
            country = click['country']
            shortUrlClickCounter.incrementByReferrerAndCountry(user,referrer=referrer,country=country,clickTime=clickTime)
            if shortUrlClickCounter not in allShortUrlCounters:
                allShortUrlCounters.append(shortUrlClickCounter)
        retry = 0
        while retry < 2:
            retry += 1
            try:
                db.put(allShortUrlCounters)
                logging.debug("Count Clicks: Increased user url clicks successfully for user %d and urlHash %s." % (uid, post.urlHash))
                break
            except:
                if retry == 2:
                    logging.error("Count Clicks: Error when increasing user url clicks for user %d and urlHash %s: " % (uid, post.urlHash))
             
        allGlobalCounters = []
        for click in clicks :
            post = click['post']
            url = post.url
            if not isinstance(post, SPost):
                continue
            content = post.content
            if content.__class__.__name__ != 'Feed':
                continue
            elif len(content.topics) == 0 :
                continue
            params = {}
            params['topics'] = content.topics
#            topicsForNew = []
#            for topic in content.topics:
#                newTopics = Topic.get_topics_for_new(topic)
#                for newTopic in newTopics:
#                    if not newTopic in topicsForNew:
#                        topicsForNew.append(newTopic)
#            params['topicsForNew'] = topicsForNew
            params['shared'] = False
            globalUrlCounter = GlobalUrlCounter.get_or_insert_by_url(url, params=params, clickTime=click['createdTime'])
            if globalUrlCounter is None:
                continue
            if globalUrlCounter in allGlobalCounters:
                globalUrlCounter = allGlobalCounters[allGlobalCounters.index(globalUrlCounter)]
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
            if globalUrlCounter not in allGlobalCounters:
                allGlobalCounters.append(globalUrlCounter)
            
        retry = 0
        while retry < 2:
            retry += 1
            try:
                db.put(allGlobalCounters)
                logging.debug("Count Clicks: Increased global url clicks successfully for url %s" % url)
                break
            except:
                if retry == 2:
                    logging.error("Count Clicks: Error when increasing global url clicks for url %s: " % url)
        

class UrlClickCounterProcessor(BaseProcessor):
    def getModel(self):
        return UrlClickCounter

    def _trans_refresh_turn(self,user,filter_date,limit_number=200):
        objects= self.getModel().all().filter('createdTime >=', filter_date).order('createdTime').ancestor(user).fetch(limit=limit_number)
        for obj in objects:
            try:
                obj.url = obj.keyNameStrip() 
            except:
                logging.error("UrlClickCounter created at %s has no key name." % obj.createdTime)
        db.put(objects)
        num=len(objects)
        if len(objects)==limit_number:
            filter_date = objects[limit_number-1].createdTime
            return True,filter_date,num
        else:
            return False,filter_date,num


class ShortUrlClickCounterProcessor(BaseProcessor):
    def getModel(self):
        return ShortUrlClickCounter 
    

class SiteMapProcessor(BaseProcessor):
    def getModel(self):
        return SiteMap
    
    @classmethod
    def supportedOperations(cls):
        return ImmutableSet([api_const.API_O_CRON_EXECUTE, 
                           ]).union(BaseProcessor.supportedOperations())
                           
    def cron_execute(self,params):
        deferred.defer(_deferredExecutionHandler, processorClass=GlobalUrlCounterProcessor)
        
    def execute(self):
        if SiteMap.all().count() == 0:
            return
        siteIndex = SiteMap.get_index()
        content = ''
        number = 0
        limit = 100
        offset = 0
        while True:
            maps = Query(SiteMap,keys_only=True).order('createdTime').fetch(limit=limit,offset=offset)
            if len(maps) == 0:
                break
            for sitemap in maps:
                offset += 1
                number += 1
                if sitemap.name().find('index')!= -1:
                    continue
                content += SiteMapProcessor.getSiteMapInfo(sitemap)
        siteIndex.content = content
        siteIndex.number = number
        siteIndex.put()
        logging.info('Finished setting Site Map index!')
        
            
    @classmethod
    def getSiteMapInfo(cls,siteMap):
        location = 'http://' + deploysoup.DOMAIN_MAP[context.get_context().application_id()] + '/sitemap/' + siteMap.name().split(':')[1] +'/'
        loc = '<loc>' + location + '</loc>'
        date = siteMap.name().split(':')[1]
        if date.find('_')!= -1:
            date = date.split('_')[0]
        mod = '<lastmod>' + date[:4]+'-'+date[4:6]+'-'+date[6:8]+ '</lastmod>'
        return '<sitemap>' + loc + mod + '</sitemap>'

     
class GlobalUrlProcessor(BaseProcessor):
    def getModel(self):
        return GlobalUrl
    
    @classmethod
    def supportedOperations(cls):
        return ImmutableSet([api_const.API_O_CRON_EXECUTE,
                           ]).union(BaseProcessor.supportedOperations())

    def cron_execute(self, params):         
        query = self.getModel().all().filter('troveState', None).order('-createdTime')
#         query_str = "SELECT * FROM GlobalUrl WHERE troveState = NULL ORDER BY createdTime DESC"
#         query = db.GqlQuery(query_str)
        global_urls = query.fetch(limit=10)
        for global_url in global_urls:
            global_url.resolve_trove_url()


class GlobalUrlCounterProcessor(BaseProcessor):
    def getModel(self):
        return GlobalUrlCounter
    
    @classmethod
    def supportedOperations(cls):
        return ImmutableSet([api_const.API_O_EXECUTE, api_const.API_O_RATE, 
                           ]).union(BaseProcessor.supportedOperations())
         
    def execute(self):
        utcnow = datetime.datetime.utcnow()
        beginDay = datetime.datetime(year=utcnow.year,month=utcnow.month,day=utcnow.day,hour=7)
        lastDay = beginDay -datetime.timedelta(days=1)
        lastSiteMap = SiteMap.get_by_date(lastDay)
        if lastSiteMap.modifiedTime < beginDay:
            GlobalUrlCounterProcessor.setDailySiteMap(lastDay)
        GlobalUrlCounterProcessor.setDailySiteMap(beginDay)
        deferred.defer(_deferredExecutionHandler, processorClass=SiteMapProcessor)

    def rate(self, params):
        """
        oldscore - 0-5, 0 and none are equivalent
        newscore - 0-5, 0 and none are equivalent
        If old score is none, it is a new rating. 
        If new score is none, it is a removal of rating.  
        """
        return db.run_in_transaction(self._trans_rate, params)

    def _trans_rate(self, params):
        obj = self.get(params)
        oldScore = int(params.get('oldscore', 0))
        newScore = int(params.get('newscore', 0))
        if oldScore==newScore:
            return
        if obj.ratingScore is None:
            obj.ratingScore = 0
        if obj.ratingCount is None:
            obj.ratingCount = 0
        if oldScore==0:
            obj.ratingCount += 1
            obj.ratingScore += newScore
        elif newScore==0:
            obj.ratingCount -= 1
            obj.ratingScore -= oldScore
        else:
            obj.ratingScore += newScore - oldScore
        db.put(obj)
        return obj
        
    @classmethod
    def setDailySiteMap(cls,theDay):
        def getCounterInfo(counter):
            return '<url><loc>' + counter.soupLink()+'</loc></url>'

        filterDate = theDay
        endDate = theDay + datetime.timedelta(days=1)
        numbers = []
        contents = []
        for i in range(0,url_const.SITE_MAP_HASH_SIZE):
            numbers.append(0)
            contents.append('')
        go_on = True
        fetchCount = 100
        while go_on :
            counters = GlobalUrlCounter.all().filter('createdTime > ', filterDate).fetch(limit=fetchCount)
            if len(counters) < fetchCount:
                go_on = False
            for counter in counters:
                if counter.createdTime > endDate:
                    go_on = False
                    break
                else:
                    filterDate = counter.createdTime
                    hashValue = hash(counter.keyNameStrip())%10
                    numbers[hashValue] = numbers[hashValue] +1
                    contents[hashValue] = contents[hashValue] + getCounterInfo(counter)
        for i in range(0,url_const.SITE_MAP_HASH_SIZE):
            siteMap = SiteMap.get_by_date(theDay,hashValue=i)
            siteMap.content = contents[i]
            siteMap.number = numbers[i]
            siteMap.put()
        logging.info('Finished setting daily Site Map for %s!' % str(theDay))
     

def is_ads(mediaUrl, domain):
    if mediaUrl is None or domain is None:
        return False
    index = mediaUrl.find('//')
    full = mediaUrl[index:]
    mediaDomain = urllib.splithost(full)[0]
    if str_util.strip(mediaDomain) is None :
        return False
    blackSites = getPatternValue(log_const.PATTERN_AD_SITE)
    for site in blackSites:
        if mediaDomain.find(site) != -1 and domain.find(site) == -1:
            return True
    return False


class WebsiteProcessor(BaseProcessor):
    def getModel(self):
        return Website
    
    def create(self, params):
        params['key_name'] = Website.keyName(params['domain'])
        return BaseProcessor.create(self, params)
        

def get_rawclick_bucket_key(time,userHashCode):
    return 'rawclick_bucket'+ str(userHashCode) + ':' + str(datetimeparser.intMinute(time))
    

def get_rawclick_bucket(time,userHashCode):
    key = get_rawclick_bucket_key(time,userHashCode)
    bucket = memcache.get(key)
    if bucket is None:
        return []
    else:
        return bucket


def raw_click_for_post(urlHash, post, postParent, referrer, country):
    uid = postParent.uid
    userHashCode = uid%url_const.RAW_CLICK_HASH_SIZE
    rawClick = dict(userHashCode=userHashCode,uid=uid,post=post,referrer=referrer,country=country,createdTime=datetime.datetime.utcnow())
    _cache_raw_click(rawClick)


def raw_click_for_spost(urlHash, username, referrer, country):
    post = GlobalShortUrl.get_post_by_surl(urlHash)
    if post is None:
        logging.error("Post not found: urlHash '%s', parent '%s'" % (urlHash, username))  
    else:      
        postParent = StandardCampaignParent.get_by_key_name(StandardCampaignParent.keyName(username))
        try:
            raw_click_for_post(urlHash, post, postParent, referrer, country)
            logging.debug("Create raw click succeeded for user %s."%(postParent.key().name()))
        except Exception:
            logging.exception("Create raw click failed for post short url '%s' of user '%s'!" 
                              % (urlHash, postParent.key().name())) 
#        """ Use different GA parameters to track redirect clicks. """
#        globalUrl = GlobalUrl.get_by_url(post.url)
#        if globalUrl and globalUrl.toSoup and globalUrl.titleKey is not None: 
#            channel = post.get_channel()
#            if channel:
#                utc = {}
#                utc['utm_medium']='Twitter/'+channel.name
#                utc['utm_source']='SNS.Analytics'
#                url = 'http://%s/soup/%s'%(deploysoup.DOMAIN_MAP[context.get_context().application_id()],globalUrl.titleKey)
#                if globalUrl.videoSrc is not None and globalUrl.videoSrc!= '':
#                    utc['utm_campaign'] = 'RedirectR01'
#                    url = url + '?' + urllib.urlencode(utc)
#                elif globalUrl.mediaUrl is not None and globalUrl.mediaUrl != '':
#                    utc['utm_campaign'] = 'RedirectT01'
#                    url = url + '?' + urllib.urlencode(utc)
    

def raw_click_for_surl(urlHash, referrer, country):
    globalShortUrl = GlobalShortUrl.get_by_surl(urlHash)
    if globalShortUrl is None :
        return
    username = globalShortUrl.campaignParent.keyNameStrip()
    raw_click_for_spost(urlHash, username, referrer, country)


def raw_click_for_url(url, referrer, country):
    userHashCode = random.randint(0, url_const.RAW_CLICK_HASH_SIZE-1)
    _cache_raw_click(dict(userHashCode=userHashCode, url=url, referrer=referrer, country=country, createdTime=datetime.datetime.utcnow()))
    logging.debug("Create raw click succeeded for url %s." % (url,))


def _cache_raw_click(rawClick):
    if users.is_current_user_admin() and not context.get_context().count_admin_user_clicks() and not context.is_dev_mode():
        logging.debug("Admin raw click. Not counted!")
        return
    userHashCode = rawClick['userHashCode']
    time = rawClick['createdTime']
    bucket_key = get_rawclick_bucket_key(time, userHashCode)
    bucket = get_rawclick_bucket(time, userHashCode)
    bucket.append(rawClick)
    logging.info("Cached raw click to bucket '%s' at %s" % (bucket_key, time))
    memcache.set(bucket_key, bucket, time=url_const.RAW_CLICK_CACHE_MINUTES*60)
    

def is_browser_cake_compatible():
    _CAKE_SUPPORTED_BROWSERS = (common_const.BROWSER_CHROME, common_const.BROWSER_FIREFOX)
    _CAKE_UNSUPPORTED_DEVICES = common_const.DEVICES_IOS
    if context.get_context().browser() is None :
        return False
    if context.get_context().device() is not None and context.get_context().device() in _CAKE_UNSUPPORTED_DEVICES :
        return False
    if context.get_context().browser() in _CAKE_SUPPORTED_BROWSERS :
        return True
    return False

    