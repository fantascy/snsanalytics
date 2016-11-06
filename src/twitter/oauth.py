import datetime
import logging

from google.appengine.api.urlfetch import fetch as urlfetch
from google.appengine.ext import db
from twitter import TwitterApiClient

import context
from sns.core.base import  DatedBaseModel


CLEANUP_BATCH_SIZE = 100
EXPIRATION_WINDOW = datetime.timedelta(seconds=3600)


class TwitterOAuthRequestToken(DatedBaseModel):
    oauth_token = db.StringProperty()
    oauth_token_secret = db.StringProperty()


class TwitterOAuthAccessToken(DatedBaseModel):
    handle = db.StringProperty()
    oauth_token = db.StringProperty(indexed=False)
    oauth_token_secret = db.StringProperty(indexed=False)
    
    @classmethod
    def get_or_insert_by_chid(cls, chid, **token_info):
        return cls.get_or_insert("%s:%s" % (context.get_context().app(), chid), **token_info)
        
    @classmethod
    def get_by_chid(cls, chid, **token_info):
        return cls.get_by_key_name("%s:%s" % (context.get_context().app(), chid))
        
    def chid(self):
        return int(self.key().name().split(':')[-1]) if self.is_new_format() else None
    
    def is_new_format(self):
        key_split = self.key().name().split(':')
        if len(key_split) != 2:
            return False
        try:
            if int(key_split[1]):
                return True
        except:
            return False

    def user_str(self):
        try:
            return "%s@%s" % (self.key().name(), self.handle)
        except:
            return "%s" % self.handle
        
    def __str__(self):
        return "@%s(%s) oauth_token:%s, oauth_token_secret: %s"%(self.user_str(), self.oauth_token, self.oauth_token_secret)


class TwitterOAuthClient(TwitterApiClient):
    __public__ = ('callback', 'cleanup', 'login', 'logout')

    def get_request_token(self):
        """
        create a get token request, return the http request url
        """
        url = self.service_info.requestTokenUrl
        http_method = 'POST'
        payload=self.get_signed_body(url, self.access_token, http_method, **self.request_params) 
        resp = urlfetch(url=url, payload=payload, method=http_method, deadline=self.URLFETCH_DEADLINE)
        token_info = resp.content
        logging.info("Twitter OAuth request token info: %s" % token_info)
        token = TwitterOAuthRequestToken(
            **dict(token.split('=') for token in token_info.split('&'))
            )
        token.put()
        if self.oauth_callback:
            oauth_callback = {'oauth_callback': self.oauth_callback}
        else:
            oauth_callback = {}
        return self.get_signed_url(
            self.service_info.userAuthUrl, token, **oauth_callback
            )

    def callback(self, oauth_token, oauth_verifier):
        request_token = TwitterOAuthRequestToken.all().filter('oauth_token =', oauth_token).fetch(1)[0]
        token_info = self.get_data_from_signed_url(self.service_info.accessTokenUrl, request_token, 'GET', oauth_verifier=oauth_verifier)
        token_dict = dict(token.split('=') for token in token_info.split('&'))
        self.access_token = TwitterOAuthAccessToken.get_or_insert_by_chid(token_dict['user_id']) 
        self.access_token.oauth_token = token_dict['oauth_token']
        self.access_token.oauth_token_secret = token_dict['oauth_token_secret']
        self.access_token.handle = token_dict['screen_name']
        self.access_token.put()
        return self.access_token 
       
    def cleanup(self):
        query = TwitterOAuthRequestToken.all().filter(
            'createdTime <', datetime.datetime.utcnow() - EXPIRATION_WINDOW
            )
        count = query.count(CLEANUP_BATCH_SIZE)
        db.delete(query.fetch(CLEANUP_BATCH_SIZE))
        return "Cleaned %i entries" % count

