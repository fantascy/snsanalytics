import datetime
import logging
import json
import urllib
from StringIO import StringIO

from twython import Twython

import context
from common.utils import timezone as ctz_util
from common.utils import image as image_util
from common.utils import twitter as twitter_util
from common.utils.memcache import memcache
from twitter import consts as twitter_const
from twitter import errors as twitter_error
from twitter import get_app_oauth_settings, TwitterApiClient


def get_twython_client_args():
    return {
        'headers': {
            'User-Agent': twitter_const.USER_AGENT
        },
        'allow_redirects': False
    }


class TwitterRateLimit(object):
    MEM_KEY_APP_LIMIT_PREFIX = "twitter_rate_limit"
    NEW_ACCOUNT_FRIENDS_LIMIT = 1800
    GET_LIMIT_CEILING = 180
    POST_LIMIT_CEILING = 15
    GET_LIMIT_FLOOR = 60
    POST_LIMIT_FLOOR = 5

    def __init__(self, oauth_token, data):
        self.oauth_token = oauth_token
        try:
            self._data = data
            data_post = data['resources']['statuses']['/statuses/mentions_timeline']
            data_get = data['resources']['search']['/search/tweets']
            self._expire = ctz_util.timestamp_2_utc(data_post['reset'])
            self._post_limit = data_post['remaining']
            self._get_limit = data_get['remaining']
        except:
            logging.exception("Error creating %s object for %s and %s." % (self.__class__.__name__, oauth_token.user_str(), data))
            self._data = None
            self._expire = None
            self._post_limit = 0
            self._get_limit = 0

#     def __del__(self):
#         try:
#             mem_key = self.mem_key()
#             if self.expired():
#                 memcache.delete(mem_key)
#             else:
#                 memcache.set(mem_key, self, time=900)
#         except:
#             logging.exception("Unexpected exception!")
            
    @classmethod
    def get_mem_key(cls, oauth_token):
        return "%s:%s" % (cls.MEM_KEY_APP_LIMIT_PREFIX, oauth_token.user_str())

    def mem_key(self):
        return self.__class__.get_mem_key(self.oauth_token)

    def expired(self):
        return not self._expire or self._expire <= datetime.datetime.utcnow()
    
    def consume_get_limit(self):
        if not self.expired() and self._get_limit > self.GET_LIMIT_FLOOR:
            self._get_limit -= 1
            return True
        return False 

    def consume_post_limit(self):
        if not self.expired() and self._post_limit > self.POST_LIMIT_FLOOR:
            self._post_limit -= 1
            return True
        return False 

    def available_get_limit(self):
        if not self.expired() and self._get_limit > self.GET_LIMIT_FLOOR:
            return self._get_limit - self.GET_LIMIT_FLOOR
        return 0

    def available_post_limit(self):
        if not self.expired() and self._post_limit > self.POST_LIMIT_FLOOR:
            return self._post_limit - self.POST_LIMIT_FLOOR
        return 0

    def mark_over_get_limit(self):
        self._get_limit = 0

    def mark_over_post_limit(self):
        self._post_limit = 0


class TwitterCall(object):
    NEW_ACCOUNT_FRIENDS_LIMIT = TwitterRateLimit.NEW_ACCOUNT_FRIENDS_LIMIT
    def __init__(self, domain, uri="", agent=None, oauth_access_token=None):
        self.domain = domain
        self.uri = uri
        self.agent = agent
        self.oauth_access_token=oauth_access_token
        self._limit_obj = None

    def limit_obj(self):
        if self._limit_obj:
            return self._limit_obj 
        mem_key = TwitterRateLimit.get_mem_key(self.oauth_access_token)
        limit_obj = memcache.get(mem_key)
        if limit_obj and limit_obj.expired():
            memcache.delete(mem_key)
            limit_obj = None
        if not limit_obj:
            rate_limit = self.application.rate_limit_status(resources="search,statuses")
            limit_obj = TwitterRateLimit(oauth_token=self.oauth_access_token, data=rate_limit)
        if limit_obj:
            memcache.set(mem_key, self._limit_obj, time=900)
        self._limit_obj = limit_obj
        return self._limit_obj
        
    def __getattr__(self, k):
        try:
            return object.__getattr__(self, k)
        except AttributeError:
            return TwitterCall(self.domain, self.uri + "/" + k, self.agent, self.oauth_access_token)

    def consume_get_limit(self):
        if self._is_limit_check():
            return True
        limit_obj = self.limit_obj()
        return limit_obj.consume_get_limit() if limit_obj else False
        
    def consume_post_limit(self):
        if self._is_limit_check():
            return True
        limit_obj = self.limit_obj()
        return limit_obj.consume_post_limit() if limit_obj else False
        
    def available_get_limit(self):
        if self._is_limit_check():
            return TwitterRateLimit.GET_LIMIT_CEILING
        limit_obj = self.limit_obj()
        return limit_obj.available_get_limit() if limit_obj else 0
        
    def available_post_limit(self):
        if self._is_limit_check():
            return TwitterRateLimit.POST_LIMIT_CEILING
        limit_obj = self.limit_obj()
        return limit_obj.available_post_limit() if limit_obj else 0
        
    def mark_over_get_limit(self):
        if self._is_limit_check():
            return
        limit_obj = self.limit_obj()
        if limit_obj:
            limit_obj.mark_over_get_limit()
        
    def mark_over_post_limit(self):
        if self._is_limit_check():
            return
        limit_obj = self.limit_obj()
        if limit_obj:
            limit_obj.mark_over_post_limit()
    
    def __call__(self, **kwargs):
        if self._is_limit_check():
            self.uri = '/application/rate_limit_status'
        uri = self.uri
        method = "GET"
        for action in twitter_const.POST_ACTIONS:
            if self.uri.endswith(action):
                method = "POST"
                if (self.agent):
                    kwargs["source"] = self.agent
                break
        if not self._is_limit_check():
            rate_limit = self.available_get_limit() if method == 'GET' else self.available_post_limit()
            if not rate_limit:
                twitter_error.TwitterError.raise_post_limit_exceeded(self.oauth_access_token)
        if action.find('image') == -1:
            from common.utils import url as sa_urllib
            kwargs = sa_urllib.normalize_params(kwargs)
        if uri in twitter_const.ID_IN_URI_ACTIONS:
            uri = "%s/%s" % (uri, kwargs.pop('id', None))
        if self.oauth_access_token:
            return self._access_by_oauth(uri, method, kwargs)
        else:
            twitter_error.TwitterError.raise_missing_oauth_access_token()
    
    def _access_by_oauth(self, uri, method, kwargs):
        client = TwitterApiClient(access_token=self.oauth_access_token)
        if method == "GET":
            self.consume_get_limit()
            resp = client.get(uri, **kwargs)
        else:
            self.consume_post_limit()
            resp = client.post(uri, **kwargs)
        if resp.status_code == 200:
#             return decode_json(resp.content) 
            return json.loads(resp.content)
        elif resp.status_code == 429:
            if method == 'GET':
                self.mark_over_get_limit() 
            else:
                self.mark_over_post_limit()
            logging.error("Twitter API error - over limit - %s - %s" % (self.oauth_access_token.user_str(), self.uri))
            return []
        else:
            raise twitter_error.TwitterError(resp.content, status_code=resp.status_code, oauth_access_token=self.oauth_access_token)
        
    def _is_limit_check(self):
        return self.uri and self.uri.find('rate_limit_status') != -1


class TwitterApi(TwitterCall):
    def __init__(self, domain="api.twitter.com", agent=None, oauth_access_token=None):
        TwitterCall.__init__(self, domain, "", agent, oauth_access_token)

    def screen_name(self):
        return self.oauth_access_token.identifier if self.oauth_access_token else None

    def user_id(self):
        return self.oauth_access_token.chid if self.oauth_access_token else None

    def user_str(self):
        return self.oauth_access_token.user_str() if self.oauth_access_token else None

    def get_user_id_by_handle(self, handle):
        try:
            resp = self.users.show(screen_name=handle)
            user_id = int(resp['id'])
            return user_id
        except:
            logging.warn("Failed getting user_id for handle %s!" % handle)
            return None

    def get_handle_by_user_id(self, user_id):
        try:
            resp = self.users.show(user_id=user_id)
            return resp['screen_name']
        except:
            logging.exception("Error getting handle from user id %s!" % user_id)
            return None

    def get_friends_followers_count(self):
        """get friends count"""
        userInfo = self.account.verify_credentials()
        screen_name = userInfo["screen_name"]
        friends_count = int(userInfo["friends_count"])
        followers_count = int(userInfo["followers_count"])
        logging.info("Account '%s' has %s friends and %s followers." % (screen_name, friends_count, followers_count))
        return friends_count, followers_count

    def is_following_or_requested(self, screen_name=None, user_id=None):
        """ true if account already follows target """
        if screen_name:
            resp = self.friendships.lookup(screen_name=screen_name)
        else:
            resp = self.friendship.lookup(user_id=user_id)
        return resp and resp[0]['connections'] in (twitter_const.CONNECTIONS_FOLLOWING, twitter_const.CONNECTIONS_FOLLOWING_REQUESTED)

    def get_twython_api(self):
        app_oauth_settings = get_app_oauth_settings()
        app_key = app_oauth_settings.consumerKey
        app_secret = app_oauth_settings.consumerSecret
        oauth_token = self.oauth_access_token.oauth_token
        oauth_token_secret = self.oauth_access_token.oauth_token_secret
        return Twython(app_key, app_secret, oauth_token, oauth_token_secret, client_args=get_twython_client_args())
    
    def upload_media(self, media):
        twython_api = self.get_twython_api()
        if media and not context.is_dev_mode():
            try:
                image_data = urllib.urlopen(media).read()
#                 size = image_util.size_by_data(image_data)
#                 if size < twitter_const.MINIMUM_IMAGE_SIZE:
#                     logging.info("Status update with media skipped on small image size %d. %s" % (size, media))
#                     return None
                x, y = image_util.dimension_by_data(image_data)
                if x < twitter_const.MINIMUM_IMAGE_WIDTH or y < twitter_const.MINIMUM_IMAGE_HEIGHT:
                    logging.info("Status update with media skipped on small image! %s (%d, %d). %s" % (self.user_str(), x, y, media))
                    return None
                image_data = image_util.resize_data(image_data, maxdim=2000)
                image_io = StringIO(image_data)
                resp = twython_api.upload_media(media=image_io)
                return resp.get('media_id')
            except:
                logging.exception("Status update with media failed! %s %s" % (self.user_str(), media))
        return None

    def status_update(self, status, media=None):
        media_id = self.upload_media(media)
        if media_id:
            try:
                resp = self._status_update_with_media(status, media_id, retry=1)
                logging.debug("Status update with media! %s %s %s" % (self.user_str(), status, media))
                return resp
            except:
                logging.exception("Status update with media failed! %s %s %s" % (self.user_str(), status, media))
        return self.statuses.update(status=status)


    def _status_update_with_media(self, status, media_id, retry=1):
        try:
            return self.statuses.update(status=status, media_ids=media_id)
        except Exception, ex:
            if retry and isinstance(ex, twitter_error.TwitterError) and  twitter_error.is_over_140_chars(ex):
                hacked_status = twitter_util.hack_tweet_with_media(status)
                logging.info("Status update with media retry! %s %s" % (self.user_str(), hacked_status))
                return self._status_update_with_media(hacked_status, media_id, retry=0)
            raise
        return None


__all__ = ["TwitterApi", ]

