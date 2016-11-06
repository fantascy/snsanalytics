from django.http import HttpResponse

import context
from sns.api import consts as api_const
from sns.view.baseview import BaseView
from sns.view.controllerview import ControllerView 
from sns.deal import consts as deal_const
from sns.deal.models import DealBuilder, CatDealBuilder, DealStats
from sns.deal.forms import DealBuilderCreateForm, DealBuilderUpdateForm, DealStatsForm
from django.views.generic.list_detail import object_list


class DealBuilderView(BaseView, ControllerView):
    def __init__(self):
        BaseView.__init__(self,api_const.API_M_DEAL_BUILDER,DealBuilderCreateForm,DealBuilderUpdateForm)
        ControllerView.__init__(self)
            
    def titleList(self):
        return 'Deal Feeds'
    
    def titleCreate(self):
        return "Add Deal Feed"
    
    def titleUpdate(self):
        return "Modify Deal Feed" 
        
    
def deal_list(request):
    view=DealBuilderView()
    extra_params = {'sortByType': 'nameLower'}  
    return view.list(request, view, extra_params=extra_params)
    

def deal_create(request):
    view=DealBuilderView()
    extra_params = {'domain': context.get_context().feedbuilder_domain()}
    return view.create(request, view, extra_params=extra_params, template_name='form.html')


def deal_update(request):
    view=DealBuilderView()
    extra_params = {'domain': context.get_context().feedbuilder_domain()}
    return view.update(request, view, extra_params=extra_params ,template_name='form.html')


def deal_delete(request):
    return DealBuilderView().delete(request)


def deal_rss_location(request, location):
    return _deal_rss_location(request, location, channel_type=deal_const.CHANNEL_DEAL_TWITTER_ACCOUNTS)


def deal_rss_location_mobile(request, location):
    return _deal_rss_location(request, location, channel_type=deal_const.CHANNEL_DEAL_MOBILE_APPS)


def _deal_rss_location(request, location, channel_type):
    cat = request.REQUEST.get('cat', None)
    if cat is None :
        builder = DealBuilder.get_by_key_name(DealBuilder.keyName(location))
    else :
        builder = CatDealBuilder.get_by_key_name(CatDealBuilder.key_name(location, cat))
    return _deal_feed(builder, channel_type)


def deal_rss_location_cat(request, location, cat):
    return _deal_rss_location_cat(request, location, cat, channel_type=deal_const.CHANNEL_DEAL_TWITTER_ACCOUNTS)


def deal_rss_location_cat_mobile(request, location, cat):
    return _deal_rss_location_cat(request, location, cat, channel_type=deal_const.CHANNEL_DEAL_MOBILE_APPS)


def _deal_rss_location_cat(request, location, cat, channel_type):
    builder = CatDealBuilder.get_by_key_name(CatDealBuilder.key_name(location, cat))
    return _deal_feed(builder, channel_type)


def _deal_feed(dealBuilder, channel_type):
    context.get_context().set_login_required(False)
    if dealBuilder is None :
        return HttpResponse(status=404)
    return HttpResponse(dealBuilder.feed(channel_type=channel_type).writeString('utf-8'), 'text/html')
    

class DealStatsView(BaseView, ControllerView):
    def __init__(self):
        BaseView.__init__(self,api_const.API_M_DEAL_BUILDER)
        ControllerView.__init__(self)
            
    def titleList(self):
        return 'Deal Stats'
    
    
def deal_stats(request):
    view = DealStatsView()
    orderBy = request.REQUEST.get("orderBy", "totalClicks")
    location = request.REQUEST.get("location", "all")
    cat = request.REQUEST.get("cat", "all")
    pagination = int(request.REQUEST.get("pagination",20))
    keyword = request.REQUEST.get("query", "")
    if keyword is not None and keyword != "":
        query = DealStats.searchIndex.search(keyword)
    else:
        query = DealStats.all()
        if cat != 'all':
            query = query.filter('category',cat)
        if location != 'all':
            query = query.filter('location',location)
        query = query.order('-'+orderBy)
    form = DealStatsForm(initial={'orderBy':orderBy, 'location':location, 'cat':cat, 'pagination':pagination})
    post_path = "/#/deal/stats/?orderBy=" + str(orderBy) + "&cat="+cat+"&location=" + location + "&pagination=" + str(pagination)
    return object_list(request,
                       query,
                       paginate_by=pagination,
                       extra_context=dict(view=view, title=view.titleList(), orderBy=orderBy, form=form, post_path=post_path, pageSize=pagination, keyword=keyword),
                       template_name="sns/deal/deal_stats.html")
    
