from django.shortcuts import render_to_response
from django.template import RequestContext
from soup.view.controllerview import ContentView, SOUP_FACEBOOK_PAGE


class CorpView(ContentView):
    def __init__(self, title):
        ContentView.__init__(self)
        self.title = title
        
    def name(self):
        return self.title
    
    def pageTitle(self):
        return "Allnewsoup.com - %s" % self.title

    def pageDescription(self):
        return self.pageTitle()

    def sideColumnFacebookPage(self):
        return SOUP_FACEBOOK_PAGE
    

def tos(request):
    return render_to_response('soup/corp/tos.html', dict(view=CorpView(title="Terms of Service")), context_instance=RequestContext(request))
    

