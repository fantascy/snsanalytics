import logging
from datetime import datetime, timedelta

from google.appengine.ext import db
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.views.generic.list_detail import object_list
from django.http import HttpResponse

from sns.usr import timezone as utz_util
from sns.api.facade import iapi
from sns.api import consts as api_const
from sns.dm.forms import DMCampaignCreateForm, DMCampaignUpdateForm, DMCampaignChartForm, DMCampaignSortByForm, AdvancedDMCampaignCreateForm, AdvancedDMCampaignUpdateForm, AdvancedDMCampaignChartForm 
from sns.dm.models import DMCampaignClickCounter
from sns.core import consts as core_const
from sns.dm import consts as dm_const
from sns.serverutils import deferred
from sns.dm.api import AdvancedDMCampaignProcessor, BasicDMCampaignProcessor
from sns.report.views import getClickChart,getCounterChart
from sns.dm.models import get_source_account
from sns.chan.models import ChannelHourlyKeyName,ChannelDailyKeyName,HourlySendStats,DailySendStats
from sns.view.baseview import BaseView
from sns.view import consts as view_const
from sns.view.controllerview import ControllerView



FOLLOW_MONITOR_KEYNAME = 'followmonitor'
SEED_MONITOR_KEYNAME = 'seedmonitor'
FOLLOW_STATS_KEYNAME = 'followstats'


class DMCampaignControllerView(ControllerView):
    def __init__(self):
        ControllerView.__init__(self, "Direct Message Campaigns")


class DMCampaignView(BaseView, DMCampaignControllerView):
    def __init__(self):
        BaseView.__init__(self, api_const.API_M_DM_RULE, DMCampaignCreateForm, DMCampaignUpdateForm)
        DMCampaignControllerView.__init__(self)    
            
    def titleList(self):
        return "Basic DM Campaigns" 

    def titleCreate(self):
        return "Add Basic DM Campaign"
    
    def titleUpdate(self):
        return "Modify Basic DM Campaign"
    
    def titleDetail(self):
        return "Basic DM Campaign Details"

    def read_object(self,request):
        params = iapi(self.api_module_name).call('get', request.GET, 'python')
        if params :
            params=self.custom_api2form(params)
            params['ret_url']=request.GET.get('ret_url','')
            params['current_page']=request.GET.get('current_page','')
            form = self.update_form_class(initial=params)
        return form
    
    def initiate_create_params(self,request):
        params = BaseView.initiate_create_params(self, request)
        params['googleAnalytics']= True
        params['analyticsSource']='KillerSocialApps'
        params['analyticsMedium']='Twitter'
        params['defaultCampaign']=True
        return params

    def custom_api2form(self,api_params):
        params = BaseView.custom_api2form(self,api_params)
        if params['gaSource'] is None or params['gaSource']=='':
            params['gaSource']='KillerSocialApps'
        if params['gaMedium'] is None or params['gaMedium']=='':
            params['gaMedium']='Twitter'
        if params.has_key('sourceChannel') and params['sourceChannel'] is not None:
            params['sChannel']=db.get(params['sourceChannel']).login()
        return params
    

class AllDMCampaignView(DMCampaignView):
    def titleList(self):
        return "All Basic DMs" 


class AdvancedDMCampaignView(DMCampaignView):
    
    def __init__(self):
        BaseView.__init__(self, api_const.API_M_ADVANCED_DM_RULE, AdvancedDMCampaignCreateForm, AdvancedDMCampaignUpdateForm)
        DMCampaignControllerView.__init__(self)  
        
    def titleList(self):
        return "Advanced DM Campaigns" 

    def titleCreate(self):
        return "Add Advanced DM Campaign"
    
    def titleUpdate(self):
        return "Modify Advanced DM Campaign"
    
    def titleDetail(self):
        return "Advanced DM Campaign Details"

    def custom_form2api(self,params):
        params = DMCampaignView.custom_form2api(self,params)
        params['categoryType'] = int(params['categoryType'])
        params['sourceChannel'] = None
        if params['categoryType'] == dm_const.PROMOTE_CATEGORY_TYPE_NATION:
            params['topics'] = params['nationalTopics']
        return params
    
    def custom_api2form(self,params):
        params = DMCampaignView.custom_api2form(self,params)
        params['categoryType'] = int(params['categoryType'])
        if params['categoryType'] == dm_const.PROMOTE_CATEGORY_TYPE_NATION:
            params['nationalTopics'] = params['topics']
            params['topics'] = []
        return params
        
def parseHourlyKeyname(keyname):
    words=keyname.split("_")
    time = datetime(hour=int(words[-1]),day=int(words[-2]),month=int(words[-3]),year=int(words[-4]))
    return time


def parseDailyKeyname(keyname):
    words=keyname.split("_")
    time = datetime(day=int(words[-1]),month=int(words[-2]),year=int(words[-3]))
    return time


def dmrule_list(request):
    view = DMCampaignView()
    extra_params = dict(form=DMCampaignSortByForm(),sortByType='nameLower')
    return view.list(request, view,  extra_params= extra_params)  


def dmrule_create(request):
    view = DMCampaignView()
    return view.create(request, view)


def dmrule_update(request):
    view = DMCampaignView()
    return view.update(request, view, template_name= 'update_form.html')


def dmrule_delete(request):
    try:
        view=DMCampaignView()
        response = view.delete(request)
        return response
    except Exception,ex:
        logging.error('Delete article error:%s' % str(ex))
        return HttpResponse("Exception:"+str(ex))


def dmrule_activate(request):
    view = DMCampaignView()
    return view.activate(request)


def dmrule_deactivate(request):
    view = DMCampaignView()
    return view.deactivate(request)


def haveDMChart(id, unit):
    return 'True'
    

def getChartSrc(id,unit):
    rule=db.get(id)
    chid = rule.sourceChannel.keyNameStrip()
    parent = get_source_account(chid)
    endDate = rule.modifiedTime
    if unit == 'hour':
        modelClass = HourlySendStats
        nameClass  = ChannelHourlyKeyName
        hourCount=24*7
        startDate = endDate-timedelta(hours=hourCount-1)
        startDate = max(rule.createdTime,startDate)
        interval = timedelta(hours=1)
    elif unit == 'day':
        modelClass = DailySendStats
        nameClass  = ChannelDailyKeyName
        startDate = rule.createdTime-timedelta(days=1)
        interval = timedelta(days=1)  
    firstQuery = modelClass.all().ancestor(parent).filter('createdTime >', startDate).order('createdTime')
    lastQuery  = modelClass.all().ancestor(parent).filter('createdTime <', endDate).order('-createdTime')
    
    if firstQuery.count(1000) == 0 or lastQuery .count(1000) == 0:
        logging.info('No historical data available')
        return [0],rule.modifiedTime,rule.modifiedTime
    else:
        firstStats = firstQuery.fetch(limit=1)[0]
        lastStats = lastQuery.fetch(limit=1)[0]
    
    if unit == 'hour':
        firstTime = parseHourlyKeyname(firstStats.key().name())
        lastTime  = parseHourlyKeyname(lastStats.key().name())
    elif unit == 'day':
        firstTime = parseDailyKeyname(firstStats.key().name())
        lastTime  = parseDailyKeyname(lastStats.key().name())
        
    statsTime=firstTime
    counters=[]
    while statsTime <=lastTime:
        keyName = nameClass.keyName(chid, statsTime)
        stats = modelClass.get_by_key_name(keyName, parent=parent)
        if stats is None :
            counters.append(0)
        else:
            counters.append(stats.sendCount) 
        statsTime += interval
        
    chartstart = datetime(year=firstTime.year,month=firstTime.month,day=firstTime.day,hour=firstTime.hour)
    chartend   = datetime(year=lastTime.year,month=lastTime.month,day=lastTime.day,hour=lastTime.hour)
    
    chartstart = utz_util.to_usertz(chartstart)
    chartend = utz_util.to_usertz(chartend)    
    return counters,chartstart,chartend


def dmrule_sendcount(request):
    id = request.POST.get('id','')
    rule = db.get(id)
    sendCount = rule.totalSendCount + rule.totalFailCount
    if rule.followerNumber is None:
        tapi = rule.getTwitterApi()
        info = tapi.account.verify_credentials()
        rule.followerNumber = info['followers_count']
        rule.put()
    sendInfo = str(sendCount) + ' / ' +str(rule.followerNumber)
    failInfo = str(rule.totalSendCount) + ' / '+str(rule.totalFailCount)
    return render_to_response("sns/dm/rule/send_info.html",dict(sendInfo=sendInfo,failInfo=failInfo), context_instance=RequestContext(request));
    

def dmrule_clickcount(request):
    id = request.POST.get('id','')
    turn = request.POST.get('turn',0)
    rule = db.get(id)
    dmRuleClickCounter = DMCampaignClickCounter.get_or_insert(DMCampaignClickCounter.keyName(id+'_'+str(turn)), parent=rule.parent())   
    clickCount = dmRuleClickCounter.life
    if len(rule.sendTurn) == 0:
        sendCount = rule.totalSendCount
    else:
        sendCount = rule.sendTurn[int(turn)]
    if rule.totalSendCount == 0:
        rate = "0 %"
    else:
        rate = clickCount*100.0/rule.totalSendCount
        rate = str(round(rate, ndigits=2)) + ' %'
    return render_to_response("sns/dm/rule/click_info.html",dict(clickCount=clickCount,rate=rate, sendCount=sendCount), context_instance=RequestContext(request));
    

def dmrule_chartdetail(request):
    id = request.POST.get('id','')
    infoType = request.POST.get('infoType','')
    chartType = request.POST.get('chartType','')
    turn = request.POST.get('turn','0')
    infoTypes = dm_const.INFO_TYPES
    info = id+'_'+infoType+'_'+chartType+'_'+turn
    hasChart = 'True'
    if chartType == 'sendcount':
        hasChart = haveDMChart(id,infoType)
        
    return render_to_response("sns/dm/rule/chart.html",dict(hasChart=hasChart,info=info,infoType=infoType,chartType=chartType,
                                                               infoTypes=infoTypes,
                                                               ), context_instance=RequestContext(request));
                                                               

def dmrule_chartdata(request):
    info = request.GET.get('info','')
    infos= info.split("_")
    id = infos[0]
    infoType = infos[1]
    chartType = infos[2]
    turn = infos[3]
    rule = db.get(id)
    dmRuleClickCounter = DMCampaignClickCounter.get_or_insert(DMCampaignClickCounter.keyName(id+'_'+str(turn)), parent=rule.parent())   
    now = datetime.utcnow()        
    timeDelta = now - dmRuleClickCounter.createdTime                                                        
    if infoType == 'hour':
        units = timeDelta.days*24+timeDelta.seconds/3600+1
        if units > 24*7:
            units = 24*7
        timeunit = core_const.TIME_UNIT_HOUR
    elif infoType == 'day':
        units = timeDelta.days+1
        timeunit = core_const.TIME_UNIT_DAY
    #units = len(dmRuleClickCounter)
    if chartType == 'clickcount':
        data = getClickChart(dmRuleClickCounter,timeunit,units,noLabel=True)
    if chartType == 'sendcount':
        counters,startTime,endTime = getChartSrc(id,infoType)
        logging.info("len(counters) %s" % len(counters))
        logging.info("units %s" % units)
        logging.info("timeunit %s" % timeunit)
        units = len(counters)
        data = getCounterChart(counters,timeunit,units,startTime,endTime,title="Total DMs")
        
    return HttpResponse(data)

            
def dmrule_chart(request):
    id = request.GET.get('id','')
    infoType = dm_const.INFO_TYPES[0][0]
    form = DMCampaignChartForm(id)
    hideform=False
    rule = db.get(id)
    title = rule.name + ' / ' + rule.sourceChannel.name
    return render_to_response("sns/dm/rule/chart_list.html",dict(infoType=infoType,
                                                                    id=id,
                                                                    title=title,
                                                                    form=form,
                                                                    infoTypes=dm_const.INFO_TYPES,
                                                                    hideform=hideform,
                                                                    view=ControllerView()
                                                                    ), context_instance=RequestContext(request));                     
                                                                    

def dmrule_advanced_chart(request):
    id = request.GET.get('id','')
    infoType = dm_const.INFO_TYPES[0][0]
    form = AdvancedDMCampaignChartForm()
    hideform=False
    rule = db.get(id)
    title = rule.name 
    return render_to_response("sns/dm/rule/chart_list.html",dict(infoType=infoType,
                                                                    id=id,
                                                                    title=title,
                                                                    form=form,
                                                                    infoTypes=dm_const.INFO_TYPES,
                                                                    hideform=hideform,
                                                                    view=ControllerView()
                                                                    ), context_instance=RequestContext(request));      
    

def dm_all_rule_list(request):
    show_search= True
    view = AllDMCampaignView()
    keyword=request.GET.get('query', '')
    
    sortBy = request.GET.get('sortby', 'nameLower')
    directType = request.GET.get('directType', 'asc')
    paginate_by = request.GET.get('paginate_by', view_const.DEFAULT_INITIAL_PAGE_SIZE)
    
    try:
        paginate_by = int(paginate_by)
    except:
        paginate_by = view_const.DEFAULT_INITIAL_PAGE_SIZE
    
    ret_url='dm/all/rule/list/?query='+keyword

    if not keyword or keyword == '':    
        objects = BasicDMCampaignProcessor().getModel().all().filter('deleted =',False).order(('-' if directType == 'desc' else '')+sortBy)
    else:
        objects = BasicDMCampaignProcessor().getModel().search_index.search(keyword,filters=('deleted =', False))
    
    page=request.GET.get('page','1')
    paginate_by=paginate_by
    total_number=len(objects)
    total_pages=total_number/paginate_by+1
    if total_pages<int(page):
        page=total_pages
    show_list_info='True'
    if total_number<5:
        show_list_info='False' 
    params=dict(view=view,form=DMCampaignSortByForm(), title=view.titleList(),show_list_info=show_list_info,ret_url=ret_url,keyword=keyword,
                show_search=show_search, current_page=str(page),sortBy=sortBy, directType=directType, paginate_by= paginate_by,post_path='/dm/all/rule/list/'+'?sortby='+sortBy+'&directType='+directType+'&paginate_by='+str(paginate_by)+'&query='+keyword)    
    
    return object_list( request, 
                            objects,
                            paginate_by=paginate_by,
                            page=page,
                            extra_context = params,
                            template_name='sns/dm/all/list.html'
                           )
                             
def dmrule_advanced_list(request):
    view = AdvancedDMCampaignView()
    extra_params = dict(form=DMCampaignSortByForm(),sortByType='nameLower')
    return view.list(request, view,  extra_params= extra_params)  


def dmrule_advanced_create(request):
    view = AdvancedDMCampaignView()
    return view.create(request, view)


def dmrule_advanced_update(request):
    view = AdvancedDMCampaignView()
    return view.update(request, view, template_name= 'update_form.html')


def dmrule_advanced_delete(request):
    view=AdvancedDMCampaignView()
    response = view.delete(request)
    return response
  
  
def dmrule_advanced_activate(request):
    view = AdvancedDMCampaignView()
    return view.activate(request)


def dmrule_advanced_deactivate(request):
    view = AdvancedDMCampaignView()
    return view.deactivate(request)

def dmrule_advanced_confirm(request):
    return render_to_response('sns/dm/rule/advanced/confirm.html', {'id':request.GET.get('id')},
                                   context_instance=RequestContext(request,{"path":request.path}))

def dmrule_advanced_sync(request):
    ruleId = request.POST.get('id')
    deferred.defer(AdvancedDMCampaignProcessor._deferred_sync_dm_campaigns,ruleId)
    return HttpResponse('ok')