from django.shortcuts import render_to_response
from django.template import RequestContext
from cake.view.controllerview import ContentView


class CorpView(ContentView):
    def __init__(self, title):
        ContentView.__init__(self)
        self.title = title
        
    def name(self):
        return self.title
    
    def pageTitle(self):
        return "RippleOne.com - %s" % self.title

    def pageDescription(self):
        return self.pageTitle()


def tos(request):
    return render_to_response('cake/corp/tos.html', dict(view=CorpView(title="Terms of Service")), context_instance=RequestContext(request))
    

