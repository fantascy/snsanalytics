from django.views.generic.list_detail import object_list
from sns.api.facade import iapi
from sns.view.baseview import BaseView
from sns.view.controllerview import ControllerView
from sns.api import consts as api_const
from sns.camp import consts as camp_const
from sns.view import consts as view_const
from sns.camp.api import CampaignProcessor
from sns.camp.forms import CampaignCreateForm, CampaignUpdateForm

class CampaignView(BaseView, ControllerView):
    
    def __init__(self):
        BaseView.__init__(self, api_const.API_M_CAMPAIGN, create_form_class=CampaignCreateForm, update_form_class=CampaignUpdateForm)
        ControllerView.__init__(self, "Admin")
        return
    
    def input_datetime_params(self):
        r"""
        list of param keys that are type of date, time, or datetime. these params need timezone translation.
        """
        return BaseView.input_datetime_params(self) + ['scheduleStart','scheduleEnd','scheduleNext']
    
    def output_datetime_params(self):
        return BaseView.output_datetime_params(self) + ['scheduleStart','scheduleEnd','scheduleNext'] 
    
    
    def initiate_create_params(self,request):
        params = BaseView.initiate_create_params(self, request)
        params['scheduleInterval']='1Hr'
        params['gaSource']=camp_const.CAMPAIGN_ANALYTICS_SOURCE_DEFAULT
        params['gaMedium']='email'
        params['gaUseCampaignName']=True
        return params
    
    def custom_api2form(self,api_params):
        params = BaseView.custom_api2form(self,api_params)
        if params['gaSource'] is None or params['gaSource']=='':
            params['gaSource']=camp_const.CAMPAIGN_ANALYTICS_SOURCE_DEFAULT
        if params['gaMedium'] is None or params['gaMedium']=='':
            params['gaMedium']='email'
        return params
      
    
    def titleList(self):
        return "Campaign" 
    
    def titleCreate(self):
        return "Add a Campaign"
    
    def titleUpdate(self):
        return "Modify a Campaign"
    
    def titleDetail(self):
        return "Campaign Details"
    

def list(request):
    num = len(CampaignProcessor().query_base().fetch(limit=view_const.SHOW_SEARCH_NUMBER))
    show_search= (num==view_const.SHOW_SEARCH_NUMBER)  
    view = CampaignView()
    keyword=request.GET.get('query','')
    sortBy = request.GET.get('sortBy','modifiedTime')
    if sortBy == 'name': 
        sortBy = 'nameLower' 
    ret_url='campaign/?query='+keyword
    params=dict(view=view, title=view.titleList,ret_url=ret_url,keyword=keyword,show_search=show_search)    
    objects = []
    return object_list( request, 
                            objects,
                            paginate_by=view_const.DEFAULT_INITIAL_PAGE_SIZE,
                            extra_context = params,
                            template_name='sns/' + api_const.API_M_CAMPAIGN +"/list.html"
                           )
    
def create(request):
    campaignView = CampaignView()
    return campaignView.create(request, campaignView)

def update(request):
    campaignView = CampaignView()
    return campaignView.update(request, campaignView)

def delete(request):
    campaignView = CampaignView()
    return campaignView.delete(request)

def detail(request, id):
    campaignView = CampaignView()
    return campaignView.detail(request, id, campaignView)

def activate(request):
    campaignView = CampaignView()
    return campaignView.activate(request)

def deactivate(request):
    campaignView = CampaignView()
    return campaignView.deactivate(request)

def test(request):
    CampaignProcessor().cron_execute('')
    
    num = len(CampaignProcessor().query_base().fetch(limit=view_const.SHOW_SEARCH_NUMBER))
    show_search= (num==view_const.SHOW_SEARCH_NUMBER)   
    view = ControllerView()
    keyword=request.GET.get('query','')
    ret_url='campaign/?query='+keyword
    params=dict(view=view, title="Campaign",ret_url=ret_url,keyword=keyword,show_search=show_search)    
    objects = []
    return object_list( request, 
                            objects,
                            paginate_by=view_const.DEFAULT_INITIAL_PAGE_SIZE,
                            extra_context = params,
                            template_name='sns/' +api_const.API_M_CAMPAIGN +"/list.html"
                           )
    
