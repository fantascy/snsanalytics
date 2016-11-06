from django.views.generic.simple import direct_to_template, redirect_to
from django.views.defaults import page_not_found as django_page_not_found

import deploysoup
import context
import settings
from sns.dashboard.views import home as sns_home
from sns.chan.views import twitter_callback as new_twitter_callback
from sns.chan.views import facebook_callback as new_facebook_callback
from sns.url.views import redirect as new_redirect
from msb.dashboard.views import home as msb_home
from fe.dashboard.views import home as fe_home
from soup.dashboard.views import home as soup_home
from cake.dashboard.views import home as cake_home
from soup.user.views import twitter_callback as soup_twitter_callback


_DASHBOARD_MAP = {
    "sns" : sns_home,
    "msb" : msb_home,
    "fe" : fe_home,
    "soup" : soup_home,
    "cake" : cake_home,
    "appspot" : sns_home,
    }

def home(request):
    return _DASHBOARD_MAP[context.get_context().app()](request)
        
def twitter_callback(request):
    if context.get_context().app() == deploysoup.APP :
        return soup_twitter_callback(request)
    else:
        return new_twitter_callback(request)

def facebook_callback(request):
    return new_facebook_callback(request)
    
def redirect(request, urlHash):
    return new_redirect(request, urlHash)
    
def page_not_found(request):
    context.get_context().set_login_required(False)
    return django_page_not_found(request, template_name=("%s/404.html" % context.get_context().app()))
      
def favicon(request):
    context.get_context().set_login_required(False)
    return redirect_to(request, url=("%s%s/images/favicon.ico" % (settings.MEDIA_URL, context.get_context().app())))

def robot_txt(request):
    context.get_context().set_login_required(False)
    return direct_to_template(request, "%s/robots.txt" % context.get_context().app())
