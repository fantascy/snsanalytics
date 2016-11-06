import logging
from sets import ImmutableSet

from google.appengine.ext import db

import context, deploysoup
from sns.core import core as db_core
from sns.serverutils import deferred, memcache
from sns.core.core import SystemStatusMonitor
from sns.url.models import GlobalUrlCounter, HotArticleCache
from sns.cont.models import Topic
from sns.cont.topic.api import TopicCacheMgr
from sns.api import consts as api_const
from soup import consts as soup_const
from soup.api.base import BaseProcessor


#    COMMENTED AWAY CODE for Facebook Page posting and Topic Feed
#def _deferredExecutionFeedHandler(processorClass, topicKey):
#    context.set_deferred_context(deploy=deploysoup)
#    return processorClass().executeFeed(topicKey)
#
#
#def _deferredExecutionPostHandler(processorClass, topicKey):
#    context.set_deferred_context(deploy=deploysoup)
#    return processorClass().executePost(topicKey)


class ArticleRankProcessor(BaseProcessor):
    pass


class TopicRankProcessor(BaseProcessor):
    @classmethod
    def supportedOperations(cls):
        return ImmutableSet([api_const.API_O_CRON_EXECUTE]).union(BaseProcessor.supportedOperations())
    
    _MEM_KEY_HOT_ARTICLES_CRON_START = "soup_rank_mem_key_hot_articles_cron_start"   
    _MEM_KEY_HOT_ARTICLES_CRON_CURSOR = "soup_rank_mem_key_hot_articles_cron_cursor"   
     
    def cron_execute(self, params):
        deferred.defer(set_hot_cache, queueName='hot')
        

def set_hot_cache():
    context.set_deferred_context(deploy=deploysoup)
    TopicCacheMgr.rebuild_if_cache_not_valid()
    topicKeys = TopicCacheMgr.get_all_topic_keys()
    topicKeys = list(Topic.SPECIAL_TOPIC_KEYS) + topicKeys
    total = len(topicKeys)
    logging.info("Hot articles cache - building cache for %d topics." % total)
    count = 0
    while count<total:
        try :
            deferred.defer(set_hot_cache_batch, topicKeys[count:count+100], queueName='hot')
            count += 100
        except:
            logging.exception("Hot articles cache exception:")
    

def set_hot_cache_batch(topicKeys):
    context.set_deferred_context(deploy=deploysoup)
    count = 0
    try :
        for topicKey in topicKeys:
            cacheHotArticles(topicKey)
            count += 1
    except:
        logging.exception("Hot articles cache exception after finished building %d topics: " % count)
    if count<len(topicKeys):
        logging.error("Hot articles cache - finished building %d out of a batch of %d topics." % (count, len(topicKeys)))
    else:
        logging.info("Hot articles cache - finished building a batch of %d topics." % len(topicKeys))


#    COMMENTED AWAY CODE for Facebook Page posting and Topic Feed
#    def cron_execute(self, params): 
#        context.set_deferred_context(deploy=deploysoup)
#        topicKeys = TopicCacheMgr.get_all_topic_keys()
#        topicKeys.append(Topic.soup_frontpage_topic().keyNameStrip())
#        for topicKey in topicKeys:
#            deferred.defer(_deferredExecutionPostHandler, processorClass=self.__class__, topicKey=topicKey)
#    
#    def executePost(self, topicKey):
#        if topicKey == Topic.soup_frontpage_topic().keyNameStrip():
#            topicUrl = "http://%s/"%(context.get_context().long_domain())
#        else:
#            topicUrl = "http://%s/%s"%(context.get_context().long_domain(),topicKey)
#        articles = getSoupArticles(topicKey,soup_const.RANK_TYPE_HOT,soup_const.MEDIA_TYPE_ALL)
#        if len(articles) == 0:
#            return 
#        hots = articles[:5]
#        for hot in hots:
#            hot = db.get(hot)
#            globalUrl = hot.globalUrl()
#            if str_util.empty(globalUrl.description) or str_util.empty(globalUrl.getThumbnail()):
#                continue
#            try:
#                url = "https://graph.facebook.com/feed"
#                params = {}
#                params['id'] = topicUrl
#                params['access_token'] = deploysoup.FACEBOOK_OAUTH_MAP[context.get_context().application_id()]['access_token']
#                params['link'] = hot.soupLink()
#                params['name'] = globalUrl.title
#                params['description'] = globalUrl.description
#                params['picture'] = globalUrl.getThumbnail()
#                for key in params.keys():
#                    params[key] = params[key].encode('utf-8')
#                info = urllib.urlopen(url, data=urllib.urlencode(params)).read()
#                if info.find('error') != -1:
#                    if info.find('not resolve to a valid user ID') != -1:
#                        logging.warning('Error when do og post %s for %s' % (info, topicUrl))
#                    else:
#                        logging.error('Error when do og post %s for %s' % (info, topicUrl))
#                else:
#                    logging.info('Do og post %s for %s' % (info, topicUrl))
#            except Exception:
#                logging.exception('Unknown error when do og post for %s' % topicUrl)
#            break
#    
#    def executeFeed(self, topicKey):
#        if topicKey == Topic.soup_frontpage_topic().keyNameStrip():
#            title = "All New Soup"
#            description = "Socially curated news, pictures, videos, and comments."
#        else:
#            topic = Topic.get_by_topic_key(topicKey)
#            title = topic.name
#            description = topic.description
#        soupFeed = SoupFeed.get_or_insert(key_name=SoupFeed.keyName(topicKey),title=title,description=description)
#        articles = getSoupArticles(topicKey,soup_const.RANK_TYPE_HOT,soup_const.MEDIA_TYPE_ALL)
#        if len(articles) == 0:
#            return
#        urls = Set()
#        for item in soupFeed.items:
#            item = eval(item)
#            urls.add(item['url'])
#        articles = articles[:50]
#        for article in articles:
#            article = db_core.normalize_2_model(article)
#            url = article.keyNameStrip()
#            if url in urls:
#                continue
#            item = {}
#            globalUrl = GlobalUrl.get_by_key_name(GlobalUrl.keyName(url))
#            item['url'] = url
#            item['link'] = "http://%s/soup/%s"%(context.get_context().long_domain(),globalUrl.titleKey)
#            item['title'] = globalUrl.title
#            item['description'] = globalUrl.description
#            item['picture'] = globalUrl.mediaUrl
#            soupFeed.items.insert(0, db.Text(str(item))) 
#            soupFeed.items = soupFeed.items[:50]
#            soupFeed.put()
#            logging.info('Add hot article for %s'%topicKey)
#            break
    

def getTopicMemKey(titleKey, rankType, mediaType):
    return "%s_%s_%s" % (titleKey, rankType, mediaType)


def getTopMaxKey(titleKey, mediaType, rankRange):
    return "%s_%s_%s"%(titleKey,mediaType,rankRange)
    

def getSoupArticles(topicKey, rankType, mediaType, rankRange=''):
    mediaType = soup_const.int_media_type(mediaType)
    if topicKey==Topic.TOPIC_KEY_PHOTOS :
        mediaType = soup_const.MEDIA_TYPE_IMAGE
    elif topicKey==Topic.TOPIC_KEY_VIDEOS :
        mediaType = soup_const.MEDIA_TYPE_VIDEO
    elif topicKey==Topic.TOPIC_KEY_FRONTPAGE :
        mediaType = soup_const.MEDIA_TYPE_NORMAL
    if rankType == soup_const.RANK_TYPE_NEW:
        return getNewArticles(topicKey, mediaType)
    else :
        """ TODO: remove this conversion! """
        return [articleCache.counterId for articleCache in getHotArticles(topicKey, mediaType)]


def getCacheTime(titleKey, rankType, rankRange):
    time = 0
    if rankType == soup_const.RANK_TYPE_HOT:
        time = 720
    elif rankType == soup_const.RANK_TYPE_TOP:
        if titleKey == Topic.soup_frontpage_topic().keyNameStrip():
            time = soup_const.TIME_CACHE[rankRange][1]
        else:
            time = soup_const.TIME_CACHE[rankRange][0]
    return time
        

def _top_100_articles(articles):
    articles = list(articles)
    for article in articles:
        article.recalculateHotScore()
    articles.sort(lambda x,y: cmp(x.hotScore, y.hotScore), reverse=True)
    articles = add_user_decay(articles)
    return articles[:100]


def _hot_cache_media_type(topicKey):
    if topicKey==Topic.TOPIC_KEY_FRONTPAGE : 
        return soup_const.MEDIA_TYPE_NORMAL
    elif topicKey==Topic.TOPIC_KEY_PHOTOS :
        return soup_const.MEDIA_TYPE_IMAGE
    elif topicKey==Topic.TOPIC_KEY_VIDEOS :
        return soup_const.MEDIA_TYPE_VIDEO
    else :
        return soup_const.MEDIA_TYPE_NORMAL


def _hot_cache_query(topicKey):
    query = db.Query(GlobalUrlCounter, keys_only=True).order('-createdTime')
    limit = 500
    mediaType = _hot_cache_media_type(topicKey)
    query = query.filter('mediaType', mediaType)
    if topicKey not in Topic.SPECIAL_TOPIC_KEYS :
        query = query.filter('topics', topicKey)
        limit = 100
    return query.fetch(limit=limit)


def cacheHotArticles(topicKey):
    topic = Topic.get_by_topic_key(topicKey)
    if topic is None:
        return []
    mediaType = _hot_cache_media_type(topicKey)
    dataSet = set([])
    dataList = []
    oldCacheMap = {}
    memKey = getTopicMemKey(topicKey, soup_const.RANK_TYPE_HOT, mediaType)
    oldCache = memcache.get(memKey)
    if oldCache is not None :
        for articleCache in oldCache :
            oldCacheMap[articleCache.counterId] = articleCache
    counterKeys = _hot_cache_query(topicKey)
    for counterKey in counterKeys :
        counterId = str(counterKey)
        if oldCacheMap.has_key(counterId) :
            articleCache = oldCacheMap.get(counterId)
        else : 
            counter = db_core.normalize_2_model(counterKey)
            articleCache = HotArticleCache(counter)
        articleCache.recalculateHotScore()
        dataSet.add(articleCache)
    topicMemKey = getTopicMemKey(topicKey, soup_const.RANK_TYPE_HOT, mediaType)
    if topicKey==Topic.TOPIC_KEY_FRONTPAGE :
        children = TopicCacheMgr.get_all_level_1_topic_keys()
        for child in children:
            childMemKey = getTopicMemKey(child, soup_const.RANK_TYPE_HOT, mediaType)
            topicArticleCache = memcache.get(childMemKey)
            if topicArticleCache is not None :
                dataSet.update(topicArticleCache)
        filteredDataList = list(dataSet)
        _cache_hot_topics(filteredDataList)
        dataList = _top_100_articles(filteredDataList)
    else :
        children = Topic.get_child_topic_keys(topicKey)
        if not topic.excludeChildContents :
            for child in children :
                childMemKey = getTopicMemKey(child, soup_const.RANK_TYPE_HOT, mediaType)
                topicArticleCache = memcache.get(childMemKey)
                if topicArticleCache is not None :
                    dataSet.update(topicArticleCache)
        dataList = _top_100_articles(dataSet)
    memcache.set(topicMemKey, dataList, time=18000)
    return dataList
    

_MEM_KEY_HOT_TOPICS = "soup_rank_mem_key_hot_topics"   


def _cache_hot_topics(hotArticleCaches):
    """
    Topics are ranked by aggregated scores of all scores of articles having the topic. 
    """
    topicScoreMap = {}
    for article in hotArticleCaches :
        for topicKey in article.topicKeys :
            topicScore = topicScoreMap.get(topicKey, 0)
            topicScore += article.hotScore
            topicScoreMap[topicKey] = topicScore
    topicScores = topicScoreMap.items()
    topicScores.sort(lambda x,y: cmp(x[1], y[1]),reverse=True)
    hotTopicKeys = [topicScore[0] for topicScore in topicScores[:10]]
    hotTopics = Topic.keys_2_objs(hotTopicKeys)[:6]
    hotTopicKeys = [topic.keyNameStrip() for topic in hotTopics]
    if len(hotTopics)>0 :
        memcache.set(_MEM_KEY_HOT_TOPICS, hotTopics)
        SystemStatusMonitor(key_name=_MEM_KEY_HOT_TOPICS, info=str(hotTopicKeys)).put()
    return hotTopics
    

def get_hot_topics():
    hotTopics = memcache.get(_MEM_KEY_HOT_TOPICS)
    if hotTopics is None :
        monitor = SystemStatusMonitor.get_by_key_name(_MEM_KEY_HOT_TOPICS)
        if monitor is None :
            return []
        else :
            hotTopicKeys = eval(monitor.info)
            hotTopics = Topic.keys_2_objs(hotTopicKeys)
            memcache.set(_MEM_KEY_HOT_TOPICS, hotTopics)
    return hotTopics
    

def getHotArticles(topicKey, mediaType):
    memKey = getTopicMemKey(topicKey, soup_const.RANK_TYPE_HOT, mediaType)
    cache = memcache.get(memKey)
    if cache is None :
        return cacheHotArticles(topicKey)
    else :
        return cache
    

def getNewArticles(topicKey, mediaType):
    query = GlobalUrlCounter.all().order('-createdTime')
#    if topicKey in Topic.SPECIAL_TOPIC_KEYS :
#        pass
#    else :
#        query = query.filter('topicsForNew', topicKey)
    if mediaType == soup_const.MEDIA_TYPE_IMAGE:
        query = query.filter('mediaType', soup_const.MEDIA_TYPE_IMAGE)
    elif mediaType == soup_const.MEDIA_TYPE_VIDEO:
        query = query.filter('mediaType', soup_const.MEDIA_TYPE_VIDEO)
    return query.fetch(limit=100)


def getFreshArticles(topicKey, mediaType, lastRefreshTime):
    query = GlobalUrlCounter.all().order('-createdTime')
#    if topicKey == Topic.soup_frontpage_topic().keyNameStrip():
#        pass
#    else :
#        query = query.filter('topicsForNew', topicKey)
    if mediaType == soup_const.MEDIA_TYPE_IMAGE:
        query = query.filter('mediaType', soup_const.MEDIA_TYPE_IMAGE)
    elif mediaType == soup_const.MEDIA_TYPE_VIDEO:
        query = query.filter('mediaType', soup_const.MEDIA_TYPE_VIDEO)
    size = query.count()
    result = [];
    offset = 0;
    while True:
        results = query.fetch(limit=1, offset=offset)
        if len(results)==0 :
            break
        globalUrlCounter = results[0]
        if globalUrlCounter.createdTime < lastRefreshTime:
            break
        result.append(globalUrlCounter)
        offset += 1
        if offset >= size:
            break
    return result


def getTopArticles(topicKey, mediaType, rankRange):
    """ DB_OPT Skip all top queries. """ 
    return []
    

def add_user_decay(articles):
    user_keys = {}
    for article in articles:
        uid = article.uid
        if user_keys.has_key(uid):
            user_keys[uid] = user_keys[uid]*2
        else:
            user_keys[uid] = 1
        article.hotScore = article.hotScore*10/user_keys[uid]
    articles.sort(lambda x,y: cmp(x.hotScore, y.hotScore),reverse=True)
    return articles
