from django.shortcuts import render_to_response
from django.template import RequestContext

from soup.view.controllerview import ContentView, SOUP_FACEBOOK_PAGE
        

class SearchView(ContentView):
    def __init__(self):
        ContentView.__init__(self)
        self.query = self.ctx().request().REQUEST.get('q', "") 

    def name(self):
        return "Google Custom Search"
    
    def pageTitle(self):
        return "Allnewsoup Search - %s" % (self.query,)
    
    def pageDescription(self):
        return "%s - powered by Google Custom Search" % (self.pageTitle(),)
    
    def sideColumnFacebookPage(self):
        return SOUP_FACEBOOK_PAGE
    

def google_custom_search(request):
    return render_to_response('soup/search/search.html',dict(view=SearchView()),
                                  context_instance=RequestContext(request,{"path":request.path}))