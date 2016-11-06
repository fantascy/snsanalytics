import logging

from django.http import HttpResponse
from django.shortcuts import render_to_response
from django.template import RequestContext

import context
from sns.serverutils import memcache
from sns.core import core as db_core
from sns.cont.models import Topic
from sns.url.models import GlobalUrlCounter, GlobalUrl
from soup.rank import api as soup_rank_api
from soup.view import controllerview as soup_controllerview
from cake import consts as cake_const
from cake.topic import api as cake_topic_api
from cake.view.controllerview import ControllerView, ContentView, ArticleInfo
from forms import TopicForm


class ArticleView(ContentView, ArticleInfo):
    def __init__(self, request, globalUrlCounter):
        ContentView.__init__(self)
        ArticleInfo.__init__(self, 
                             globalUrlCounter=globalUrlCounter,
                             globalUrl=globalUrlCounter.globalUrl())
        self.surl = request.GET.get('surl', None)
        currentTopicKey = request.GET.get('topic', None)
        if currentTopicKey is None :
            topicKeys = globalUrlCounter.topics
            ancestorTopics = []
            if self.topic is not None :
                for topicKey in topicKeys:
                    topic = Topic.get_by_topic_key(topicKey)
                    if topic is None :
                        continue
                    ancstors = topic.ancestorTopics
                    for ancestor in ancstors:
                        ancestorTopics.append(ancestor)
            allMatchedTopics = topicKeys + ancestorTopics
            cookieTopicKey = context.get_context().cookie('currentTopic')
            if cookieTopicKey is not None : 
                if cookieTopicKey==Topic.TOPIC_KEY_FRONTPAGE \
                    or (cookieTopicKey==Topic.TOPIC_KEY_PHOTOS and globalUrlCounter.mediaType==cake_const.MEDIA_TYPE_IMAGE) \
                    or (cookieTopicKey==Topic.TOPIC_KEY_VIDEOS and globalUrlCounter.mediaType==cake_const.MEDIA_TYPE_VIDEO) \
                    or cookieTopicKey in allMatchedTopics : 
                    currentTopicKey = cookieTopicKey 
            if currentTopicKey is None :
                if self.topic.parentTopics is not None and len(self.topic.parentTopics)>0 :
                    currentTopicKey = self.topic.parentTopics[0]
                else :
                    currentTopicKey = self.topicKey
        if currentTopicKey==self.topicKey :
            self.currentTopic = self.topic
        else :
            self.currentTopic = Topic.get_by_topic_key(currentTopicKey)
        self.topicForm = TopicForm(initial={'topic':currentTopicKey}) 
        self.referrer = context.get_context().http_user_referrer()

        self.nextCake = None
        counterIds = cake_topic_api.get_hot_articles(currentTopicKey, cake_const.MEDIA_TYPE_ALL, set([globalUrlCounter.id]))
        if len(counterIds) > 0:
            nextCounter = db_core.normalize_2_model(counterIds[0])
            self.nextCake = nextCounter.globalUrl()
        self.recommendations = ArticleInfo.toList(counterIds[:5])
        
    def name(self):
        return "Article"
    
    def pageTitle(self):
        return "RippleOne - %s" % self.globalUrl().title 
    
    def pageDescription(self):
        return self.globalUrl().description
    
    def relatedStoriesTitle(self):
        currentTopicKey = self.currentTopic.keyNameStrip()
        if currentTopicKey==Topic.TOPIC_KEY_PHOTOS :
            return "Popular Photos"
        elif currentTopicKey==Topic.TOPIC_KEY_VIDEOS :
            return "Popular Videos"
        else :
            return "Related Stories"
                
    def popularTopics(self):
        return soup_rank_api.get_hot_topics()
    
    def keywords(self):
        tags = self.globalUrl().tags
        if tags is None or tags == '':
            return ContentView.keywords(self)
        else:
            return self.globalUrl().tags
    
    
def article_main(request, title):
    try:
        if title=='None':
            logging.error("Global URL title is none.")
            return ControllerView.page_not_found()
        globalUrl = GlobalUrl.get_by_title_key(title)
        if globalUrl is None:
            logging.error("Global URL is none for title: %s" % title)
            return ControllerView.page_not_found()
        globalUrlCounter=GlobalUrlCounter.get_by_key_name(globalUrl.key().name())
        if globalUrlCounter is None :
            logging.error("GlobalUrlCounter is None for URL %s" % globalUrl.url())
            return ControllerView.page_not_found()
        view = ArticleView(request=request, globalUrlCounter=globalUrlCounter)
        response = render_to_response("cake/article/article.html", dict(view=view,object=view), context_instance=RequestContext(request))
        response['Last-Modified'] = view.counter.modifiedTime.strftime('%a, %d %b %Y %H:%M:%S GMT')
        return response
    except Exception, e:
        logging.exception("Error: %s! Request path: %s" % (e.message, context.get_context().request_full_path()))
    return HttpResponse(status=404)


def article_click(request):
    counterId = request.REQUEST.get("id")
    cookie = request.COOKIES
    if cookie.has_key(cake_const.COOKIE_USER_SESSION):
        session = cookie[cake_const.COOKIE_USER_SESSION]
        history = memcache.get(session)
        if history is None:
            history = set([])
        if not counterId in history:
            history.add(counterId)
            memcache.set(session, history, time=300)
    return soup_controllerview.ControllerView.article_click(request)
    

