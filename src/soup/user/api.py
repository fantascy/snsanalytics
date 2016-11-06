import urllib, urllib2
from sets import ImmutableSet, Set

from google.appengine.ext import db
import json
import logging
import context
from sns.core import core as db_core
from sns.url.models import UrlKeyName
from sns.serverutils import memcache,deferred
from common.utils.facebook import GraphAPI
from common.utils.string import split_strip
from soup.commonutils.cookie import getFbCookie
from soup.api import consts as api_const
from soup.api.base import BaseProcessor
from soup.api import errors as api_error
from models import BaseChannel, Friendship , FChannel, SoupUser, UserArticleRating, UserArticleFollowing,UserComment


def current_user(login_required=True):
    user = None
    cookie = context.get_context().request().COOKIES
    fbCookie = getFbCookie(cookie)
    if fbCookie is not None:
        try:
            access_token = fbCookie['access_token']
            fbKey = FChannel.keyName(fbCookie['uid'])
            user = memcache.get(fbKey)
            if user is None:
                channel = FChannel.get_by_key_name(fbKey)
                if channel is None or channel.email is None:
                    profile = json.load(urllib2.urlopen("https://graph.facebook.com/me?%s" % urllib.urlencode(dict(access_token=access_token,fields='id,name,picture,link,email,location'))))
                    if profile.has_key('location'):
                        location = profile['location']['name']
                    else:
                        location = None
                    graph = GraphAPI(access_token)
                    friends = graph.get_connections('me','friends')['data']
                    allFriends = Set()
                    for friend in friends:
                        allFriends.add((friend['id'],friend['name']))
                    channel = FChannel(key_name=FChannel.keyName(profile['id']),uid=int(profile['id']),avatarUrl=profile['picture'],oauthAccessToken=access_token,
                                       name=profile['name'],nameLower=profile['name'].lower(),url=profile['link'],email=profile['email'],location=location,allFriends=str(allFriends))
                    channel.put()
                users = SoupUser.all().filter('fChannel', channel).fetch(limit=1)
                if len(users) > 0:
                    user = users[0]
                else:
                    params = {}
                    params['fChannel'] = channel
                    params['name'] = channel.name
                    params['nameLower'] = channel.nameLower
                    params['avatarUrl'] = channel.avatarUrl
                    params['email'] = channel.email
                    locationInfo = split_strip(channel.location,',')
                    if len(locationInfo)==2 :
                        params['city'] = locationInfo[0] 
                        params['country'] = locationInfo[1] 
                    user = SoupUserProcessor().create(params)
                    fid = int(channel.keyNameStrip())
                    commentCount = UserComment.all().filter('fid', fid).count()
                    if commentCount > 0:
                        counter = user.getCounter()
                        counter.commentCount = commentCount
                        counter.put()
                memcache.set(fbKey, user, time=3600)
                if channel.soupFriends is None:
                    deferred.defer(initial_soup_friends,channel.keyNameStrip(),user.uid)
        except:
            logging.exception("Unexpected error when handling soup facebook cookie!")
    else:
        if login_required :
            raise api_error.ApiError(api_error.API_ERROR_USER_NOT_LOGGED_IN)
    return user     

def initial_soup_friends(fid,uid):
    try:
        fChannel = FChannel.get_by_key_name(FChannel.keyName(fid))
        name = fChannel.name
        allFriends = fChannel.getFriends()
        soupFriends = fChannel.getSoupFriends()
        for friend in allFriends:
            sid = friend[0]
            sChannel = FChannel.get_by_key_name(FChannel.keyName(sid))
            if sChannel is not None:
                sUser = SoupUser.all().filter('fChannel', sChannel).fetch(limit=1)
                if len(sUser) == 0:
                    continue
                suid = sUser[0].key().id()
                soupFriends.add(friend)
                db.put(Friendship(key_name=Friendship.keyName(str(uid)+':'+str(suid)),userId=uid,friendId=suid))
                if sChannel.soupFriends is not None:
                    sFriends = sChannel.getSoupFriends()
                    sFriends.add((fid,name))
                    sChannel.soupFriends = str(sFriends)
                    sChannel.put()
                    db.put(Friendship(key_name=Friendship.keyName(str(suid)+':'+str(uid)),userId=suid,friendId=uid))
                logging.info('Add soup friend %s for %s'%(sid,fid))
        fChannel.soupFriends = str(soupFriends)
        fChannel.put()
        memcache.delete(FChannel.keyName(fid))        
    except Exception:
        logging.exception('Unexpected error when initial soup friends')
            
       

def clear_current_user():
    cookie = context.get_context().request().COOKIES
    fbCookie = getFbCookie(cookie)
    if fbCookie is not None:
        fbKey = FChannel.keyName(fbCookie['uid'])
        user = memcache.get(fbKey)
        if user is not None:
            memcache.delete(fbKey)

class ChannelProcessor(BaseProcessor):
    def getModel(self):
        return BaseChannel

    @classmethod
    def supportedOperations(cls):
        """"
        Supported public API operations of this processor
        """
        return ImmutableSet([api_const.SOUP_API_O_RATE, 
                             api_const.SOUP_API_O_TOGGLE_ARTICLE_FOLLOW,
                             api_const.SOUP_API_O_IS_ARTICLE_FOLLOWED,
                             ]).union(BaseProcessor.supportedOperations())

    def rate(self, params):
        """
        newscore - 0-5, 0 and none are equivalent
        If new score is none, it is a removal of rating.  
        """
        return db.run_in_transaction(self._trans_rate, params)

    def _trans_rate(self, params):
        newScore = int(params.get('newscore', 0))
        userRating = self.get_article_rating(params)
        if newScore==0 :
            if userRating is not None :
                db.delete(userRating)
            return None
        else :
            if userRating is None :
                userRating = self._create_article_rating(params)
            userRating.rating = newScore
            db.put(userRating)
            return userRating 

    def _create_article_rating(self, params):
        keyName = db_core.normalize_2_key(params).name()
        return UserArticleRating(key_name=keyName, parent=current_user(login_required=True), urlKeyName=keyName)
        
    def get_article_rating(self, params):
        loginUser = current_user(login_required=False)
        if loginUser is None :
            return None
        articleUrl = UrlKeyName.urlFromKey(db_core.normalize_2_key(params))
        return UserArticleRating.get_by_key_name(UrlKeyName.keyName(articleUrl), loginUser)        
        
    def get_or_insert_article_rating(self, params):
        loginUser = current_user(login_required=True)
        if loginUser is None :
            return None
        articleUrl = UrlKeyName.urlFromKey(db_core.normalize_2_key(params))
        keyName = UrlKeyName.keyName(articleUrl)
        return UserArticleRating.get_or_insert(key_name=keyName, parent=loginUser, urlKeyName=keyName)        

    def toggle_article_follow(self, params):
        """
        Toggle article follow status for user. Follow the article if not. Otherwise, unfollow the article and remove record from db.
        """
        return db.run_in_transaction(self._trans_toggle_article_follow, params)

    def _trans_toggle_article_follow(self, params):
        loginUser = current_user(login_required=False)
        if loginUser is None :
            return {'toggled':False}
        articleUrl = UrlKeyName.urlFromKey(db_core.normalize_2_key(params))
        followed_article = UserArticleFollowing.get_by_key_name(UrlKeyName.keyName(articleUrl), loginUser)
        if followed_article is None :
            keyName = UrlKeyName.keyName(articleUrl)
            db.put(UserArticleFollowing(key_name=keyName, parent=loginUser, urlKeyName=keyName))
            return {'followed':True, 'toggled':True}
        else :
            db.delete(followed_article)        
            return {'followed':False, 'toggled':True}

    def is_article_followed(self, params):
        loginUser = current_user(login_required=False)
        if loginUser is None :
            return False
        articleUrl = UrlKeyName.urlFromKey(db_core.normalize_2_key(params))
        followed_article = UserArticleFollowing.get_by_key_name(UrlKeyName.keyName(articleUrl), loginUser)
        if followed_article is None :
            return False
        else :
            return True
        

class SoupUserProcessor(BaseProcessor):
    def getModel(self):
        return SoupUser


def getArticleRatingQuery(keyname):
    query = UserArticleRating.all().filter("urlKeyName = ", keyname).order('-modifiedTime')
    return query

