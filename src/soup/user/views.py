import urllib
import logging
import urllib2
from sets import Set
import json

from google.appengine.ext import db
from django.views.generic.list_detail import object_list
from django.http import HttpResponseRedirect
from django.http import HttpResponse
from django.shortcuts import render_to_response
from django.template import RequestContext
from twitter.api import TwitterApi
from twitter.oauth import TwitterOAuthClient

from common.utils.string import split_strip
import context
from sns.serverutils import deferred
from sns.log import consts as log_const
from sns.url.models import GlobalUrlCounter
from soup.view.controllerview import ContentView, FacebookPageNode, ArticleInfo, SOUP_FACEBOOK_PAGE
import consts as user_const
from sns.serverutils import memcache
from soup.commonutils.cookie import get_ip_mem_key
from common.utils.facebook import GraphAPI
from deploysoup import FACEBOOK_OAUTH_MAP, DOMAIN_MAP
from soup import consts as soup_const
from soup.commonutils import pagination
from models import TChannel, SoupUser, UserArticleRating, UserArticleFollowing, UserComment, FChannel, Friendship
from soup.api.facade import iapi
from soup.api import consts as api_const
from soup.user.api import current_user, clear_current_user


class CommentedArticleInfo(ArticleInfo):
    def __init__(self, globalUrlCounter, comment):
        ArticleInfo.__init__(self, globalUrlCounter)
        self.comment = comment

    @classmethod
    def userComment2ArticleInfo(cls, userComment):
        return cls(globalUrlCounter=GlobalUrlCounter.get_by_key_name(GlobalUrlCounter.keyName(userComment.articleUrl)), comment=userComment)
        
    @classmethod
    def userCommentList2List(cls, userCommentList):
        return [cls.userComment2ArticleInfo(userComment) for userComment in userCommentList]
    

class ProfileRatedArticleInfo(ArticleInfo):
    def __init__(self, globalUrlCounter, profileUserRating):
        ArticleInfo.__init__(self, globalUrlCounter)
        self.profileUserRating = profileUserRating

    @classmethod
    def profileUserRating2ArticleInfo(cls, profileUserRating):
        return cls(globalUrlCounter=GlobalUrlCounter.get_by_key_name(profileUserRating.key().name()), profileUserRating=profileUserRating)
        
    @classmethod
    def profileUserRatingList2List(cls, profileUserRatingList):
        return [cls.profileUserRating2ArticleInfo(profileUserRating) for profileUserRating in profileUserRatingList]
    

class ProfileView(ContentView, FacebookPageNode):
    def __init__(self, user, article_type):
        ContentView.__init__(self)
        self.user = user
        self.articleType = article_type
        if user == self.loginUser:
            self.currentUserProfile = True
        
    def name(self):
        return self.user.name
    
    def _keywords(self):
        return ContentView._keywords(self) + [self.user.name] 
    
    def pageTitle(self):
        return self.og_title()

    def pageDescription(self):
        return self.og_description()

    def ogEnabled(self):
        """ We are not yet ready to map our user profile page to Facebook Open Graph. """
        return 'False'

    def og_title(self):
        return "%s on Allnewsoup" % self.user.name
    
    def og_type(self):
        return "blog"
    
    def og_url(self):
        """TODO: get user's username as the profile URL. """
        return self.user.url()
    
    def og_description(self):
        return "TODO: get user bio as description"

    def sideColumnFacebookPage(self):
        return SOUP_FACEBOOK_PAGE
    
    def articleTypeMap(self):
        return user_const.USER_OBJ_LIST_MAP
    
    def hideArticleUserInfo(self):
        return self.articleType==user_const.USER_OBJ_LIST_POSTS


def _submitted_articles(user):
    objects = GlobalUrlCounter.all().filter('uid', user.oid()).filter('deleted',False).order('-createdTime')
    return ArticleInfo.toList(objects[:100])
    

def _rated_articles(user):
    objects = UserArticleRating.all().ancestor(user).order('-createdTime')
    return ProfileRatedArticleInfo.profileUserRatingList2List(objects[:100])
    

def _commented_articles(user):
    if user.fChannel is None:
        objects = []
    else:
        objects = UserComment.all().filter('fid',int(user.fChannel.keyNameStrip())).order('-createdTime')
    return CommentedArticleInfo.userCommentList2List(objects[:100])
    

def _followed_articles(user):
    objects = UserArticleFollowing.all().ancestor(user)
    return ArticleInfo.userFollowedList2List(objects[:100])
    

_ARTICLE_INFO_HANDLE_MAP = {
    user_const.USER_OBJ_LIST_POSTS : _submitted_articles,
    user_const.USER_OBJ_LIST_RATINGS : _rated_articles,
    user_const.USER_OBJ_LIST_COMMENTS : _commented_articles,
    user_const.USER_OBJ_LIST_FOLLOWING_POSTS : _followed_articles,
    }


def _profile_view(request, user, article_type):
    objects = _ARTICLE_INFO_HANDLE_MAP[int(article_type)](user)
    paginate_by = 10
    path = pagination.get_path(request)
    page_numbers = pagination.get_page_numbers(request, paginate_by, len(objects))
    return object_list( request, 
                        objects,
                        paginate_by=paginate_by,
                        extra_context = {'view':ProfileView(user=user, article_type=article_type),'path':path,'page_numbers':page_numbers},
                        template_name="soup/user/profile.html"
                       )
    

def profile(request, uid):
    article_type = int(request.REQUEST.get('atype', user_const.USER_OBJ_LIST_POSTS))
    user = SoupUser.get_by_id(int(uid))
    if user is None :
        return HttpResponseRedirect('/')
    return _profile_view(request, user=user, article_type=article_type)


def user_name(request):
    user = current_user(login_required=False)
    if user is None:
        id = ''
        name = ''
    else:
        id = user.uid
        name = user.name
    data = json.dumps(dict(id=id,name=name), indent=4)
    return HttpResponse(data, mimetype='application/javascript')

FRIENDS_PAGE_SIZE = 20

class FriendsView(ContentView):
    def __init__(self, user, offset):
        ContentView.__init__(self)
        self.user = user
        friendIdsQuery = Friendship.all().filter('userId', self.user.uid).order('-modifiedTime')
        friendships = friendIdsQuery.fetch(limit=FRIENDS_PAGE_SIZE, offset=offset)
        friendIds = [friendship.friendId for friendship in friendships]
        self.friends = SoupUser.get_by_id(friendIds)
        self.friendsOffset = offset+len(self.friends)
        self.friendsCount = friendIdsQuery.count()
        self.friendsSize = len(self.friends)
        
    def name(self):
        return self.user.name
    
    def _keywords(self):
        return ContentView._keywords(self) + [self.user.name] 
    
    def pageTitle(self):
        return "Allnewsoup user friends - %s" % self.user.name

    def pageDescription(self):
        return self.pageTitle()

    def sideColumnFacebookPage(self):
        return SOUP_FACEBOOK_PAGE


def _friends_view(request, template, offset):
    return render_to_response(template, dict(view=FriendsView(user=current_user(login_required=True), offset=offset)), context_instance=RequestContext(request))


def friends(request):
    return _friends_view(request, template='soup/user/friends.html', offset=0)


def get_more_friends(request):
    return _friends_view(request, template='soup/user/more_friends.html', offset=int(request.REQUEST.get("offset", FRIENDS_PAGE_SIZE)))
    

class SettingsView(ContentView):
    def __init__(self, user):
        ContentView.__init__(self)
        self.user = user
        
    def name(self):
        return self.user.name
    
    def _keywords(self):
        return ContentView._keywords(self) + [self.user.name] 
    
    def pageTitle(self):
        return "Allnewsoup user settings - %s" % self.user.name

    def pageDescription(self):
        return self.pageTitle()

    def sideColumnFacebookPage(self):
        return SOUP_FACEBOOK_PAGE
    

def user_setting(request):
    user = current_user(login_required=True)
    return render_to_response('soup/user/settings.html', dict(view=SettingsView(user=user)), context_instance=RequestContext(request))
    

def user_toggle_article_follow(request):
    result = iapi(api_const.SOUP_API_M_USER).toggle_article_follow(request.REQUEST)
    data = json.dumps(dict(result=result), indent=4)
    return HttpResponse(data, mimetype='application/javascript') 
    
    
def facebook_login(request):
    params = {}
    params['client_id'] = FACEBOOK_OAUTH_MAP[context.get_context().application_id()]['id']
    params['redirect_uri'] =  'http://'+DOMAIN_MAP[context.get_context().application_id()]
    params['response_type'] = 'token'
    params['display']='popup'
    params['scope']='email'
    url = 'https://www.facebook.com/dialog/oauth?' + urllib.urlencode(params)
    return HttpResponseRedirect(url) 

def twitter_login(request):
    client = TwitterOAuthClient()
    url=client.get_request_token()
    return HttpResponseRedirect(url)

def twitter_callback(request):
    client = TwitterOAuthClient()
    oauth_token_str = request.GET.get("oauth_token",'')
    if oauth_token_str=='':
        return HttpResponseRedirect("/settings/")
    access_token=client.callback(oauth_token_str)
    twitterInfo = TwitterApi(oauth_access_token=access_token).account.verify_credentials()
    key_name = TChannel.keyName(twitterInfo['id'])
    channel = TChannel.get_by_key_name(key_name)
    if channel is None:
        channel = TChannel(key_name=key_name,uid=twitterInfo['id'],avatarUrl=twitterInfo['profile_image_url'],username=twitterInfo['screen_name'],oauthAccessToken=access_token,
                               name=twitterInfo['name'],nameLower=twitterInfo['name'].lower(),url="http://www.twitter.com/"+twitterInfo['screen_name'])
        channel.put()
    users = SoupUser.all().filter('tChannel', channel).fetch(limit=1)
    if len(users) > 0:
        memcache.set(get_ip_mem_key('notice'), soup_const.NOTICE_TYPE_TWITTER_CONNECT_DUP)
        return HttpResponseRedirect('/settings/')
    user = current_user()
    user.tChannel = channel
    user.put()
    clear_current_user()
    return HttpResponseRedirect('/settings/')

def twitter_disconnect(request):
    user = current_user()
    user.tChannel = None
    user.put()
    clear_current_user()
    return HttpResponse('disconnect')


def friend_invite(request):
    id = request.POST.get('id')
    name = request.POST.get('name')
    toChannel = FChannel.get_by_key_name(FChannel.keyName(id))
    if toChannel is not None:
        return HttpResponse('exist')
    user = current_user()
    channel = user.fChannel
    graph = GraphAPI(channel.oauthAccessToken)
    msg = "%s, I'm tasting all new soup. I think you may be interested to try out as well." % name.split()[0]
    try:
        picture = soup_const.ALL_NEW_SOUP_IMAGE
        graph.put_object(id, "feed", 
                         message=msg,
                         name="Allnewsoup",
                         link="http://%s/?ref=invite"%context.get_context().long_domain(), 
                         description=ProfileView.defaultPageTitle(),
                         picture=picture)
        logging.info('Sent invite msg to %s' % id)
    except Exception,ex:
        logging.error('Error when send invite msg to %s : %s'%(id,str(ex)))
        return HttpResponse("fail")
    invited = user.fbInvitedFriends()
    invited.add((id,name))
    channel.invitedFriends = str(invited)
    channel.put()
    mem_key = soup_const.INVITE_FRIENDS_KEY + str(user.uid)
    memcache.delete(mem_key)
    memcache.delete(FChannel.keyName(channel.uid))
    return HttpResponse('success')

BASE_FIELDS = ['name','email','location','link']
FRIEND_FIELDS = ['friends']
        
def facebook_realtime(request):
    if request.method=='GET' and request.REQUEST.get('hub.mode')=='subscribe' and request.REQUEST.get('hub.verify_token')== log_const.FACEBOOK_REAL_TIME_VERIFY_TOKEN :
        logging.error('Get facebook challenge!')
        return HttpResponse(request.REQUEST.get('hub.challenge'),'text/plain')
    elif request.method=='POST':
        logging.info('post request:%s'%str(request.POST))
        for info in request.POST.keys():
            info = json.loads(info)
            if info['object'] == 'user':
                for entry in info['entry']:
                    fid = entry['uid']
                    base_change = False
                    friend_change = False
                    logging.info('uid : %s, change field: %s'%(entry['uid'],str(entry['changed_fields'])))
                    for field in entry['changed_fields']:
                        if field in BASE_FIELDS:
                            base_change = True
                        if field in FRIEND_FIELDS:
                            friend_change = True
                    if base_change:
                        logging.info('defer base sync')
                        deferred.defer(sync_facebook_base,fid)
                    if friend_change:
                        logging.info('defer friend sync')
                        deferred.defer(sync_facebook_friend,fid)
        return HttpResponse('success')
    
def sync_facebook_base(fid):
    try:
        fChannel = FChannel.get_by_key_name(FChannel.keyName(fid))
        if fChannel is None:
            logging.error('FChannel %s not found when sync for facebook realtime'%fid)
        else:
            access_token = fChannel.oauthAccessToken
            profile = json.load(urllib2.urlopen(
                "https://graph.facebook.com/me?" +
                urllib.urlencode(dict(access_token=access_token,fields='id,name,picture,link,email,location'))))
            if profile.has_key('location'):
                location = profile['location']['name']
            else:
                location = None
            fChannel.location = location
            fChannel.name = profile['name']
            fChannel.nameLower = profile['name'].lower()
            fChannel.avatarUrl = profile['picture']
            fChannel.url = profile['link']
            fChannel.email = profile['email']
            fChannel.put()
            syncSoupUserFacebook(fChannel)
            logging.info('Sync facebook base for %s'%fid)
    except Exception:
        logging.exception('Unknown error when sync facebook realtime for %s'%fid)
        
def sync_facebook_friend(fid):
    try:
        fChannel = FChannel.get_by_key_name(FChannel.keyName(fid))
        if fChannel is None:
            logging.error('FChannel %s not found when sync for facebook realtime'%fid)
        else:
            access_token = fChannel.oauthAccessToken
            graph = GraphAPI(access_token)
            friends = graph.get_connections('me','friends')['data']
            newFriends = Set()
            for friend in friends:
                newFriends.add((friend['id'],friend['name']))
            oldFriends = fChannel.getFriends()
            soupFriends = fChannel.getSoupFriends()
            add = newFriends - oldFriends
            remove = oldFriends - newFriends
            for a in add:
                fa = FChannel.get_by_key_name(FChannel.keyName(a[0]))   
                if fa is not None:
                    soupFriends.add(a)
                    db.put(Friendship(key_name=Friendship.keyName(fid+':'+a[0]),userId=int(fid),friendId=int(a[0])))
            for r in remove:
                if r in soupFriends:
                    soupFriends.remove(r)
            fChannel.soupFriends = str(soupFriends)  
            fChannel.allFriends = str(newFriends)
            fChannel.put()
            syncSoupUserFacebook(fChannel)
            logging.info('Sync facebook friend for %s'%fid)
    except Exception:
        logging.exception('Unknown error when sync facebook realtime for %s'%fid)
         
def syncSoupUserFacebook(fChannel):
    users = SoupUser.all().filter('fChannel', fChannel).fetch(limit=1)
    if len(users) == 0:
        logging.error('Soup user not found for %s when sync'%fChannel.keyNameStrip())
        return
    user = users[0]
    user.name = fChannel.name
    user.nameLower = fChannel.nameLower
    user.avatarUrl = fChannel.avatarUrl
    user.email = fChannel.email
    locationInfo = split_strip(fChannel.location,',')
    if len(locationInfo)==2 :
        user.city = locationInfo[0] 
        user.country = locationInfo[1] 
    user.put()
    memcache.delete(fChannel.key().name())
    
