import random
import logging

from django.template import Context as DjangoContext, Template as DjangoTemplate 
from django.views.defaults import page_not_found as django_page_not_found
from django.http import HttpResponse

import context
from common.utils import string as str_util 
from common.view.controllerview import ControllerView as CommonControllerView
from sns.serverutils import memcache
from sns.core import core as db_core
from sns.url.models import GlobalUrlCounter
from sns.url import api as sns_url_api
from sns.chan.models import TAccount
from sns.cont.models import Topic
from sns.cont.topic.api import TopicCacheMgr
from soup import consts as soup_const
from soup.commonutils.cookie import fbCookieName, twCookieName, get_ip_mem_key
from soup.api import errors as api_error
from soup.user import consts as user_const
from soup.user.models import SoupUser, Friendship
from soup.user.api import current_user
from soup.topic.api import get_custom_topics
from soup.rank.api import getSoupArticles


class ControllerView(CommonControllerView):
    def __init__(self):
        CommonControllerView.__init__(self)
        self.loginUser = current_user(login_required=False)
        self.const = soup_const
        self.userConst = user_const
    
    def name(self):
        return "Home"
    
    def topicNames(self):
        return TopicCacheMgr.get_all_topic_names()
    
    def fbCookieKey(self):
        return fbCookieName()
    
    def twCookieKey(self):
        return twCookieName()
    
    def articleRoot(self):
        return ControllerView.article_root() 
    
    @classmethod         
    def article_root(cls):
        return 'soup'
        
    @classmethod         
    def page_not_found(cls):
        return django_page_not_found(context.get_context().request(), template_name="soup/404.html")

    @classmethod
    def no_image_url(cls):
        import settings 
        return "%ssoup/images/no_image.png" % settings.MEDIA_URL
     
    @classmethod         
    def article_click(cls, request):
        country = request.POST.get("country", "")
        referrer = request.POST.get("referrer", "")
        surl = str_util.strip(request.REQUEST.get("surl", None))
        if surl is not None :
            sns_url_api.raw_click_for_surl(surl, referrer, country)
        else :
            url = request.REQUEST.get("url")
            sns_url_api.raw_click_for_url(url, referrer, country)
        return HttpResponse('success')

    @classmethod         
    def defaultPageTitle(cls):
        return Topic.soup_frontpage_topic().description

    def pageTitle(self):
        return ControllerView.defaultPageTitle()

    def pageDescription(self):
        return None

    def _keywords(self):
        return ["All New Soup", "Allnewsoup", "Socially Curated"]

    def keywords(self):
        return ','.join(self._keywords())
    
    def headerAdsOn(self):
        return False

    def sideAdsOn(self):
        return False

    def contentDiscoveryTopOn(self):
        return False

    def topArticlesTodayMediaType(self):
        return soup_const.MEDIA_TYPE_ALL_STR

    def topArticlesTodaySize(self):
        return 10

    def topArticlesToday(self):
        return ArticleInfo.toList(getSoupArticles(Topic.TOPIC_KEY_FRONTPAGE, soup_const.RANK_TYPE_TOP, self.topArticlesTodayMediaType(),soup_const.TIME_RANGE_DAY)[:self.topArticlesTodaySize()])

    def topArticlesTodayOn(self):
        return True

    def ogEnabled(self):
        """ Return 'True' for any view that corresponds to a Facebook Open Graph node. """
        return 'False'
    
    def notice(self):
        return memcache.get(get_ip_mem_key('notice'))

    def noticeMsg(self):
        key = get_ip_mem_key('notice')
        noticeType = memcache.get(key)
        if noticeType is None :
            return None
        memcache.delete(key)
        return soup_const.NOTICE_MSG_MAP.get(noticeType, None)


class FacebookOpenGraphNode(object):
    def __init__(self, type=None, url=None, title=None, image=None, description=None):
        self.ogEnabled = 'True'
        self._ogSiteName = "Allnewsoup"
        self._ogType = type
        self._ogUrl = url
        self._ogTitle = title
        self._ogImage = image
        self._ogDescription = description 
        
    def ogEnabled(self):
        return 'True'

    def og_site_name(self):
        if self._ogSiteName is None :
            raise api_error.ApiError(api_error.API_ERROR_DATA_MISSING, "og_site_name")
        else :
            return self._ogSiteName

    def og_title(self):
        if self._ogTitle is None :
            raise api_error.ApiError(api_error.API_ERROR_DATA_MISSING, "og_title")
        else :
            return self._ogTitle
    
    def og_type(self):
        if self._ogType is None :
            raise api_error.ApiError(api_error.API_ERROR_DATA_MISSING, "og_type")
        else :
            return self._ogType
    
    def og_url(self):
        if self._ogUrl is None :
            raise api_error.ApiError(api_error.API_ERROR_DATA_MISSING, "og_url")
        else :
            return self._ogUrl
    
    def og_image(self):
        return self._ogImage
        
    def og_description(self):
        return self._ogDescription


class FacebookPageNode(FacebookOpenGraphNode):
    def __init__(self, node=None, type=None, url=None, title=None, image=None, description=None):
        if node is None :
            FacebookOpenGraphNode.__init__(self,
                                type=type,
                                url=url,
                                title=title,
                                image=image, 
                                description=description)
        else :
            FacebookOpenGraphNode.__init__(self,
                                type=node.og_type(), 
                                url=node.og_url(),
                                title=node.og_title(),
                                image=node.og_image(),
                                description=node.og_description())


SOUP_FACEBOOK_PAGE = FacebookPageNode(
    type = "website",
    url = "http://www.allnewsoup.com/",
    title = "Allnewsoup",
    image = soup_const.ALL_NEW_SOUP_IMAGE,
    description = ControllerView.defaultPageTitle(),
    )


class FacebookArticleNode(FacebookOpenGraphNode):
    pass
    def __init__(self, url=None, title=None, description=None, image=None):
        FacebookOpenGraphNode.__init__(self, type="article", url=url, title=title, image=image, description=description)


class ArticleInfo():
    def __init__(self, globalUrlCounter, globalUrl=None, userRating=None):
        self.counter = globalUrlCounter
        self.topicKey = globalUrlCounter.firstTopicKey()
        self.topic = Topic.get_by_topic_key(self.topicKey)
        if self.topic is None :
            self.topicKey = Topic.TOPIC_KEY_FRONTPAGE
            self.topic = Topic.get_frontpage_topic()
        self._globalUrl = globalUrl
        self._author = None
        from soup.templatetags.souptags import userRating as user_rating
        if userRating is None:
            self.userRating = user_rating(self.counter.key())
        else :
            self.userRating = userRating

    @classmethod
    def userRating2ArticleInfo(cls, userRating):
        return cls(globalUrlCounter=GlobalUrlCounter.get_by_key_name(userRating.key().name()), 
                   userRating=userRating)
        
    @classmethod
    def userFollowed2ArticleInfo(cls, userFollowed):
        return cls(globalUrlCounter=GlobalUrlCounter.get_by_key_name(userFollowed.key().name()))
        
    @classmethod
    def userRatingList2List(cls, userRatingList):
        return [cls.userRating2ArticleInfo(userRating) for userRating in userRatingList]
    
    @classmethod
    def userFollowedList2List(cls, userFollowedList):
        return [cls.userFollowed2ArticleInfo(userFollowed) for userFollowed in userFollowedList]
    
    @classmethod
    def toList(cls, counterList, pageRange=None):
        infos = []
        for i in range(0,len(counterList)):
            counter = counterList[i]
            if pageRange is not None and ( i < pageRange[0] or i >= pageRange[1]):
                infos.append(None)
            else:
                counter = db_core.normalize_2_model(counter)
                if len(counter.topics)==0 :
                    logging.warn("Found no topic GlobalUrlCounter: %s" % counter.url())
                infos.append(ArticleInfo(globalUrlCounter=counter))
        return infos

    def articleRoot(self):
        return ControllerView.article_root() 
    
    def id(self):
        return self.counter.key()
    
    def globalUrl(self):
        if self._globalUrl is None :
            self._globalUrl = self.counter.globalUrl()
        return self._globalUrl
    
    def fullUrl(self):
        return "http://%s/%s/%s" % (self.ctx().long_domain(), self.articleRoot(), self.globalUrl().titleKey)

    def fullUrlDoubleEncode(self):
        urlTemplate = DjangoTemplate("http://%s/%s/{{urlTitleKey|iriencode}}" % (self.ctx().long_domain(), self.articleRoot()))
        return urlTemplate.render(DjangoContext({"urlTitleKey":self.globalUrl().titleKey}))

    def thumbnailUrl(self):
        url = self.globalUrl().getThumbnail()
        if str_util.empty(url) :
            return ControllerView.no_image_url()
        return url
         
    def fullImageUrl(self):
        url = self.globalUrl().getFullImage()
        if str_util.empty(url) :
            return ControllerView.no_image_url()
        return url
         
    def author(self):
        if self._author is None :
            self._author = SoupUser.get_by_id(self.counter.uid)
        return self._author
        
    def authorName(self):
        return self.counter.userName
    
    def authorId(self):
        return self.counter.uid
    
    def authorAvatar(self):
        return self.author().avatarUrl

    def snsUserEmail(self):
        """ Only consider Twitter channel for now. """
        channelNameLower = str_util.lower_strip(self.authorName())
        if channelNameLower is None :
            return None
        channels = TAccount.all().filter("deleted", False).filter('nameLower', channelNameLower)
        if len(channels)==0 :
            logging.warn("Twitter channel doesn't exist for article: %s" % self.fullUrl())
            return None
        for channel in channels :
            if channel.topics is not None and len(channel.topics)>0 :
                channelTopic = channel.topics[0]
            else :
                channelTopic = None
            if channelTopic==self.topicKey :
                return channel.userEmail
        logging.info("No Twitter channel found for handle '%s' and topic key '%s'" % (channelNameLower, self.topicKey))
        return None 
    
    def isFollowed(self):
        from soup.user.api import ChannelProcessor
        return ChannelProcessor().is_article_followed({'id':self.counter.key()})


class ContentView(ControllerView):
    def __init__(self):
        context.get_context().set_login_required(False)
        ControllerView.__init__(self)
        if self.loginUser is not None:
            friendIdsQuery = Friendship.all().filter('userId', self.loginUser.key().id()).order('-modifiedTime')
            friendships = friendIdsQuery.fetch(limit=14)
            friendIds = [friendship.friendId for friendship in friendships]
            self.friends = SoupUser.get_by_id(friendIds)
            self.friendsCount = friendIdsQuery.count()
    
    def name(self):
        return Topic.get_frontpage_topic().name
    
    def primaryColumnWidth(self):
        return 656
    
    def sideColumnWidth(self):
        return 300
    
    def sideColumnFacebookPage(self):
        pass
    
    def sideColumnTwitterAccount(self):
        fbPage = self.sideColumnFacebookPage()
        if fbPage is None :
            return None
        if fbPage.og_url() == SOUP_FACEBOOK_PAGE.og_url() :
            return "allnewsoup"
        else :
            return None
    
    def currentTopic(self):
        return {'id':None,'keyNameStrip':None}
    
    def mainTopic(self):
        return {'id':None,'keyNameStrip':None}

    def mainMenu2TopicKeyMap(self):
        return soup_const.MAIN_MENU_2_TOPIC_KEY_MAP
    
    def customTopics(self):
        return get_custom_topics(Topic.TOPIC_KEY_FRONTPAGE)
    
    def fbFriendInvites(self):
        user = self.loginUser
        if user is None:
            return None
        mem_key = soup_const.INVITE_FRIENDS_KEY + str(user.uid)
        friendInfos = memcache.get(mem_key)
        if friendInfos is None or len(friendInfos)<10:
            allFriends = user.fbFriends()
            invitedFriends = user.fbInvitedFriends()
            allFriends.difference_update(invitedFriends)
            friends = list(allFriends)[:10]
            friendInfos = []
            count = 0
            for friend in friends:
                friendInfos.append((count,friend[0],friend[1]))
                count += 1
            memcache.set(mem_key, friendInfos, time=600)
        return random.sample(friendInfos, min(len(friendInfos),10))
    
    def getSoupFriends(self):
        user = self.loginUser
        if user is None:
            return None
        mem_key = soup_const.SOUP_FRIENDS_KEY + str(user.uid)
        friendInfos = memcache.get(mem_key)
        if friendInfos is None or len(friendInfos)<10:
            soupFriends = user.friends()
            friends = list(soupFriends)[:10]
            friendInfos = []
            count = 0
            for friend in friends:
                friendInfos.append((count,friend[0],friend[1]))
                count += 1
            memcache.set(mem_key, friendInfos, time=600)
        return random.sample(friendInfos, min(len(friendInfos),10))
            
        