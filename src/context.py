"""
Global context info goes here.
"""

import os
import threading, thread
import random
from exceptions import Exception
import datetime
import logging

import conf
import deployglobal
import deploysns
import deploycake
import deploymsb
import deployfe
import deployappspot
from common import consts as common_const
from client import conf as client_conf


THREAD_CONTEXT_MAP = {}

_context_cv = threading.Condition()
_is_client = None

def is_client():
    return not os.environ.has_key('SERVER_SOFTWARE')

if not is_client():
    from google.appengine.api import app_identity
    from google.appengine.api import backends

def is_dev_mode():
    return os.environ.has_key('SERVER_SOFTWARE') and os.environ['SERVER_SOFTWARE'].startswith('Dev')

def is_trove_enabled():
    try:
        expire_time_utc = datetime.datetime.strptime(conf.TROVE_EXPIRE_TIME_UTC, common_const.COMMON_DATETIME_FORMAT)
        utcnow = datetime.datetime.utcnow()
        return utcnow < expire_time_utc
    except:
        return False

def is_frontend():
    return not is_backend()

def is_backend():
    return backends.get_backend() is not None or is_dev_mode() and conf.MARK_IS_BACKEND_ON_DEV
    
def is_backend_instance_0():
    return is_backend() and backends.get_instance() == 0 or is_dev_mode() and conf.MARK_IS_BACKEND_ON_DEV

def is_prod_instance_0():
    return backends.get_backend() == 'prod' and backends.get_instance() == 0 

def is_b4_instance_0():
    return backends.get_backend() == 'b4' and backends.get_instance() == 0 

class ContextNotFoundError(Exception):
    pass

def log_thread_info():
    count = threading.active_count()
    current = threading.current_thread()
    ctx = THREAD_CONTEXT_MAP.get(current.ident, None)
    cid = 0 if ctx is None else ctx.cid()
    logging.debug("Thread info: count=%d, current='%s', ident='%s', context=%d" % (count, current.name, current.ident, cid))
                  
def set_context(request):
    with _context_cv:
        ident = thread.get_ident()
        THREAD_CONTEXT_MAP[ident] = Context(request=request)
        log_thread_info()

def set_deferred_context(deploy):
    with _context_cv:
        ident = thread.get_ident()
        ctx = Context(loginRequired=False, deploy=deploy)
        THREAD_CONTEXT_MAP[ident] = ctx
        log_thread_info()

def get_context(raiseErrorIfNotFound=True, deploy=deploysns):
    ident = thread.get_ident()
    ctx = THREAD_CONTEXT_MAP.get(ident, None)
    if ctx is None:
        if raiseErrorIfNotFound and not is_client():
            raise ContextNotFoundError()
        else:
            logging.info("No context for thread %d, create and set to %s!" % (ident, deploy.APP))
            set_deferred_context(deploy=deploy)
            ctx = THREAD_CONTEXT_MAP.get(ident, None)
    return ctx

def get_or_create_context(deploy=deploysns):
    return get_context(raiseErrorIfNotFound=False, deploy=deploy)

class Context():
    def __init__(self, request=None, deploy=None, loginRequired=True):
        self._cid = random.randint(1, 1000000)
        self._request = request
        self._loginRequired = loginRequired
        self._deploy = deploy
        if self._deploy is None :
            self.set_deploy()
        self._browser = None
        self._device = None
        self.set_visitor_properties()
    
    def cid(self):
        return self._cid

    def is_debug(self):
        return conf.SETTING_MODE==conf.SETTING_MODE_DEBUG
     
    def application_id(self):
        if is_client():
            return client_conf.APPLICATION_ID
        elif is_dev_mode():
            return 'localhost'
        else:
            return app_identity.get_application_id()
    
    def is_primary_app(self):
        return self.application_id() == 'ripple1app'
    
    def debug(self):
        return conf.SETTING_MODE==conf.SETTING_MODE_DEBUG
        
    def request(self):
        return self._request
        
    def set_visitor_properties(self):
        agent = self.http_user_agent()
        if agent is None :
            return
        for browser in common_const.BROWSERS_KNOWN:
            if agent.find(browser)!=-1 :
                self._browser = browser
                break
        for device in common_const.DEVICES_KNOWN:
            if agent.find(device)!=-1 :
                self._device = device
                break
    
    def browser(self):
        return self._browser
    
    def device(self):
        return self._device 
    
    def is_ios(self):
        return self._device is not None and self._device in common_const.DEVICES_IOS
    
    def is_iphone(self):
        return self._device == common_const.DEVICE_IPHONE
        
    def is_phone(self):
        return self._device in common_const.DEVICES_PHONE
        
    def is_tablet(self):
        return self._device in common_const.DEVICES_TABLET
        
    def cookie(self, cookieName):
        if self._request:
            return self._request.COOKIES.get(cookieName, None)
        else:
            return None
            
    def http_user_agent(self):
        if self._request:
            return self._request.META.get("HTTP_USER_AGENT", "").decode('utf-8', 'ignore')
        else:
            return None
    
    def http_user_referrer(self):
        if self._request:
            return self._request.META.get("HTTP_REFERER", "").decode('utf-8','ignore')
        else:
            return None
    
    def http_user_session(self):
        return self.cookie(common_const.COOKIE_USER_SESSION)
            
    def request_full_path(self):
        if self._request:
            return self._request.get_full_path().encode('utf-8')
        else:
            return None
    
    def deploy(self):
        return self._deploy
        
    def set_deploy(self, deploy=None):
        if deploy is None and self._request:
            if self.is_fe():
                self._deploy = deployfe
            else:
                from common.utils.url import root_domain
                domain = root_domain(self._request.META['HTTP_HOST'])
                if deployglobal.APP_DEPLOY_MAP.has_key(domain):
                    self._deploy = deployglobal.APP_DEPLOY_MAP[domain]
                else:
                    self._deploy = deployappspot
        else :
            self._deploy = deploy
    
    def is_fe(self):
        if is_dev_mode():
            from common.utils.url import full_domain
            return deployfe.DOMAIN_MAP['localhost'].split(':')[0] == full_domain(self._request.META['HTTP_HOST'])
        else:
            return deployfe.DOMAIN_MAP.has_key(self.application_id())
        
    def app(self):
        return self._deploy.APP 
        
    def app_path(self):
        return self._deploy.APP_PATH 
        
    def app_name(self):
        return self._deploy.APP_NAME_MAP[self.application_id()]
    
    def amazon_bucket(self):
        return deploysns.AMAZON_BUCKET_MAP[self.application_id()]
    
    def login_required(self):
        return self._loginRequired
    
    def set_login_required(self, login_required):
        self._loginRequired = login_required
    
    def has_login(self):
        from google.appengine.api import users
        if users.get_current_user() is None:
            return False
        else:
            return True
    
    def require_google_login(self):
        if conf.REQUIRE_GOOGLE_LOGIN :
            return True
        return self._deploy.REQUIRE_GOOGLE_LOGIN_MAP[self.application_id()]
        
    def cake_toolbar_enabled(self):
        if conf.CAKE_TOOLBAR_ENABLED :
            return True
        return deploycake.TOOLBAR_ENABLED_MAP[self.application_id()]
        
    def ads_on(self):
        return self._deploy.ADS_ON[self.application_id()]
        
    def google_site_verification(self):
        return self._deploy.GOOGLE_SITE_VERIFICATION_MAP[self.application_id()]
    
    def google_cse_key(self):
        return self._deploy.GOOGLE_CUSTOM_SEARCH_KEY[self.application_id()]
    
    def fb_app_id(self):
        return self._deploy.FACEBOOK_OAUTH_MAP[self.application_id()]['id']
    
    def twaw_app_key(self):
        return self._deploy.TWITTERANYWHERE_OAUTH_MAP[self.application_id()]['consumer_key']
    
    def klout_key(self):
        return self._deploy.KLOUT_KEY
    
    def get_user(self):
        from sns.core.core import get_user as sns_get_user
        return sns_get_user()
    
    def skip_real_post(self):
        return is_dev_mode() and conf.DEBUG_SKIP_REAL_POST
     
    def skip_timeout(self):
        return is_dev_mode() and conf.DEBUG_SKIP_TIMEOUT
     
    def treat_localhost_ip_as_cn(self):
        return conf.LOCALHOST_IP_IS_CN
     
    def manual_approval(self):
        if self.app() == "msb":
            return True
        else:
            return not is_dev_mode() and not self.is_primary_app()
    
    def short_domain(self):
        return self._deploy.SHORT_DOMAIN_MAP[self.application_id()]
    
    def feedbuilder_domain(self):
        return deploymsb.DOMAIN_MAP.get(self.application_id(), None)
    
    def long_domain(self, app_deploy=None):
        if app_deploy is None:
            app_deploy = self._deploy
        return app_deploy.DOMAIN_MAP[self.application_id()]
    
    def short_url_length(self):
        return common_const.TWITTER_SHORT_URL_LENGTH
    
    def count_admin_user_clicks(self):
        return conf.COUNT_ADMIN_USER_CLICKS
    
    def oauth_app_settings(self):
        return self._deploy.TWITTER_OAUTH_MAP[self.application_id()]
        
    def ga_tracking_code(self):
        return self._deploy.GA_TRACKING_CODE_MAP[self.application_id()]
    
    def surl_ga_tracking_code(self):
        return self._deploy.SURL_GA_TRACKING_CODE_MAP[self.application_id()]
    
    def quantcast_tracking_code(self):
        return self._deploy.QUANTCAST_TRACKING_CODE
    
    def cmp_on(self):
        return self._deploy.CMP_MAP.get(self.application_id(), False)


if __name__ == '__main__':
    pass
