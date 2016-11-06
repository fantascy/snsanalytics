from exceptions import Exception

from google.appengine.api import users
from django.http import HttpResponseRedirect,HttpResponse
import logging
import context


def process_request(request):
    if not context.get_context().require_google_login() or is_google_bot(request):
        return
    user = users.get_current_user()
    if request.get_full_path()!= '/cake/login/':
        if user is None :
            return HttpResponse(status=404)
        if not users.is_current_user_admin() :
            raise Exception
    
        
def process_exception(request, exception):
    logging.exception('Unexpected cake error!')
    return HttpResponseRedirect('/')
        

def is_google_bot(request):
    agent=context.get_context().http_user_agent()
    if agent.lower().find('google') != -1 or agent.lower().find('facebook') != -1 :
        return True
    else:
        return False