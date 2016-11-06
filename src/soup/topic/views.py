import random
from datetime import datetime
from django.shortcuts import render_to_response
from sns.serverutils import memcache
from django.views.generic.simple import redirect_to
from django.template import RequestContext
from django.views.generic.list_detail import object_list
from django.utils import feedgenerator
from django.http import HttpResponseRedirect
from django.http import HttpResponse
import context
from common.utils import string as str_util
from common.utils import datetimeparser
from sns.cont.models import Topic
from common.utils import iplocation
from soup.commonutils import pagination
from soup import consts as soup_const
from soup.api import errors as api_error
from soup.user.api import current_user
from soup.topic.api import get_custom_topics
from soup.topic.models import SoupFeed
from soup.rank.api import getSoupArticles, getTopMaxKey, getFreshArticles
from soup.view.controllerview import ContentView, FacebookPageNode, ControllerView, ArticleInfo, SOUP_FACEBOOK_PAGE


TOPIC_DESCRIPTION_FORMAT_MAP = {
    0 : "%s",                                
    1 : "Socially curated %s news, pictures, videos, and comments.",
    2 : "Socially curated news, pictures, videos, and comments about %s.",
    }


class TopicView(ContentView, FacebookPageNode):
    def __init__(self, topicKey=Topic.soup_frontpage_topic().keyNameStrip(), rank=soup_const.RANK_TYPE_HOT, mediaType=soup_const.MEDIA_TYPE_ALL_STR, timeRange="week"):
        ContentView.__init__(self)
            
        self.topicKey = topicKey
        self.rank = rank
        self.mediaType = mediaType
        self.timeRange = timeRange
        self._fbTopicView = None
        self.topic = Topic.get_by_topic_key(topicKey)
        """ Temporarily work around topic extended info load issue. """
        FacebookPageNode.__init__(self, node=SOUP_FACEBOOK_PAGE)
#        if topicKey==Topic.soup_frontpage_topic().keyNameStrip() :
#            FacebookPageNode.__init__(self, node=SOUP_FACEBOOK_PAGE)
#        else :
#            FacebookPageNode.__init__(self,
#                                      type="blog",
#                                      url="http://%s/%s" % (self.ctx().long_domain(), self.topic.keyNameStrip()),
#                                      title="Allnewsoup %s" % self.topic.name,
#                                      image=self.topic.image,
#                                      description=TopicView.normalized_description(self.topic),
#                                      )
        
    def currentTopic(self):
        return self.topic
    
    def mainTopic(self):
        if self.topic.name in soup_const.MAIN_TOPIC_NAMES or self.topic.name==Topic.soup_frontpage_topic().name:
            return self.topic
        elif len(self.topic.parentTopics) > 0:
            return Topic.get_by_topic_key(self.topic.parentTopics[0])
        else:
            return {'id':None,'keyNameStrip':None}
        
    def customTopics(self):
        return get_custom_topics(self.topicKey)
    
    def isFrontPage(self):
        return self.topic == Topic.soup_frontpage_topic()

    def name(self):
        return self.topic.name
    
    def _keywords(self):
        """ TODO: need add parent topics, and put into memcache. """
        return ContentView._keywords(self) + [self.topic.name] 
    
    def pageTitle(self):
        return self.og_title()

    def pageDescription(self):
        return self.og_description()

    @classmethod
    def normalized_description(cls, topic):
        """ A raw description looks like "0", "1", "2", "1;$lowercase", "2;New York City", etc. """
        description = str_util.strip(topic.description)
        if description is None :
            description = "0"
        descrParts = description.split(';')
        format = TOPIC_DESCRIPTION_FORMAT_MAP.get(int(descrParts[0]), None)
        if format is None :
            raise api_error.ApiError(api_error.SOUP_API_ERROR_BAD_TOPIC_DESCRIPTION, topic.name, description)
        if len(descrParts)==1 :
            descrPart2 = topic.name
        else :
            descrPart2 = descrParts[1].strip()
            if descrPart2=="$lowercase" :
                descrPart2 = topic.name.lower()
        return format % (descrPart2,)
                                                  
    def sideColumnFacebookPage(self):
        if self._fbTopicView is None :
            if self.topic.fbTopicSelf() :
                self._fbTopicView = self
            else : 
                self._fbTopicView = TopicView(topicKey=self.topic.fbTopic)
        return self._fbTopicView
    
    def sideColumnTwitterAccount(self):
        if self.topic.twitter is None or self.topic.twitter=='none':
            return None
        else:
            return self.topic.twitter

    def topArticlesTodayMediaType(self):
        if self.mediaType == soup_const.MEDIA_TYPE_VIDEO_STR :
            return soup_const.MEDIA_TYPE_VIDEO_STR
        return soup_const.MEDIA_TYPE_ALL_STR

    def topArticlesTodayOn(self):
        return not Topic.is_special_topic_key(self.topicKey)


def front_page_topic_view():
    return TopicView(topicKey=Topic.soup_frontpage_topic().keyNameStrip(), rank=soup_const.RANK_TYPE_HOT,mediaType=soup_const.MEDIA_TYPE_ALL_STR, timeRange='week')

def default_articles(request,topic):
    return topic_view(request,topic,rank=soup_const.RANK_TYPE_HOT,media=soup_const.MEDIA_TYPE_ALL_STR)

def hot_articles(request,topic,media):
    return topic_view(request,topic,rank=soup_const.RANK_TYPE_HOT,media=media)

def new_articles(request,topic,media):
    return topic_view(request,topic,rank=soup_const.RANK_TYPE_NEW,media=media)


def top_articles(request,topic,media,range):
    return topic_view(request,topic,rank=soup_const.RANK_TYPE_TOP,media=media,timeRange=range)


def topic_view(request,topicKey,rank,media,timeRange=None):
    format = request.GET.get('format',None)
    if format == 'rss':
        return soup_feed(request,topicKey)
    context.get_context().set_login_required(False)
    if topicKey != Topic.soup_frontpage_topic().keyNameStrip():
        theTopic = Topic.get_by_topic_key(topicKey)
        if theTopic is None or theTopic.deleted:
            return ControllerView.page_not_found() 
    if media not in soup_const.MEDIA_TYPE_STRS:
        return HttpResponseRedirect('/') 
    page = int(request.GET.get('page',1))
    paginate_by = 10
    pageRange = ((page-1)*paginate_by,page*paginate_by)
    if rank == soup_const.RANK_TYPE_HOT:
        articleInfos = ArticleInfo.toList(getSoupArticles(topicKey,rank,media),pageRange=pageRange)
    elif rank == soup_const.RANK_TYPE_NEW:
        articleInfos = ArticleInfo.toList(getSoupArticles(topicKey,rank,media),pageRange=pageRange)
    elif rank == soup_const.RANK_TYPE_TOP:
        articleInfos = ArticleInfo.toList(getSoupArticles(topicKey,rank,media,timeRange),pageRange=pageRange)
    topicView = TopicView(topicKey=topicKey, rank=rank, mediaType= media, timeRange=timeRange)
    path = pagination.get_path(request)
    page_numbers = pagination.get_page_numbers(request, paginate_by, len(articleInfos))
    topic_suffix = get_topic_suffix(rank,media,timeRange)
    if rank == soup_const.RANK_TYPE_TOP :
        topInfo = timeRange + ":" + getTopMaxKey(topicKey,media,timeRange)
    else:
        topInfo = ''
    currentTime = str(datetime.now())
    return object_list( request, 
                        articleInfos,
                        paginate_by=paginate_by,
                        extra_context = {'view':topicView,'path':path,'page_numbers':page_numbers,'topic_suffix':topic_suffix,'rankType':rank,'topInfo':topInfo, 'currentTime':currentTime},
                        template_name="soup/topic/topic.html",
                       )

def get_topic_suffix(rank,media,timeRange):
    if rank == soup_const.RANK_TYPE_HOT and media == soup_const.MEDIA_TYPE_ALL_STR:
        return ""
    elif rank == soup_const.RANK_TYPE_TOP :
        return "/top/" + media + '/' + timeRange
    else:
        return "/" + soup_const.RANK_TYPE_MAP[rank] + "/" + media

def topic_search(request):
    keyword = request.REQUEST.get('query','') 
    if keyword == '':
        topics = []
    else: 
        topics = Topic.searchIndex.search(keyword,filters=('deleted =',False))
    if len(topics) == 0:
        return render_to_response('soup/topic/search.html',dict(view=ContentView()),
                                      context_instance=RequestContext(request,{"path":request.path})) 
    else:
        topic = topics[0]
        return redirect_to(request,url="/%s"%topic.keyNameStrip())
    
def topic_feel_lucky(request):
    mem_key = 'feel_lucky_topics'
    lucky_topics = memcache.get(mem_key)
    if lucky_topics is None:
        lucky_topics = []
        topics = Topic.all().fetch(limit=1000)
        for topic in topics:
            if not topic.name in soup_const.MAIN_MENU and topic.c24h > 0:
                lucky_topics.append(topic.keyNameStrip())
        memcache.set(mem_key, lucky_topics, time=3600)
    if len(lucky_topics) == 0:
        return HttpResponse(Topic.all().fetch(limit=1)[0].keyNameStrip())
    index = random.randint(0,len(lucky_topics)-1)
    return HttpResponse(lucky_topics[index])
    
def topic_local(request):
    user = current_user(login_required=False)
    if user is not None:
        countryTopic = user.getCountryTopic()
    else:
        countryTopic = None
    if countryTopic is None:
        ip = request.META.get("REMOTE_ADDR","")
        country_info = iplocation.get_country_info_by_qqlib(ip)
        name = country_info[3]
        topics = Topic.all().filter('name', name).fetch(limit=1)
        if len(topics)> 0:
            countryTopic = topics[0]
        else:
            countryTopic = Topic.get_by_topic_key('us')
    titleKey = countryTopic.keyNameStrip()
    if len(getSoupArticles(titleKey,soup_const.RANK_TYPE_HOT,soup_const.MEDIA_TYPE_ALL_STR))==0:
        if len(countryTopic.parentTopics) > 0:
            titleKey = countryTopic.parentTopics[0]
    return HttpResponse(titleKey)
        
def topic_find(request):
    name = request.REQUEST.get('name','') 
    topic = Topic.all().filter('name',name)[0]
    return HttpResponse(topic.keyNameStrip())
        
def soup_feed(request,topicKey):
    context.get_context().set_login_required(False)
    feed = SoupFeed.get_by_key_name(SoupFeed.keyName(topicKey))
    if feed is None:
        return HttpResponse(status=404)
    f = feedgenerator.Atom1Feed(title = feed.title,description=feed.description,link=feed.feedUrl())
    for item in feed.items:
        item = eval(item)
        f.add_item(title = item['title'], link= item['url'], description=item['description'])
    info = f.writeString('utf-8')
    return HttpResponse(info,'text/html')

def fresh_articles(request):
    topic = request.REQUEST.get('topic')
    media = request.REQUEST.get('mediatype')
    lastRefreshTimeStr = request.REQUEST.get('lastrefresh')
    lastRefreshTime = datetimeparser.parseDateTime(lastRefreshTimeStr)
    freshArticles = getFreshArticles(topic, media, lastRefreshTime)
    newTime = str(datetime.now())
    if not freshArticles:
        return HttpResponse(newTime + '|0|none')
    articleInfos = ArticleInfo.toList(freshArticles)
    topicView = TopicView(topicKey=topic, rank=soup_const.RANK_TYPE_NEW, mediaType= media, timeRange=None)
    return render_to_response("soup/topic/more_articles.html", dict(view=topicView,object_list=articleInfos,new_time=newTime),context_instance=RequestContext(request))