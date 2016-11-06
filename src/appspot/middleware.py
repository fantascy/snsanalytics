from django.shortcuts import render_to_response
from django.template import RequestContext

def process_request(request):
    return
            
        
def process_exception(request, exception):
    return render_to_response("appspot/error.html", dict(title='Error Message', msg="TODO",view="TODO"),context_instance=RequestContext(request))
        
