import json

from django.views.generic.list_detail import object_list
from django.http import HttpResponseRedirect
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.http import HttpResponse

from sns.api import consts as api_const
from sns.view import consts as view_const
from sns.usr import timezone as utz_util
from sns.core.core import get_user_id, ChannelParent, ContentParent, EmailCampaignParent
from sns.api.facade import iapi as sns_iapi


CHANNEL_MODULES = [api_const.API_M_CHANNEL,api_const.API_M_FCHANNEL,api_const.API_M_FBPAGE]
CONTENT_MODULES = [api_const.API_M_ARTICLE,api_const.API_M_FEED,api_const.API_M_FEED_BUILDER]
CAMPAIGN_MODULES = [api_const.API_M_POSTING_RULE_ARTICLE,api_const.API_M_POSTING_RULE_FEED,api_const.API_M_LINK,api_const.API_M_CUSTOM_RULE,api_const.API_M_DM_RULE]
EMAIL_MODULES = [api_const.API_M_MAIL_LIST,api_const.API_M_MAIL_CONTACT,api_const.API_M_MAIL_TEMPLATE,api_const.API_M_MAIL_CAMPAIGN]
GLOBAL_MODULES = [api_const.API_M_DEAL_BUILDER, api_const.API_M_ADVANCED_DM_RULE, api_const.API_M_ACCTMGMT_YAHOO, api_const.API_M_ACCTMGMT_CMP]

LIST_SORT_MAP = {'name':'Name',
                 'modifiedTime':'Last modified time',
                 'status':'Status',
                 'msg':'Message',
                 'scheduleType':'ScheduleType',
                 'state':'Status',
                 '':'',
                 }


class BaseView:
    r"""
    base view, it implements basic create/update/delete/list/detail method. 
    A module can extend this class by implementing custom_api2form and custom_form2api method.
    """
    iapi = sns_iapi
    app_path = 'sns' 
    
    def __init__(self, api_module_name, create_form_class=None, update_form_class=None, update_passwd_form_class=None):
        self.api_module_name=api_module_name
        self.create_form_class=create_form_class
        self.update_form_class=update_form_class       
        self.update_passwd_form_class=update_passwd_form_class

    def template_path(self, template_name):
        return "%s/%s/%s" % (self.app_path, self.api_module_name, template_name)

    def list(self, request, view, template_name="list.html",extra_params={}):
        num = len(self.iapi(self.api_module_name).query_base().fetch(limit=view_const.SHOW_SEARCH_NUMBER))
        show_search= (num==view_const.SHOW_SEARCH_NUMBER)
        keyword=request.GET.get('query','')
        sortBy = request.GET.get('sortby', extra_params.get('sortByType'))
        if sortBy == 'name': 
            sortBy = 'nameLower' 
        directType = request.GET.get('directType', 'asc')
        paginate_by = request.GET.get('paginate_by', view_const.DEFAULT_INITIAL_PAGE_SIZE)
        try:
            paginate_by = int(paginate_by)
        except:
            paginate_by = view_const.DEFAULT_INITIAL_PAGE_SIZE
        
        if not keyword or keyword == '':
            if self.api_module_name in CHANNEL_MODULES:
                objects = self.iapi(self.api_module_name).getModel().all().filter('deleted =',False).ancestor(ChannelParent.get_or_insert_parent()).order(('-' if directType == 'desc' else '')+sortBy)
            if self.api_module_name in CONTENT_MODULES:
                objects = self.iapi(self.api_module_name).getModel().all().filter('deleted =',False).ancestor(ContentParent.get_or_insert_parent()).order(('-' if directType == 'desc' else '')+sortBy)
            if self.api_module_name in EMAIL_MODULES:
                objects = self.iapi(self.api_module_name).getModel().all().filter('deleted =',False).ancestor(EmailCampaignParent.get_or_insert_parent()).order(('-' if directType == 'desc' else '')+sortBy)
            if self.api_module_name in CAMPAIGN_MODULES:
                objects = self.iapi(self.api_module_name).getModel().all().filter('deleted =',False).filter('uid =',get_user_id()).order(('-' if directType == 'desc' else '')+sortBy)
            if self.api_module_name in GLOBAL_MODULES:
                objects = self.iapi(self.api_module_name).getModel().all().filter('deleted =',False).order(('-' if directType == 'desc' else '')+sortBy)
        else:
            if self.api_module_name in CHANNEL_MODULES:
                objects = self.iapi(self.api_module_name).getModel().searchIndex.search(keyword,filters=('deleted =',False)).ancestor(ChannelParent.get_or_insert_parent())
            if self.api_module_name in CONTENT_MODULES:
                objects = self.iapi(self.api_module_name).getModel().searchIndex.search(keyword,filters=('deleted =',False)).ancestor(ContentParent.get_or_insert_parent())
            if self.api_module_name in EMAIL_MODULES:
                objects = self.iapi(self.api_module_name).getModel().searchIndex.search(keyword,filters=('deleted =',False)).ancestor(EmailCampaignParent.get_or_insert_parent())
            if self.api_module_name in CAMPAIGN_MODULES:
                objects = self.iapi(self.api_module_name).getModel().searchIndex.search(keyword,filters=('deleted =',False,'uid =',get_user_id()))
            if self.api_module_name in GLOBAL_MODULES:
                objects = self.iapi(self.api_module_name).getModel().searchIndex.search(keyword,filters=('deleted =',False,))
        page=request.GET.get('page','1')
        paginate_by=paginate_by
        total_number=objects.count()
        total_pages=total_number/paginate_by+1
        if total_pages<int(page):
            page=total_pages
        show_list_info='True'
        if total_number<5:
            show_list_info='False'
        ret_url = '/'+self.api_module_name+'/?sortby='+sortBy+'&directType='+directType+'&query='+keyword+'&paginate_by='+str(paginate_by)+'&page='+str(page)
        post_path = '/'+self.api_module_name+'/?sortby='+sortBy+'&directType='+directType+'&query='+keyword+'&paginate_by='+str(paginate_by)
        params=dict(view=view, title=self.titleList(),show_list_info=show_list_info,ret_url=ret_url, show_search=show_search, current_page=str(page),sortBy=sortBy, directType=directType, paginate_by= paginate_by,post_path=post_path, keyword=keyword)
        params.update(extra_params)
        return object_list( request, 
                            objects,
                            paginate_by=paginate_by,
                            page=page,
                            extra_context = params,
                            template_name = self.template_path(template_name)
                           )

    def create(self, request, view, template_name="form.html",ret_url = None,extra_params={}):
        if request.method=="GET":
            form=self.initiate_create_form(request) # An unbound form
        elif request.method=='POST':
            form=self.create_form_class(request.POST)
            if form.is_valid():
                params=form.cleaned_data.copy()
                if params.has_key('ret_url'):
                    ret_url = params['ret_url']
                self.create_object(form)
                return HttpResponse('success','text/html')
        ret_url = '/'+self.api_module_name+'/' if not ret_url else ret_url
        params={'form': form, 'view' : view, 'title' : self.titleCreate(), 'action':'/'+self.api_module_name+'/create/', 'ret_url':ret_url}
        params.update(extra_params)
        return render_to_response(self.template_path(template_name), 
                                   params,
                                   context_instance=RequestContext(request,{"path":request.path}))
        
    def update(self, request, view, template_name="form.html", ret_url = None, extra_params={}):
        if request.method=="GET":
            form=self.read_object(request)
        elif request.method=='POST':
            form=self.update_form_class(request.POST)      
            if form.is_valid():
                params=form.cleaned_data.copy()
                if params.has_key('ret_url'):
                    ret_url=params['ret_url']
                    if params.has_key('current_page'):
                        ret_url=ret_url+"&page="+params['current_page']
                self.update_object(form)                
                return HttpResponse('success','text/html')
            
        ret_url = '/'+self.api_module_name+'/'
        params = {'form': form, 'view' : view, 'title' : self.titleUpdate(), 'action':'/'+self.api_module_name+'/update/', 'ret_url':ret_url}
        params.update(extra_params)
        return render_to_response(self.template_path(template_name), 
                                  params,
                                  context_instance=RequestContext(request,{"path":request.path}))

    def delete(self,request):
        obj = self.get_object(request)
        self.iapi(self.api_module_name).delete(obj)
        return HttpResponse('success')
    
    def activate(self,request):
        oid = request.GET.get('id', '')
        if oid:
            self.iapi(self.api_module_name).activate(oid)
        return HttpResponseRedirect('/'+self.api_module_name+'/')
    
    def deactivate(self,request):
        oid = request.GET.get('id','')
        if oid:
            self.iapi(self.api_module_name).deactivate(oid)
        return HttpResponseRedirect('/'+self.api_module_name+'/')    
        
    def detail(self, request, id , view, template_name="detail.html", extra_params={}):
        obj=self.iapi(self.api_module_name).call('get', {"id":id})
        params=json.loads(json.dumps(obj, cls=self.iapi(self.api_module_name).getJSONEncoder(), indent=4))
        params=self.custom_api2detail(params)
        params.update(extra_params)
        return render_to_response(self.template_path(template_name), 
                                  {'object': obj, 'view' : view, 'title' : self.titleDetail(), 'params' : params},
                                  context_instance=RequestContext(request),
                                )
        
    def update_object(self,form):
        params=form.cleaned_data.copy()
        params=self.custom_form2api(params)
        form.iapi().update(params)

    def create_object(self,form):
        params=form.cleaned_data.copy()
        params=self.custom_form2api(params)
        form.iapi().create(params)

    def read_object(self,request):
        obj = self.get_object(request)
        params = self.iapi(self.api_module_name).convertFormat(obj,'python')
        if params :
            params=self.custom_api2form(params)
            params['ret_url']=request.GET.get('ret_url','')
            form = self.update_form_class(initial=params)
        return form
    
    def get_object(self,request):
        return self.iapi(self.api_module_name).call('get', request.GET, 'model')
    
    def initiate_create_form(self,request):
        return self.create_form_class(initial=self.initiate_create_params(request))
    
    def order_field(self):
        return "nameLower"
    
    def titleList(self):
        return None
    
    def titleCreate(self):
        return None
    
    def titleUpdate(self):
        return None
    
    def titleDetail(self):
        return None
    
    def input_datetime_params(self):
        return []
    
    def output_datetime_params(self):
        r"""
        list of param keys that are type of date, time, or datetime. these params need timezone translation.
        """
        return ['createdTime','modifiedTime']
    
    def initiate_create_params(self,request):
        params={}
        params['ret_url']=request.GET.get('ret_url','')
        params['left_length']=140
        return params
    
    def custom_form2api(self,form_params):
        r"""
        custom form2api, translate form clean data to a dict acceptable to model api
        """
        if form_params.has_key('keywords'):
            words=unicode(form_params['keywords']).strip()
            keywords = []
            for keyword in words.split(','):
                keywords.append(unicode(keyword).strip())
            form_params['keywords'] = keywords
        utz_util.trans_input(form_params, self.input_datetime_params())
        return form_params.copy()
    
    def custom_api2form(self,api_params):
        r"""
        custom api2form, translate api dict to a dict acceptable to form
        """
        if api_params.has_key('keywords'):
            api_params['keywords']=",".join(api_params['keywords'])
        utz_util.trans_output(api_params, self.output_datetime_params())
        ret_params = api_params.copy()
        ret_params['moduleName'] = self.api_module_name
        return ret_params

    def custom_api2detail(self,api_params):
        r"""
        custom api2detail, translate api dict to a dict acceptable to detail page
        """
        utz_util.trans_output(api_params, self.output_datetime_params())
        ret_params = api_params.copy()
        ret_params['moduleName'] = self.api_module_name
        return ret_params
    



