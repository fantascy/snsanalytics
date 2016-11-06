from django.http import HttpResponse
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.utils import feedgenerator

import context
from sns.api import consts as api_const
from sns.view.baseview import BaseView
from sns.view.controllerview import ControllerView 
from sns.feedbuilder.models import FeedBuilder
from sns.feedbuilder.api import ComboFeedBuilderProcessor, TopicScoreFeedBuilderProcessor, TroveFeedBuilderProcessor
from sns.feedbuilder.forms import FeedBuilderCreateForm, FeedBuilderUpdateForm, FeedBuilderSortByForm


class FeedBuilderView(BaseView,ControllerView):
    def __init__(self):
        BaseView.__init__(self,api_const.API_M_FEED_BUILDER,FeedBuilderCreateForm,FeedBuilderUpdateForm)
        ControllerView.__init__(self)
        
    def custom_form2api(self, form_params):
        api_params = BaseView.custom_form2api(self, form_params)
        api_params['feeds'] = map(lambda x: x.id, form_params['feeds'])
        return api_params
    
    def titleList(self):
        return 'Build Your Own Feeds'
    
    def titleCreate(self):
        return "Build Feed"
    
    def titleUpdate(self):
        return "Modify Feed" 
        
    
def lst(request):
    view=FeedBuilderView()
    extra_params = dict(form=FeedBuilderSortByForm(), sortByType='nameLower', model_name='feed', domain=context.get_context().feedbuilder_domain())    
    return view.list(request, view, extra_params= extra_params)
    

def create(request):
    view=FeedBuilderView()
    extra_params = {'domain':context.get_context().feedbuilder_domain()}
    return view.create(request, view, extra_params=extra_params, template_name='form.html')


def update(request):
    view=FeedBuilderView()
    extra_params = {'domain':context.get_context().feedbuilder_domain()}
    return view.update(request, view, extra_params=extra_params ,template_name='form.html')


def delete(request):
    view=FeedBuilderView()
    return view.delete(request)


def feed(request, uri):
    context.get_context().set_login_required(False)
    builder = FeedBuilder.all().filter('uri', uri).filter('deleted', False).fetch(limit=1)
    if len(builder) == 0:
        return HttpResponse(status=404)
    builder = builder[0]
    f = feedgenerator.Atom1Feed(title = builder.name,description=builder.name,link=builder.feedUrl())
    for item in builder.items:
        item = eval(item)
        f.add_item(title = item['title'], link= item['link'], description=item['description'])
    info = f.writeString('utf-8')
    return HttpResponse(info,'text/html')
    

def hlp(request):
    return render_to_response("sns/feedbuilder/help.html",dict(),context_instance=RequestContext(request))


def combo_feed(request, q):
    return _feed_builder_feed(processor=ComboFeedBuilderProcessor(), q=q)


def topic_score_feed(request, q):
    return _feed_builder_feed(processor=TopicScoreFeedBuilderProcessor(), q=q)


def trove_feed(request, q):
    return _feed_builder_feed(processor=TroveFeedBuilderProcessor(), q=q)


def _feed_builder_feed(processor, q):
    context.get_context().set_login_required(False)
    info = processor.fetch_content_by_topic_key(q)
    if info:
        return HttpResponse(info,'text/html')
    else:
        return HttpResponse(status=404)

