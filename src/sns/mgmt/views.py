import csv

from google.appengine.ext import db
from django.views.generic.list_detail import object_list
from django.http import HttpResponse
from django.shortcuts import render_to_response
from django.template import RequestContext

from common.utils import string as str_util
from sns.serverutils import deferred
from sns.core.core import SystemStatusMonitor
from sns.api import consts as api_const
from sns.camp import consts as camp_const
from sns.cont import consts as cont_const
from sns.cont.models import NoChannelTopic
from sns.log import consts as log_const
from sns.log.models import GlobalStats
from sns.mgmt.api import ContentCampaignProcessor, TopicCampaignProcessor
from sns.view.controllerview import ControllerView 
from sns.view.baseview import BaseView
from sns.mgmt.forms import ContentCampaignCreateForm, ContentCampaignUpdateForm, \
            TopicContentCampaignCreateForm, TopicContentCampaignUpdateForm,NoChannelForm,NoTopicForm


class ContentCampaignView(BaseView,ControllerView):
    def __init__(self):
        BaseView.__init__(self,api_const.API_M_MGMT,ContentCampaignCreateForm,ContentCampaignUpdateForm)
        ControllerView.__init__(self)
            
    def titleCreate(self):
        return "Add CMP Campaign"
    
    def titleUpdate(self):
        return "Modify CMP Campaign" 
    
class TopicContentCampaignView(BaseView,ControllerView):
    def __init__(self):
        BaseView.__init__(self,api_const.API_M_MGMT_TOPIC,TopicContentCampaignCreateForm,TopicContentCampaignUpdateForm)
        ControllerView.__init__(self)
            
    def titleCreate(self):
        return "Add Topic Content Campaign"
    
    def titleUpdate(self):
        return "Modify Topic Content Campaign" 
        
    
def list(request):
    objects= ContentCampaignProcessor().query_base().order('-priority')
    return object_list(request, 
                       objects,paginate_by=10, 
                       template_name='sns/mgmt/list.html', 
                       extra_context={'view':ContentCampaignView(), 
                                      'title':'CMP Campaigns'})
    
def create(request):
    view=ContentCampaignView()
    extra_params = {}   
    return view.create(request, view, extra_params=extra_params, template_name='form.html')

def update(request):
    view=ContentCampaignView()
    extra_params = {}   
    return view.update(request, view, extra_params=extra_params ,template_name='form.html')

def delete(request):
    view=ContentCampaignView()
    return view.delete(request)


def update_channel_campaign(request):
    channel = db.get(request.POST.get('id'))
    keywords = str_util.split_strip(request.POST.get('keyword'), '|')
    if ContentCampaignProcessor().update_channel_campaign(channel, keywords):
        return HttpResponse("success")
    else:
        return HttpResponse("failure")


def tc_list(request):
    objects= TopicCampaignProcessor().query_base()
    return object_list(request, 
                       objects,paginate_by=10, 
                       template_name='sns/mgmt/topic/list.html', 
                       extra_context={'view':TopicContentCampaignView(), 
                                      'title':'Topic Content Campaigns'})
    
def tc_create(request):
    view=TopicContentCampaignView()
    extra_params = {}   
    return view.create(request, view, extra_params=extra_params, template_name='form.html')

def tc_update(request):
    view=TopicContentCampaignView()
    extra_params = {}   
    return view.update(request, view, extra_params=extra_params ,template_name='form.html')

def tc_delete(request):
    view=TopicContentCampaignView()
    return view.delete(request)

def tc_activate(request):
    rule = db.get(request.GET.get('id'))
    if rule.state == camp_const.CAMPAIGN_STATE_INIT:
        rule.state = camp_const.CAMPAIGN_STATE_ACTIVATED
    else:
        rule.state = camp_const.CAMPAIGN_STATE_INIT
    rule.put()
    return HttpResponse(str(rule.state)) 

def tc_nochannel(request):
    priority = int(request.GET.get('priority',-1))
    keyword = request.GET.get('query','')
    pagination = int(request.GET.get('pagination',20))
    objects= NoChannelTopic.all().order('name')
    if priority != -1:
        objects = objects.filter('priority',priority)
    form = NoChannelForm(initial={'priority':priority,'pagination':pagination})
    if keyword != '':
        objects = NoChannelTopic.searchIndex.search(keyword)
    post_path = '/mgmt/topic/nochannel/?paginate_by='+str(pagination) + '&priority='+str(priority)
    return object_list(request, 
                       objects,
                       paginate_by=pagination, 
                       template_name='sns/mgmt/topic/nochannel_list.html', 
                       extra_context={'view':TopicContentCampaignView(),'post_path':post_path,'form':form,
                                      'title':'Topics without Twitter Account'})
    
def tc_notopic(request):
    stats = GlobalStats.get_or_insert_by_id(log_const.GLOBAL_STATS_CMP_TWITTER_ACCT_NO_TOPICS)
    noTopicList = stats.get_counter_info()[1]
    if noTopicList is None:
        noTopicList = []
    infos = []
    pagination = int(request.GET.get('pagination',50))
    for info in noTopicList:
        ce = info.split(':')
        infos.append((ce[0], ce[1], ce[2]))
    infos.sort(lambda x,y: cmp(x[0], y[0]))
    form = NoTopicForm(initial={'pagination':pagination})
    post_path = '/mgmt/topic/notopic/?paginate_by='+str(pagination)
    return object_list(request, 
                       infos,
                       paginate_by=pagination, 
                       template_name='sns/mgmt/topic/notopic_list.html', 
                       extra_context={'view':TopicContentCampaignView(),'post_path':post_path,
                                      'title':'CMP Twitter Accounts without Topic','form':form})
    

def tc_nochannel_update(request):
    priority = int(request.GET.get('priority',-1))
    nochannel = db.get(request.GET.get('id'))
    nochannel.priority = priority
    nochannel.put()
    return HttpResponse('OK')


def tc_nochannel_export(request):
    response = HttpResponse(mimetype='text/csv')
    response['Content-Disposition'] = 'attachment; filename=NoChannelTopics.csv'
    writer = csv.writer(response)
    writer.writerow(['Topic'])
    monitor = SystemStatusMonitor.get_system_monitor(cont_const.MONITOR_TOPIC_CAMPAIGN_EXECUTE)
    objects= monitor.info.split('|')
    for obj in objects:
        writer.writerow([obj])
    return response


def confirm(request):
    return render_to_response('sns/mgmt/confirm.html', {'id':request.GET.get('id')},
                                   context_instance=RequestContext(request,{"path":request.path}))

    
def sync(request):
    cmp_camp_id = request.POST.get('id')
    deferred.defer(ContentCampaignProcessor.deferred_sync, cmp_camp_id)
    return HttpResponse('OK')
    


    