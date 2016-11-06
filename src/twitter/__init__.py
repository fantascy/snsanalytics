import os
import datetime
from hashlib import sha1
from hmac import new as hmac
from random import getrandbits
from time import time
from urllib import urlencode, quote as urlquote
from uuid import uuid4
import mimetypes
import re
import urllib2
import base64
import logging

import context
from common.utils import url as url_util


class TwitterOAuthSettings():
    def __init__(self, 
                consumerKey=None,
                consumerSecret=None,
                requestTokenUrl='https://api.twitter.com/oauth/request_token',
                accessTokenUrl='https://api.twitter.com/oauth/access_token',
                userAuthUrl='https://api.twitter.com/oauth/authorize',
                defaultApiPrefix='https://api.twitter.com/1.1', 
                defaultApiSuffix='.json',
                mediaApiPrefix='https://upload.twitter.com/1.1',
                 ):
        self.consumerKey = consumerKey
        self.consumerSecret = consumerSecret
        self.requestTokenUrl = requestTokenUrl
        self.accessTokenUrl = accessTokenUrl
        self.userAuthUrl = userAuthUrl
        self.defaultApiPrefix = defaultApiPrefix
        self.defaultApiSuffix = defaultApiSuffix
        self.mediaApiPrefix = mediaApiPrefix


def get_app_oauth_settings():
    try:
        oauth_app_settings = context.get_context().oauth_app_settings()
        return TwitterOAuthSettings(
           consumerKey = oauth_app_settings['consumer_key'],
           consumerSecret = oauth_app_settings['consumer_secret'],
           )
    except:
        return None


def get_service_key():
    oauthSettings = get_app_oauth_settings()
    return "%s&" % encode(oauthSettings.consumerSecret)


def create_uuid():
    return 'id-%s' % uuid4()


def encode(text):
    return urlquote(str(text), '')


class TwitterApiClient(object):
    #Set timeout to 10 seconds, google app engine use 5 seconds by default
    URLFETCH_DEADLINE = 10

    def __init__(self, access_token=None, oauth_callback=None, **request_params):
        self.service_info = get_app_oauth_settings()
        self.service_key = None
        self.request_params = request_params
        self.oauth_callback = oauth_callback
        self.access_token = access_token

    def get(self, uri, http_method='GET', expected_status=(200,), **extra_params):
        if not (uri.startswith('http://') or uri.startswith('https://')):
            uri = '%s%s%s' % (self.service_info.defaultApiPrefix, uri, self.service_info.defaultApiSuffix)
        url = self.get_signed_url(uri, self.access_token, http_method, **extra_params)
        logging.debug("Twitter API: %s" % url)
        return url_util.urlfetch(url, deadline=self.URLFETCH_DEADLINE)

    def post(self, uri, http_method='POST', expected_status=(200,), **extra_params):
        if not (uri.startswith('http://') or uri.startswith('https://')):
            if uri == '/media/upload':
                api_prefix = self.service_info.mediaApiPrefix
            else:
                api_prefix = self.service_info.defaultApiPrefix
        url = '%s%s%s' % (api_prefix, uri, self.service_info.defaultApiSuffix)
        logging.debug("Twitter API: %s" % url)
        signedParams = self.get_signed_body_params(url, self.access_token, http_method, **extra_params)
        headers = {'Authorization': self.getOauthHeader(signedParams)}
        if extra_params.has_key('image') :
            contentType, contentBody = self._encode_multipart_formdata(fields=extra_params, mediaField='image')
            headers['Content-Type'] = contentType
            headers['Content-Length'] = len(contentBody)
            req = urllib2.Request(url, contentBody, headers)
            return urllib2.urlopen(req)
        else:
            payload = urlencode(self.getUrlParams(signedParams))
            headers['Content-Type'] = "application/x-www-form-urlencoded"
            headers['Content-Length'] = len(payload)
            return url_util.urlfetch(url=url, headers=headers, payload=payload, deadline=self.URLFETCH_DEADLINE)

    def get_data_from_signed_url(self, url, token, meth='GET', **extra_params):
        url=self.get_signed_url(url, token, meth, **extra_params)
        try:
            content = url_util.urlfetch(url, deadline=self.URLFETCH_DEADLINE).content
        except Exception,ex:
            raise(ex)
        else:
            return content

    def get_signed_url(self, url, token, meth='GET', **extra_params):
        return '%s?%s'%(url, self.get_signed_body(url, token, meth, **extra_params))
    
    def get_signed_body(self, url, token, meth='GET', **extra_params):
        return urlencode(self.get_signed_body_params(url, token, meth, **extra_params))
    
    def get_signed_body_params(self, url, token, meth='GET', **extra_params):
        service_info = self.service_info
        kwargs = {
            'oauth_consumer_key': service_info.consumerKey,
            'oauth_signature_method': 'HMAC-SHA1',
            'oauth_version': '1.0',
            'oauth_timestamp': int(time()),
            'oauth_nonce': getrandbits(64),
            }
        if not extra_params.has_key('image') :
            kwargs.update(extra_params)
#        for (k,v) in extra_params.items():
#        This extra encode() is not needed since the twitter/api.py does the encoding for extra_params already.
#            kwargs[k]=unicode(v).encode("utf8")
        if self.service_key is None:
            self.service_key = get_service_key()

        if token is not None:
            kwargs['oauth_token'] = token.oauth_token
            key = self.service_key + encode(token.oauth_token_secret)
        else:
            key = self.service_key
        message = '&'.join(map(encode, [
            meth.upper(), url, '&'.join(
                '%s=%s' % (encode(k), encode(kwargs[k])) for k in sorted(kwargs)
                )
            ]))
        kwargs['oauth_signature'] = hmac(
            key, message, sha1
            ).digest().encode('base64')[:-1]
        return kwargs
    
    def getOauthHeader(self, signedParams):
        oauthHeader = 'OAuth oauth_consumer_key="%s", oauth_nonce="%s", oauth_signature="%s", oauth_signature_method="HMAC-SHA1", oauth_timestamp="%s", oauth_token="%s", oauth_version="1.0"'
        return oauthHeader % (
                            signedParams['oauth_consumer_key'],
                            signedParams['oauth_nonce'],
                            encode(signedParams['oauth_signature']),
                            signedParams['oauth_timestamp'],
                            signedParams['oauth_token'],
                              )
    
    def getUrlParams(self, signedParams):
        urlParams = {}
        for key in signedParams.keys():
            if not key.startswith('oauth'):
                urlParams[key] = signedParams[key]
        return urlParams
    
    def _encode_multipart_formdata(self, fields=None, mediaField='image'):
        BOUNDARY = '-------tHISiStheMulTIFoRMbOUNDaRY'
        CRLF = '\r\n'
        L = []
        filedata = None
        media = fields.get(mediaField, '')
        
        if media:
            filedata = self._get_filedata(media)
            del fields[mediaField]
        
        if fields:
            for (key, value) in fields.items():
                L.append('--' + BOUNDARY)
                L.append('Content-Disposition: form-data; name="%s"' % str(key))
                L.append('')
                L.append(str(value))
                
        if filedata:     
            for (filename, value) in [(media, filedata)]:
                L.append('--' + BOUNDARY)
                L.append('Content-Disposition: form-data; name="%s"; filename="%s"' % (mediaField, str(filename)))
                L.append('Content-Type: %s' % self._get_content_type(media))
                L.append('Content-Transfer-Encoding: Base64')
                L.append('')
                L.append(value)
        
        L.append('--' + BOUNDARY + '--')
        L.append('')
        body = CRLF.join(L)
        content_type = 'multipart/form-data; boundary=%s' % BOUNDARY
        
        return content_type, body
    
    def _get_content_type(self, media):
        return mimetypes.guess_type(media)[0] or 'application/octet-stream'
    
    def _get_filedata(self, media):
        # Check self.image is an url, file path, or nothing.
        prog = re.compile('((https?|ftp|gopher|telnet|file|notes|ms-help):((//)|(\\\\))+[\w\d:#@%/;$()~_?\+-=\\\.&]*)')
        
        if prog.match(media):
            return base64.b64encode(url_util.fetch_url(media))
        elif os.path.exists(media):
            return base64.b64encode(open(media, 'rb').read())
        else:
            return None
    
