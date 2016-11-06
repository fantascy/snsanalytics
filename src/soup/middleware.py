from exceptions import Exception

from google.appengine.api import users
from google.appengine.runtime.apiproxy_errors import CapabilityDisabledError 
from django.http import HttpResponseRedirect,HttpResponse
import logging
import context
from sns.serverutils import memcache
from soup.commonutils.cookie import get_ip_mem_key
from soup.api import errors as api_error
from soup import consts as soup_const


def process_request(request):
    if not context.get_context().require_google_login() or is_google_bot(request):
        return
    user = users.get_current_user()
    if request.get_full_path()!= '/brew/login/':
        if user is None :
            return HttpResponse(status=404)
        if not users.is_current_user_admin() :
            raise Exception
    
        
def process_exception(request, exception):
    logging.exception('Unexpected soup error!')
    if type(exception) == api_error.ApiError and exception.error_code==api_error.API_ERROR_USER_NOT_LOGGED_IN:
        error = soup_const.NOTICE_USER_NOT_LOGIN
    elif type(exception) == CapabilityDisabledError:
        error = soup_const.NOTICE_GAE_MAINTENANCE
    else:
        error = soup_const.NOTICE_UNKNOWN_ERROR
    memcache.set(get_ip_mem_key('notice'), error)
    return HttpResponseRedirect('/')
        

def is_google_bot(request):
    agent = context.get_context().http_user_agent()
    if agent.lower().find('google') != -1 or agent.lower().find('facebook') != -1 :
        return True
    else:
        return False