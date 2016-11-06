import datetime 
import logging
import urllib
from google.appengine.ext import db
from django.http import HttpResponse
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.http import HttpResponseRedirect
from django.views.generic.simple import direct_to_template

import context, deploysns, deploysoup
from twitter.api import TwitterApi
from common.utils import string as str_util, url as url_util
from common.utils.facebook import GraphAPI
from sns.serverutils import deferred
from sns.post.api import getFbActions,StandardCampaignProcessor
from sns.url.api import ShortUrlProcessor
from sns.url.models import ShortUrlReserve, GlobalUrlCounter, GlobalUrl, SoupPost, isImageUrl
from common.content import pageparser
from sns.serverutils import memcache
from sns.cont.models import Topic
from sns.core.core import SoupCampaignParent
from sns.url import api as url_api
from soup import consts as soup_const
from soup.user.api import current_user
from soup.topic.api import get_custom_topics, get_topic_name_by_key
from soup.commonutils.cookie import get_ip_mem_key
from forms import ShareForm
from soup.view.controllerview import ContentView, SOUP_FACEBOOK_PAGE
from soup.topic.views import hot_articles
        

class ShareArticleView(ContentView):
    def __init__(self, form, pics, link, mediaType, videoSrc):
        ContentView.__init__(self)
        self.form = form
        self.pics = pics
        self.defaultPic = None 
        if len(pics)>0 :
            self.defaultPic = pics[0]
        self.link = link
        self.mediaType = mediaType
        self.videoSrc = videoSrc
        self.popularTopics = ShareArticleView._popular_topics()
        
    @classmethod
    def _popular_topics(cls):
        """
        TODO: Pick topics that include all level 1 topics, and 10 trending topics.
        Later, we will use keyword match to make this popular topics more relevant.
        """ 
        topicNames = []
        trendingTopics = get_custom_topics(Topic.soup_frontpage_topic().keyNameStrip())
        for topic in trendingTopics :
            topicNames.append(topic.name)
        return soup_const.MAIN_MENU + topicNames
         
    def name(self):
        return "Share Article"
    
    def mediaUrl(self):
        return self.defaultPic
        
    def sideColumnFacebookPage(self):
        return SOUP_FACEBOOK_PAGE
    
    def thumbnailsInOneLine(self):
        if len(self.pics)>5 :
            return ""
        else :
            return "thumbnails-in-one-line"
    
    
def home(request):
    return hot_articles(request, Topic.soup_frontpage_topic().keyNameStrip() ,soup_const.MEDIA_TYPE_ALL_STR )
    
    
def login(request):
    return direct_to_template(request,'soup/login.html')
    
    
def share_check(request):
    link = request.POST.get('link','')
    if not link.startswith('http://') and not link.startswith('https://'):
        msg = "Invalid URL!"
        return render_to_response('soup/share/share_error.html', 
                  {'type':1,'msg':msg},
                  context_instance=RequestContext(request)) 
    if len(link) > 500:
        msg = "URL too long!"
        return render_to_response('soup/share/share_error.html', 
                  {'type':1,'msg':msg},
                  context_instance=RequestContext(request)) 
    
    nLink = GlobalUrl.normalize(link)
    globalUrlCounter = GlobalUrlCounter.get_by_key_name(GlobalUrlCounter.keyName(nLink))
    if globalUrlCounter is not None:
        globalUrl = GlobalUrl.get_by_key_name(GlobalUrl.keyName(nLink))
        type = 0
        memcache.set(get_ip_mem_key('notice'), soup_const.NOTICE_TYPE_SHARE_ARTICLE_DUP)
        url = "/soup/%s"% (globalUrl.titleKey)
        data = "%d%s"%(type,url)
    else:
        type = 2
        data = type
    return HttpResponse(data)
    
    
def share(request):
    user = current_user(login_required=False)
    if user is None:
        return HttpResponse("User login required!") 
    link = request.POST.get('link')
    title = ''
    description = ''
    pics = []
    form_params = {}
    info = url_util.fetch_url(link)
    parser = pageparser.SPageParser()
    parser.feed(info,is_quick=True)
    title =  parser.get_title()
    if len(parser.ps) > 0:
        description = parser.ps[0]
    elif len(parser.br) > 0:
        description = parser.br[0]
    description = str_util.strip(description)
    
    if len(parser.pics) > 0:
        for pic in parser.pics:
            if not url_api.is_ads(pic,parser.domain):
                pics.append(pic)
    videoSrc = ''
    if len(parser.video) > 0:
        mediaType = soup_const.MEDIA_TYPE_VIDEO
        videoSrc = parser.video[0]
        pics = [parser.videoImg]
    elif isImageUrl(link) :
        mediaType = soup_const.MEDIA_TYPE_IMAGE
    else :
        mediaType = soup_const.MEDIA_TYPE_NORMAL
    form_params['title'] = title
    form_params['description'] = description
    form_params['mediaType'] = mediaType
    if parser.keywords is not None:
        keywords = parser.keywords.strip()
        keywords = keywords.replace('\n', ',').replace('  ',' ').replace('\t',' ')[:500]
    else:
        keywords = ''
    form_params['keywords'] = keywords
    form_params['showImg'] = True
    form_params['postToFacebook'] = True
    if user.tChannel is not None :
        form_params['postToTwitter'] = True
    else :
        form_params['postToTwitter'] = False
        
    form = ShareForm(initial=form_params)
    return render_to_response("soup/share/share.html",
                              dict(view=ShareArticleView(form=form,pics=pics,link=link,mediaType=mediaType,videoSrc=videoSrc)),
                              context_instance=RequestContext(request))    


def share_form_check(request):
    topicName = request.REQUEST.get('topic')
    title = request.REQUEST.get('title')
    topic = Topic.get_by_name(topicName)
    response = ''
    if topic is None:
        response += 'topic_'
    if len(title.strip()) == 0:
        response += 'title_'
    return HttpResponse(response)


def share_confirm(request):
    user = current_user(login_required=True)
    link = request.REQUEST.get('link')
    title = request.REQUEST.get('title',None).replace('\n',' ')
    showImg = request.REQUEST.get('showImg',None)
    picture = request.REQUEST.get('picture',None)
    description = request.REQUEST.get('description',None)
    keywords = request.REQUEST.get('keywords',None)
    topicName = request.REQUEST.get('topic')
    topic = Topic.get_by_name(topicName).keyNameStrip()
    mediaType = int(request.REQUEST.get('mediaType',soup_const.MEDIA_TYPE_NORMAL))
    videoSrc = request.REQUEST.get('videoSrc','')
    globalUrl = GlobalUrl.get_or_insert_by_url(link)
    globalUrl.title = str_util.slice(title,'0:490')
    globalUrl.description = description
    globalUrl.tags = keywords
    if showImg is not None:
        globalUrl.mediaUrl = picture
    else:
        globalUrl.mediaUrl = ''
    if mediaType == soup_const.MEDIA_TYPE_VIDEO:
        globalUrl.videoSrc = videoSrc
    globalUrl.put()
    globalUrlCounter = GlobalUrlCounter.get_or_insert_by_url(link)
    globalUrlCounter.topics = [topic]
#    globalUrlCounter.topicsForNew = Topic.get_topics_for_new(topic)
    globalUrlCounter.mediaType = mediaType
    globalUrlCounter.uid = user.uid
    globalUrlCounter.userName = user.name
    globalUrlCounter.increment(size=1,clickTime=datetime.datetime.utcnow())
    globalUrlCounter.put()
    userCounter = user.getCounter()
    userCounter.postCount += 1
    userCounter.put()
    postToFacebook = request.REQUEST.get('postToFacebook',None)
    if postToFacebook == 'on':
        deferred.defer(_deferredPostFacebook,user.id,globalUrl.id)
    postToTwitter = request.REQUEST.get('postToTwitter',None)
    if postToTwitter == 'on':
        deferred.defer(_deferredPostTwitter,user.id,globalUrl.id)
    memcache.set(get_ip_mem_key('notice'), soup_const.NOTICE_TYPE_SHARE_ARTICLE)
    url = "/soup/%s" % (str_util.title_2_key(title))
    url = url.encode('utf-8')
    url = urllib.quote(url,safe='/?=')
    return HttpResponseRedirect(url)

def update(request):
    id = request.REQUEST.get('id')
    req_type = request.REQUEST.get('reqtype')
    globalUrlCounter = db.get(id)
    globalUrl = globalUrlCounter.globalUrl()
    user = current_user(login_required=True)
    if user is None or user.uid != globalUrlCounter.uid:
        msg = 'You are not allowed to edit this article!'
        return render_to_response('soup/share/share_error.html', 
                  {'type':1,'msg':msg},
                  context_instance=RequestContext(request)) 
    if req_type == 'check':
        return HttpResponse('success')
    link = globalUrl.keyNameStrip()
    title = globalUrl.title
    description = globalUrl.description
    topic = get_topic_name_by_key(globalUrlCounter.firstTopicKey())
    pics = []
    form_params = {}
    info = url_util.fetch_url(link)
    parser = pageparser.SPageParser()
    parser.feed(info,is_quick=True)
    if len(parser.pics) > 0:
        for pic in parser.pics:
            if not url_api.is_ads(pic,parser.domain):
                pics.append(pic)
    videoSrc = ''
    if len(parser.video) >0:
        mediaType = soup_const.MEDIA_TYPE_VIDEO
        videoSrc = parser.video[0]
        pics = [parser.videoImg]
    else:
        mediaType = soup_const.MEDIA_TYPE_NORMAL
    form_params['title'] = title
    form_params['description'] = description
    form_params['topic'] = topic
    form_params['mediaType'] = mediaType
    if parser.keywords is not None:
        keywords = parser.keywords.strip()
        keywords = keywords.replace('\n', ',').replace('  ',' ').replace('\t',' ')[:500]
    else:
        keywords = ''
    form_params['keywords'] = keywords
    form_params['showImg'] = True
    form_params['postToFacebook'] = True
    if user.tChannel is not None :
        form_params['postToTwitter'] = True
    else :
        form_params['postToTwitter'] = False
        
    form = ShareForm(initial=form_params)
    return render_to_response('soup/share/share_edit.html',
                              dict(view=ShareArticleView(form=form,pics=pics,link=link,mediaType=mediaType,videoSrc=videoSrc)),
                              context_instance=RequestContext(request))   

def update_confirm(request):
    user = current_user(login_required=True)
    link = request.REQUEST.get('link')
    title = request.REQUEST.get('title',None).replace('\n',' ')
    showImg = request.REQUEST.get('showImg',None)
    picture = request.REQUEST.get('picture',None)
    description = request.REQUEST.get('description',None)
    keywords = request.REQUEST.get('keywords',None)
    topicName = request.REQUEST.get('topic')
    topic = Topic.get_by_name(topicName).keyNameStrip()
    mediaType = int(request.REQUEST.get('mediaType',soup_const.MEDIA_TYPE_NORMAL))
    videoSrc = request.REQUEST.get('videoSrc','')
    globalUrl = GlobalUrl.get_or_insert_by_url(link)
    globalUrl.title = str_util.slice(title,'0:490')
    globalUrl.description = description
    globalUrl.tags = keywords
    if showImg is not None:
        globalUrl.mediaUrl = picture
    else:
        globalUrl.mediaUrl = ''
    if mediaType == soup_const.MEDIA_TYPE_VIDEO:
        globalUrl.videoSrc = videoSrc
    globalUrl.put()
    globalUrlCounter = GlobalUrlCounter.get_or_insert_by_url(link)
    globalUrlCounter.topics = [topic]
#    globalUrlCounter.topicsForNew = Topic.get_topics_for_new(topic)
    globalUrlCounter.mediaType = mediaType
    globalUrlCounter.uid = user.uid
    globalUrlCounter.userName = user.name
    globalUrlCounter.increment(size=1,clickTime=datetime.datetime.utcnow())
    globalUrlCounter.put()
    postToFacebook = request.REQUEST.get('postToFacebook',None)
    if postToFacebook == 'on':
        deferred.defer(_deferredPostFacebook,user.id,globalUrl.id)
    postToTwitter = request.REQUEST.get('postToTwitter',None)
    if postToTwitter == 'on':
        deferred.defer(_deferredPostTwitter,user.id,globalUrl.id)
    memcache.set(get_ip_mem_key('notice'), soup_const.NOTICE_TYPE_SHARE_ARTICLE)
    url = "/soup/%s" % (globalUrl.titleKey)
    url = url.encode('utf-8')
    url = urllib.quote(url,safe='/?=')
    return HttpResponseRedirect(url)
    

def _deferredPostFacebook(userId,globalUrlId):
    context.set_deferred_context(deploy=deploysoup)
    user = db.get(userId)
    globalUrl = db.get(globalUrlId)
    url = "http://%s/soup/%s"%(context.get_context().long_domain(),globalUrl.titleKey)
    try:
        graph = GraphAPI(user.fChannel.oauthAccessToken)
        try:
            actions = getFbActions(url)
        except:
            actions = ''
        graph.put_object('me', 'feed', picture=globalUrl.getThumbnail().encode('utf-8'),link=url.encode('utf-8'),
                         name=globalUrl.title.encode('utf-8'),description=str_util.slice(globalUrl.description,'0:490').encode('utf-8'),actions=actions)
        logging.info('Post url %s to facebook successfully!'%url)
    except Exception :
        logging.exception('Soup Error when post url %s to facebook %s'%(url,user.email))
        

def _deferredPostTwitter(userId,globalUrlId):
    context.set_deferred_context(deploy=deploysoup)
    user = db.get(userId)
    globalUrl = db.get(globalUrlId)
    url = "http://%s/soup/%s"%(context.get_context().long_domain(),globalUrl.titleKey)
    try:
        soupParent = SoupCampaignParent.get_or_insert_parent(user.uid)
        shortUrlResv = ShortUrlReserve.get_by_key_name(soupParent.key().name(),parent=soupParent)
        if shortUrlResv is None:
            shortUrlResv = ShortUrlReserve(key_name=soupParent.key().name(),firstCharacter=ShortUrlProcessor.randomFirstCharacter(),parent=soupParent)
            shortUrlResv.put()
        urlMappingIdBlocks = ShortUrlProcessor.consumeShortUrlReserve(shortUrlResv.id, 1)
        urlHash = shortUrlResv.firstCharacter + ShortUrlProcessor.extractShortUrlFromResv(urlMappingIdBlocks)
        post = SoupPost(key_name=urlHash,url=url,parent=soupParent)
        post.put()
        shortUrl = " http://%s/%s"%(deploysns.SHORT_DOMAIN_MAP[context.get_context().application_id()],urlHash)
        msg = StandardCampaignProcessor()._twitter_str_to_display(globalUrl.title, shortUrl, '', '')
        twitter = TwitterApi(oauth_access_token=user.tChannel.oauthAccessToken)
        twitter.statuses.update(status=msg) 
        logging.info('Post url %s to twitter successfully!'%url)
    except Exception :
        logging.exception('Soup Error when post url %s to twitter %s'%(url,user.email))   