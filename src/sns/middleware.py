import logging
import re

from google.appengine.api import users
from google.appengine.runtime.apiproxy_errors import CapabilityDisabledError
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.http import HttpResponseRedirect

import context
from common.utils import string as str_util
from sns.api import consts as api_const
from sns.api import errors as api_error
from sns.core.core import User
from sns.api.facade import iapi
from sns.view.controllerview import ControllerView

def redirect_to_user_init(request, modelUser):
    if request.path.startswith('/sns/') and request.path.endswith('.html') :
        return False
    if request.GET.get('initial','')=='true' :
        return False
    if not request.path.startswith('/usr/') :
        if str_util.strip(modelUser.name) is None or modelUser.timeZone is None:
            return True
    return False

def inDirectPath(uri):
    if uri == '/' or uri == '/?initial=true':
        return True
    else:
        direct_list = ['/graph/chartpath/','/deal/rss/','/dm/chartpath/','/usr/chartpath/','/api/','/callback/twitter/','/callback/facebook/','/email/unsub/','/favicon.ico','/robots.txt','/rss/']
        for direct in direct_list:
            if uri.startswith(direct):
                return True
        return False
    
def process_request(request):
    context.get_context().set_login_required(True)
    request_full_path = context.get_context().request_full_path()
    modelUser = User.log_user(login_required=False)
    if modelUser is not None :
        iapi(api_const.API_M_USER).init(modelUser)
        if redirect_to_user_init(request, modelUser) :
            if request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest':
                if not str(request_full_path).startswith("/sns/terms.html"):
                    return HttpResponseRedirect('/usr/initset')
            else:
                if not str(request_full_path).startswith("/sns/terms.html"):
                    return HttpResponseRedirect('/?initial=true#/usr/initset')
        else:
            full_path = request_full_path
            if full_path.endswith("?old=true"):
                return HttpResponseRedirect('/')
            referrer = context.get_context().http_user_referrer()
            if (referrer is None or referrer.find(request.META.get('HTTP_HOST')) <0 )and request.method == "GET":
                if not inDirectPath(str(full_path)):
                    p = re.compile("\w*\d\w*")
                    if p.search(request.path) == None:
                        return HttpResponseRedirect('/#'+full_path)
                    else:
                        pass
            elif not request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest':
                if full_path.startswith('/graph/chart') and not full_path.startswith('/graph/chartpath/') or full_path.startswith('/usr/settings'):
                    return HttpResponseRedirect('/#'+full_path)
    
        
def process_exception(request, exception):
    if request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest':
        error_page="sns/error_ajax.html"
        login_page="sns/login_error_ajax.html"
    else:
        error_page="sns/error.html"
        login_page="sns/login_error.html"
    if type(exception) == api_error.ApiError and exception.error_code==api_error.API_ERROR_USER_NOT_LOGGED_IN:
        return render_to_response(login_page, dict(msg='You have not signed in',url=users.create_login_url(request.get_full_path())+'/redirecturl'
                                                   ),context_instance=RequestContext(request))
    else:
        view=ControllerView('Error')
        msg=str(exception)
        logging.error(msg)
    
        if type(exception) == CapabilityDisabledError:
            return render_to_response("sns/maintenance.html", dict(title='Error Message', msg='The application is now in read-only. Please try again later.',view=view),context_instance=RequestContext(request))
        else:
            msg="error in handling your request"
        
        return render_to_response(error_page, dict(title='Error Message', msg=msg,view=view),context_instance=RequestContext(request))
        
