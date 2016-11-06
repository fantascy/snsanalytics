import logging
import random
import urllib
import urllib2
import json
from google.appengine.ext import db
from sns.serverutils import memcache
from django.http import HttpResponse
from django.shortcuts import render_to_response
from django.template import RequestContext

import context
from sns.core import core as db_core
from sns.cont.models import Topic
from sns.url.models import GlobalUrlCounter, GlobalUrl
from soup.api import consts as api_const
from soup import consts as soup_const
from soup.user.api import getArticleRatingQuery, current_user
from soup.rank.api import getSoupArticles
from soup.topic.api import get_custom_topics
from soup.user.models import UserComment, SoupUser
from soup.api.facade import iapi as iapi
from soup.view.controllerview import ControllerView, ContentView, FacebookArticleNode, ArticleInfo, SOUP_FACEBOOK_PAGE

RATING_LOG_PAGE_SIZE = 2

class ArticleView(ContentView, ArticleInfo, FacebookArticleNode):
    def __init__(self, globalUrlCounter):
        ContentView.__init__(self)
        ArticleInfo.__init__(self, 
                             globalUrlCounter=globalUrlCounter,
                             globalUrl=globalUrlCounter.globalUrl())
        FacebookArticleNode.__init__(self, 
                                     url=ArticleInfo.fullUrl(self), 
                                     title=ArticleInfo.globalUrl(self).title, 
                                     description=ArticleInfo.globalUrl(self).description,
                                     image=ArticleInfo.globalUrl(self).getThumbnail(),
                                     )
        ratingQuery = getArticleRatingQuery(globalUrlCounter.key().name()) 
        self.ratingCount = ratingQuery.count()
        self.ratingLog =  ratingQuery.fetch(limit=RATING_LOG_PAGE_SIZE, offset=0) 
        self.ratingOffset = len(self.ratingLog) 
        self.ratingSize = min(RATING_LOG_PAGE_SIZE, self.ratingCount-self.ratingOffset)
        try:
            if SoupUser.get_by_id(int(self.counter.uid)) == self.loginUser:
                self.isAuthor = True
        except:
            pass

    def isArticleView(self):
        return True
    
    def name(self):
        return "Article"
    
    def pageTitle(self):
        return self.globalUrl().title
    
    def pageDescription(self):
        return self.globalUrl().description
    
    def recommendationSize(self):
        if self.topArticlesTodayMediaType()==soup_const.MEDIA_TYPE_VIDEO_STR :
            return 5
        else :
            return 3

    def recommendations(self):
        articleIds = getSoupArticles(self.counter.firstTopicKey(),soup_const.RANK_TYPE_HOT,self.topArticlesTodayMediaType())[:10]
        if self.counter.id in articleIds:
            articleIds.remove(self.counter.id)
        rids = random.sample(articleIds, min(len(articleIds),self.recommendationSize()))
        return ArticleInfo.toList([db_core.normalize_2_model(rid) for rid in rids])
    
    def contentDiscoveryTopOn(self):
        return True

    def sideColumnFacebookPage(self):
        return SOUP_FACEBOOK_PAGE
    
    def topArticlesTodayMediaType(self):
        if self.counter.mediaType == soup_const.MEDIA_TYPE_VIDEO :
            return soup_const.MEDIA_TYPE_VIDEO_STR
        return soup_const.MEDIA_TYPE_ALL_STR

    def currentTopic(self):
        return self.topic
    
    def mainTopic(self):
        if self.topic.name in soup_const.MAIN_TOPIC_NAMES:
            return self.topic
        elif len(self.topic.parentTopics) > 0:
            return Topic.get_by_topic_key(self.topic.parentTopics[0])
        else:
            return {'id':None,'keyNameStrip':None}
        
    def customTopics(self):
        return get_custom_topics(self.topicKey)
    
    def keywords(self):
        tags = self.globalUrl().tags
        if tags is None or tags == '':
            return ContentView.keywords(self)
        else:
            return self.globalUrl().tags
    
    
def _rating_ajax_template(request):
    ref = request.REQUEST.get("ref", None)
    if ref is None or ref=="thumbnail_list" or ref=="article" :
        return "soup/rating/rating.html"
    elif ref=="media_list" :
        return "soup/topic/media_list_rating.html"
        

def article_view(request, globalUrlCounter=None, template="soup/article/article.html"):
    try:
        view = ArticleView(globalUrlCounter=globalUrlCounter)
        referrer = context.get_context().http_user_referrer()
        response = render_to_response(template,dict(view=view,object=view,referrer=referrer),context_instance=RequestContext(request))
        response['Last-Modified'] = view.counter.modifiedTime.strftime('%a, %d %b %Y %H:%M:%S GMT')
        return response
    except Exception, e:
        logging.exception("Error: %s! Request path: %s" % (e.message, context.get_context().request_full_path()))
    return HttpResponse(status=404)


def article_main(request, title):
    globalUrl = GlobalUrl.get_by_title_key(title)
    if globalUrl is None :
        return ControllerView.page_not_found()
    return article_view(request, globalUrlCounter=GlobalUrlCounter.get_by_key_name(globalUrl.key().name()))


def article_rate(request):
    """ The old score from request may be obsolete, in the case of pre-login rating. """
    oldUserRating = iapi(api_const.SOUP_API_M_USER).get_article_rating(request.REQUEST)
    if oldUserRating is None :
        oldScore = 0
    else :
        oldScore = oldUserRating.rating
    rateParams = {'id': request.REQUEST['id'],
                  'oldscore': oldScore,
                  'newscore': request.REQUEST['newscore'],
                  }
    iapi(api_const.SOUP_API_M_USER).rate(rateParams)
    globalUrlCounter = iapi(api_const.API_M_GLOBAL_COUNTER).rate(rateParams)
    memcache.delete(globalUrlCounter.id)
    if oldUserRating is None :
        user = current_user()
        userCounter = user.getCounter()
        userCounter.ratingCount += 1
        userCounter.put()
    return article_view(request, globalUrlCounter=globalUrlCounter, template=_rating_ajax_template(request))

def get_rating_log(request):
    offset = int(request.REQUEST.get("offset", 0))
    keyname = request.REQUEST.get("keyname",'')
    ratingQuery = getArticleRatingQuery(keyname) 
    ratings = ratingQuery.fetch(limit=RATING_LOG_PAGE_SIZE,offset=offset)
    return render_to_response('soup/article/rating_logs.html',dict(view=ContentView(),ratings=ratings),context_instance=RequestContext(request))
    
def get_comment_count(request):
    titleKey = request.REQUEST.get("titlekey")
    globalUrl = GlobalUrl.all().filter('titleKey', titleKey).fetch(limit=1)[0]
    globalUrlCounter = GlobalUrlCounter.get_by_key_name(globalUrl.key().name())
    return HttpResponse(globalUrlCounter.commentCount)
    
def article_comment(request):
    id = request.REQUEST.get("id")
    link = request.REQUEST.get("link")
    type = int(request.REQUEST.get("type",1))
    titleKey = link[link.rfind('/')+1:]
    globalUrl = GlobalUrl.all().filter('titleKey', titleKey).fetch(limit=1)[0]
    globalUrlCounter = GlobalUrlCounter.get_by_key_name(globalUrl.key().name())
    if type == 1:
        globalUrlCounter.commentCount += 1
        globalUrlCounter.put()
        params = {}
        query = 'SELECT comments_fbid FROM link_stat WHERE url= "%s"'%link 
        params['query'] =query
        params['format'] = 'json'
        url = 'https://api.facebook.com/method/fql.query?' +urllib.urlencode(params)
        data = urllib2.urlopen(url)
        content = data.read()
        info = json.loads(content)
        comments_fbid = info[0]['comments_fbid']
        params = {}
        query = 'SELECT text, fromid FROM comment WHERE object_id = %s AND post_fbid= %s'%(comments_fbid,id)
        params['query'] =query
        params['format'] = 'json'
        url = 'https://api.facebook.com/method/fql.query?' +urllib.urlencode(params)
        data = urllib2.urlopen(url)
        content = data.read()
        info = json.loads(content)
        if len(info) > 0:
            userComment = UserComment(key_name=UserComment.keyName(id), message=info[0]['text'],articleUrl=globalUrlCounter.keyNameStrip(),fid=info[0]['fromid'])
            userComment.put()
            user = current_user(login_required=False)
            if user is not None:
                counter = user.getCounter()
                counter.commentCount += 1
                counter.put()
    elif type == 0:
        globalUrlCounter.commentCount -= 1
        globalUrlCounter.put()
        userComment = UserComment.get_by_key_name(UserComment.keyName(id))
        if userComment is not None:
            db.delete(userComment)
            user = current_user(login_required=False)
            if user is not None:
                counter = user.getCounter()
                counter.commentCount -= 1
                counter.put()    
    return HttpResponse(globalUrlCounter.commentCount)


def article_click(request):
    return ControllerView.article_click(request)
    

def article_delete(request):
    id = request.REQUEST.get('id')
    globalUrlCounter = db.get(id)
    loginUser = current_user(login_required=False)
    if loginUser is not None and loginUser.key().id() == globalUrlCounter.uid:
        if not globalUrlCounter.deleted:
            globalUrlCounter.deleted = True;
            globalUrlCounter.put();
            counter = loginUser.getCounter()
            counter.postCount -= 1
            counter.put()
            return HttpResponse('success')
        else: 
            return HttpResponse('already deleted')
    else:
        return HttpResponse('fail')
