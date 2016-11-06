import context
from deploysoup import FACEBOOK_OAUTH_MAP 
from urllib import splitvalue
from sns.serverutils import memcache
from google.appengine.ext import db

def fbCookieName():
    return 'fbs_'+ FACEBOOK_OAUTH_MAP[context.get_context().application_id()]['id']

def twCookieName():
    return 'twitter_anywhere_identity'

def getFbCookie(cookie):
    cookie_key =  fbCookieName()
    if cookie.has_key(cookie_key):  
        cookie_str = cookie[cookie_key]
        params = {}
        values=cookie_str.split('&')
        for value in values:
            key,item=splitvalue(value)
            params[key] = item
        return params
    else:
        return None
    
def getTwCookie(cookie):
    cookie_key =  twCookieName()
    if cookie.has_key(cookie_key): 
        cookie_str = cookie[cookie_key]
        params = {}
        values=cookie_str.split(':')
        params['uid'] = values[0]
        params['access_token'] = values[1]
        return params
    else:
        return None
    
def get_ip_mem_key(type):
    ip = context.get_context().request().META.get("REMOTE_ADDR","")
    return ip + ':' + type

def get_by_mem_id(id):
    model = memcache.get(id)
    if model is None:
        model = db.get(id)
        memcache.set(id, model, time=3600)
    return model
