import logging
from django.http import HttpResponseRedirect

import deployglobal
import context
from entry import page_not_found
from urls import sns_url, msb_url, soup_url, cake_url, fe_url
from sns import middleware as sns_middleware
from soup import middleware as soup_middleware
from cake import middleware as cake_middleware
from msb import middleware as msb_middleware
from fe import middleware as fe_middleware

MIDDLEWARE_MAP = {
    "sns" : sns_middleware,
    "soup" : soup_middleware,
    "cake" : cake_middleware,
    "msb" : msb_middleware,
    "fe" : fe_middleware,
    "appspot" : sns_middleware,
}

URLPATTERN_MAP = {
    "sns" : sns_url,
    "soup" : soup_url,
    "cake" : cake_url,
    "msb" : msb_url,
    "fe": fe_url,  
    "appspot" : sns_url,            
                  }

def middlewareImpl():
    return MIDDLEWARE_MAP[context.get_context().app()]

        
class RequestHandler(object):
    def process_request(self, request):
        try:
            context.set_context(request)
            request_full_path = context.get_context().request_full_path()
            if str(request_full_path).find('/redirecturl') > 0 and str(request_full_path).find('/redirecturl') == len(request_full_path) - 12:
                ret_url = '/#'+str(request_full_path)[0:-12]
                return HttpResponseRedirect(ret_url)
            if request.get_host() in deployglobal.REDIRECT_MAP.keys():
                url = 'http://' + deployglobal.REDIRECT_MAP[request.get_host()] + request_full_path
                return HttpResponseRedirect(url)
            if isPathFound(request,context.get_context().app()):
                return middlewareImpl().process_request(request)
            else:
                return page_not_found(request) 
        except Exception, e:
            logging.exception("Request exception:")
            return ExceptionHandler().process_exception(request,e)
            
        
class ExceptionHandler(object):
    def process_exception(self, request, exception):
        return middlewareImpl().process_exception(request, exception)
    

def isPathFound(request,app):
    def matchPattern(path,patterns):
        match = False
        for pattern in patterns:
            if pattern.regex.search(path):
                match = True
                break
        return match
    
    path = request.path.lstrip('/')
    if app=='soup' or app=='cake':
        url_patterns = URLPATTERN_MAP['sns'] + URLPATTERN_MAP['msb'] + URLPATTERN_MAP['fe']
        return not matchPattern(path, url_patterns)
    else:
        return True
