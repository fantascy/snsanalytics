import logging
import json
from datetime import datetime, timedelta

from google.appengine.ext import db
from google.appengine.api import users
from django.views.generic.list_detail import object_list
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.http import HttpResponse
from django.http import HttpResponseRedirect

from common.utils import datetimeparser
from sns.core import consts as core_const
from sns.core import core as db_core
from sns.chan import consts as channel_const
from sns.chan.api import TAccountProcessor
from sns.camp import consts as camp_const
from fe.channel.models import ChannelHourlyStats, ChannelDailyStats, SafeFriendSet
from fe.follow.models import FollowCampaign, FeParentChannel, Config
from fe.follow.api import FollowCampaignProcessor
from fe.follow.forms import FollowCampaignChartForm
from sns.view import consts as view_const
from fe.view.baseview import BaseView
from fe.view.controllerview import ControllerView
from fe.report.views import getCounterChart
from fe.follow.forms import FollowCampaignCreateForm, FollowCampaignUpdateForm, FollowCampaignSafeCreateForm, \
    FollowCampaignSortByForm, AllFollowCampaignSortByForm, SystemSettingsForm


INFO_TYPES = [
     ('hour','7 Days'),
     ('day','Life time'),
              ]
DELIMITER = '____delimiter____' 


class FollowView(BaseView, ControllerView):
    def __init__(self):
        BaseView.__init__(self, 'follow')
        ControllerView.__init__(self)
        

def home(request):
    view = FollowView()
    return render_to_response(view.template_path("home.html"), dict(view=view), context_instance=RequestContext(request))


class FollowByAccountView(BaseView, ControllerView):
    def __init__(self):
        BaseView.__init__(self, 'follow/account', FollowCampaignCreateForm, FollowCampaignUpdateForm)
        ControllerView.__init__(self)
        self.create_safe_form_class = FollowCampaignSafeCreateForm
   
    def custom_form2api(self,form_params):
        return BaseView.custom_form2api(self, form_params)
    
    def custom_api2form(self,api_params):
        return BaseView.custom_api2form(self, api_params)

    def titleList(self):
        return "Follow Campaigns" 

    def titleCreate(self):
        return "Add a Follow Campaign"
    
    def titleUpdate(self):
        return "Modify Follow Campaign"
    
    def titleDetail(self):
        return "Follow Campaign Details"


def followacctrule_list(request):
    num = FollowCampaignProcessor().query_base().count(limit=view_const.SHOW_SEARCH_NUMBER)
    show_search = num == view_const.SHOW_SEARCH_NUMBER   
    view = FollowByAccountView()
    limited = FollowCampaignProcessor().isAddLimited()
    keyword = request.GET.get('query', '')
    sortBy = 'nameLower'
    directType = 'asc'
    paginate_by = request.GET.get('paginate_by', view_const.DEFAULT_INITIAL_PAGE_SIZE)
    try:
        paginate_by = int(paginate_by)
    except:
        paginate_by = view_const.DEFAULT_INITIAL_PAGE_SIZE
    ret_url = 'fe/follow/account/?query=' + keyword
    showInfo = 0
    if not keyword:    
        objects = FollowCampaignProcessor().query_base().order(('-' if directType == 'desc' else '') + sortBy)
    else:
        objects = FollowCampaignProcessor().search(keyword, set_ancestor=True)
    page=request.GET.get('page', '1')
    paginate_by=paginate_by
    total_number=len(objects)
    total_pages=total_number/paginate_by+1
    if total_pages<int(page):
        page=total_pages
    show_list_info='True'
    if total_number<5:
        show_list_info='False' 
    params=dict(view=view,form=FollowCampaignSortByForm(), title=view.titleList(),show_list_info=show_list_info,ret_url=ret_url,keyword=keyword,limited=limited,
                show_search=show_search, showInfo=showInfo, current_page=str(page),sortBy=sortBy, directType=directType, paginate_by= paginate_by,post_path='/fe/follow/account/'+'?sortby='+sortBy+'&directType='+directType+'&paginate_by='+str(paginate_by)+'&query='+keyword)    
    return object_list( request, 
                        objects,
                        paginate_by=paginate_by,
                        page=page,
                        extra_context=params,
                        template_name=view.template_path("list.html")
                       )

    
def followacctrule_create(request):
    view = FollowByAccountView()
    channels = TAccountProcessor().query(dict(limit=1))
    if len(channels)==0:
        return render_to_response(view.template_path("create_prerequisite.html"), dict(ruleType='follow',name='Twitter account',location='channel/twitter/login',view=ControllerView()), context_instance=RequestContext(request)) 
    extra_params={}
    if request.method=="GET":
        channel=channels[0]
        extra_params = getExtraParams(channel)
    else:
        create_type = request.GET.get('type', '')
        if create_type == 'safe':
            form=view.create_safe_form_class(request.POST)
            if form.is_valid():
                params=form.cleaned_data.copy()
                params=view.custom_form2api(params)
                rule = form.iapi().create(params)
                rule.state = camp_const.CAMPAIGN_STATE_INIT
                rule.put()
                return HttpResponseRedirect(view.template_path("safelist/?id=%s" % rule.id))
    return view.create(request, view, extra_params=extra_params)


def followacctrule_update(request):
    followByAccountView = FollowByAccountView()
    extra_params={}
    if request.method=="GET":
        rule = db.get(request.GET.get('id'))
        channel = rule.src_channel()
        extra_params = getExtraParams(channel)
    return followByAccountView.update(request, followByAccountView,template_name = "update_form.html", extra_params=extra_params)


def getExtraParams(channel):
    extra_params={}
#    extra_params['accountName']=channel.keyNameStrip()
    return extra_params
    

def followacctrule_delete(request):
    try:
        followByAccountView=FollowByAccountView()
        response = followByAccountView.delete(request)
        return response
    except Exception,ex:
        logging.error('Delete follower rule error:%s' % str(ex))
        return HttpResponse("Exception:"+str(ex))


def followacctrule_detail(request, kid):
    followByAccountView = FollowByAccountView()
    rule = db.get(kid)
    channel = rule.src_channel()
    extra_params = getExtraParams(channel)
    return followByAccountView.detail(request, kid, followByAccountView, extra_params=extra_params)


def followacctrule_activate(request):
    followByAccountView = FollowByAccountView()
    return followByAccountView.activate(request)


def followacctrule_deactivate(request):
    followByAccountView = FollowByAccountView()
    return followByAccountView.deactivate(request)


def parseHourlyKeyname(keyname):
    return datetimeparser.int_hour_2_datetime(int(keyname))


def parseDailyKeyname(keyname):
    return datetimeparser.int_day_2_datetime(int(keyname))


def getChartCounter(rid, chartType, unit):
    rule=db.get(rid)
    parent = FeParentChannel.get_or_insert_by_chid(rule.chid)
    endDate = rule.modifiedTime
    if unit == core_const.TIME_UNIT_HOUR:
        modelClass = ChannelHourlyStats
        hourCount=24*7
        startDate = endDate-timedelta(hours=hourCount-1)
        startDate = max(rule.createdTime,startDate)
        interval = timedelta(hours=1)
    elif unit == core_const.TIME_UNIT_DAY:
        modelClass = ChannelDailyStats
        startDate = rule.createdTime
        interval = timedelta(days=1)  

    firstQuery = modelClass.all().ancestor(parent).filter('createdTime >', startDate).order('createdTime')
    lastQuery  = modelClass.all().ancestor(parent).filter('createdTime <', endDate).order('-createdTime')

    logging.info('First query %d'%firstQuery.count())
    logging.info('Last query %d'%lastQuery.count())
    firstStats = firstQuery.fetch(limit=1)[0]
    lastStats = lastQuery.fetch(limit=1)[0]
    
    if unit == 'hour':
        firstTime = parseHourlyKeyname(firstStats.key().name())
        lastTime  = parseHourlyKeyname(lastStats.key().name())
        logging.info('firstTime %s'%str(firstTime))
        logging.info('lastTime %s'%str(lastTime))
    elif unit == 'day':
        firstTime = parseDailyKeyname(firstStats.key().name())
        lastTime  = parseDailyKeyname(lastStats.key().name())
    
    statsTime=firstTime
    all_counters=[]
    if chartType == 'follower':
        currentFollower=0
        counters=[]
        while statsTime <=lastTime:
            stats = modelClass.get_or_insert_by_parent_and_datetime(parent, t=statsTime)
            if stats is None or stats.totalFollowerCount is None or stats.totalFollowerCount==0:
                counters.append(currentFollower)
            else:
                counters.append(stats.totalFollowerCount)
                currentFollower=stats.totalFollowerCount
            statsTime += interval
        all_counters.append(counters)
    elif chartType == 'follow':
        counters_f=[]
        counters_uf=[]
        while statsTime <=lastTime:
            stats = modelClass.get_or_insert_by_parent_and_datetime(parent, t=statsTime)
            if stats is None or stats.followCount is None:
                counters_f.append(0)
            else:
                counters_f.append(stats.followCount) 
            if stats is None or stats.unfollowCount is None:
                counters_uf.append(0)
            else:
                counters_uf.append(stats.unfollowCount)             
            statsTime += interval
        all_counters.append(counters_f)
        all_counters.append(counters_uf)
    elif chartType == 'both'  :
        counters_f=[]
        counters_uf=[]
        while statsTime <=lastTime:
            stats = modelClass.get_or_insert_by_parent_and_datetime(parent, t=statsTime)
            if stats is None or stats.followCount is None:
                counters_f.append(0)
            else:
                counters_f.append(stats.followCount) 
            if stats is None or stats.newFollowerCount is None:
                counters_uf.append(0)
            else:
                counters_uf.append(stats.newFollowerCount)             
            statsTime += interval
        all_counters.append(counters_f)
        all_counters.append(counters_uf)

    chartstart = datetime(year=firstTime.year,month=firstTime.month,day=firstTime.day,hour=firstTime.hour)
    chartend   = datetime(year=lastTime.year,month=lastTime.month,day=lastTime.day,hour=lastTime.hour)
    
    return all_counters,chartstart,chartend


def has_follow_chart(rid, chartType, unit):
    rule=db.get(rid)
    parent = FeParentChannel.get_or_insert_by_chid(rule.chid)
    endDate = rule.modifiedTime
    if unit == core_const.TIME_UNIT_HOUR:
        modelClass = ChannelHourlyStats
        hourCount=24*7
        startDate = endDate-timedelta(hours=hourCount-1)
        startDate = max(rule.createdTime,startDate)
        interval = timedelta(hours=1)
    elif unit == core_const.TIME_UNIT_DAY:
        modelClass = ChannelDailyStats
        startDate = rule.createdTime
        interval = timedelta(days=1)  
    
    firstQuery = modelClass.all().ancestor(parent).filter('createdTime >', startDate).order('createdTime')
    lastQuery  = modelClass.all().ancestor(parent).filter('createdTime <', endDate).order('-createdTime')

    if firstQuery.count(1000) == 0 or lastQuery.count(1000) == 0:
        return False
    else:
        firstStats = firstQuery.fetch(limit=1)[0]
        lastStats = lastQuery.fetch(limit=1)[0]
    
    if unit == core_const.TIME_UNIT_HOUR:
        firstTime = parseHourlyKeyname(firstStats.key().name())
        lastTime  = parseHourlyKeyname(lastStats.key().name())
    elif unit == core_const.TIME_UNIT_DAY:
        firstTime = parseDailyKeyname(firstStats.key().name())
        lastTime  = parseDailyKeyname(lastStats.key().name())
    
    statsTime=firstTime
    all_counters=[]
    if chartType == 'follower':
        currentFollower=0
        counters=[]
        while statsTime <=lastTime:
            stats = modelClass.get_or_insert_by_parent_and_datetime(parent, t=statsTime)
            if stats is None or stats.totalFollowerCount is None or stats.totalFollowerCount==0:
                counters.append(currentFollower)
            else:
                counters.append(stats.totalFollowerCount)
                currentFollower=stats.totalFollowerCount
            statsTime += interval
            break
        all_counters.append(counters)
    elif chartType == 'follow':
        counters_f=[]
        counters_uf=[]
        while statsTime <=lastTime:
            stats = modelClass.get_or_insert_by_parent_and_datetime(parent, t=statsTime)
            if stats is None or stats.followCount is None:
                counters_f.append(0)
            else:
                counters_f.append(stats.followCount) 
            if stats is None or stats.unfollowCount is None:
                counters_uf.append(0)
            else:
                counters_uf.append(stats.unfollowCount)             
            statsTime += interval
            break
        all_counters.append(counters_f)
        all_counters.append(counters_uf)
    elif chartType == 'both'  :
        counters_f=[]
        counters_uf=[]
        while statsTime <= lastTime:
            stats = modelClass.get_or_insert_by_parent_and_datetime(parent, t=statsTime)
            if stats is None or stats.followCount is None:
                counters_f.append(0)
            else:
                counters_f.append(stats.followCount) 
            if stats is None or stats.newFollowerCount is None:
                counters_uf.append(0)
            else:
                counters_uf.append(stats.newFollowerCount)             
            statsTime += interval
            break
        all_counters.append(counters_f)
        all_counters.append(counters_uf)
    return len(all_counters[0]) > 0


def followacctrule_chartdata(request):
    info = request.GET.get('info','')
    infos= info.split(DELIMITER)
    rid = infos[0]
    infoType = infos[1]
    chartType = infos[2]
    all_counters,startTime,endTime = getChartCounter(rid, chartType, infoType)
    counter = all_counters[0]
    if len(all_counters) == 2:
        extraCounter = all_counters[1]
    else:
        extraCounter = None    
    timeunit = infoType
    units = len(counter)
    extra_info=None 
    if chartType=='follower':
        extra_info=None
    elif chartType=='follow':
        extra_info=['follow','unfollow']
    elif chartType=='both':
        extra_info=['follow','follower'] 
    data = getCounterChart(counter,timeunit,units,startTime,endTime,extraCounter=extraCounter,extraInfo=extra_info,isClick=False,count_type='follower_rule',dot_title='Count')
    return HttpResponse(data)


def followacctrule_chartdetail(request):
    view = FollowByAccountView()
    rid = request.POST.get('id','')
    infoType = request.POST.get('infoType','')
    chartType = request.POST.get('chartType','')
    infoTypes = INFO_TYPES
    info = "%s%s%s%s%s" % (rid, DELIMITER, infoType, DELIMITER, chartType)
    hasChart = has_follow_chart(rid, chartType, infoType)
    return render_to_response(view.template_path("chart.html"),
                              dict(info=info,
                                   ipad=False,
                                   hasChart=hasChart,
                                   infoType=infoType,
                                   infoTypes=infoTypes,
                                   ), 
                              context_instance=RequestContext(request));


def followacctrule_chart(request):
    view = FollowByAccountView()
    rid = request.GET.get('id', '')
    rule = db_core.normalize_2_model(rid)
    infoType = INFO_TYPES[0][0]
    form = FollowCampaignChartForm()
    if users.is_current_user_admin():
        hideform=False
    else:
        hideform=True
    return render_to_response(view.template_path("chart_list.html"),
                              dict(
                                infoType=infoType,
                                id=rid,
                                name=rule.name,
                                form=form,
                                infoTypes=INFO_TYPES,
                                hideform=hideform,
                                view=ControllerView()
                                ), 
                              context_instance=RequestContext(request));
                                                                    
                                                                    
def sourceAccountCheck(request):
    data = json.dumps(dict(result="pass"), indent=4)
    return HttpResponse(data, mimetype='application/json') 
                

def sourceAccountSafeList(request):
    view = FollowView()
    rid = request.GET.get('id')
    rule=db.get(rid)
    tapi = rule.getTwitterApi()
    lists = tapi.lists.list(user_id=rule.chid)
    logging.info("Get %d lists for account %s" % (len(lists), rule.src_channel_name()))
    title = 'Safelist for Twitter account: %s' % rule.src_channel_name()
    params = dict(view=ControllerView(), title=title, chid = rule.chid, id=rid, state=rule.state)
    parent = FeParentChannel.get_or_insert_by_chid(rule.chid)
    safeList = SafeFriendSet.get_or_insert_by_parent(parent=parent)
    listIds = safeList.listIds
    for obj in lists:
        user_id =  str(obj['id'])
        if user_id in listIds:
            obj['status']='Included'  
        else:
            obj['status']='Excluded'
    return object_list( request, 
                        lists,
                        paginate_by = view_const.DEFAULT_INITIAL_PAGE_SIZE,
                        extra_context = params,
                        template_name = view.template_path("safelist.html"),
                       )


def sourceAccountSafeListChange(request):
    action = request.GET.get('action')
    listId = request.GET.get('id')
    chid = request.GET.get('chid')
    parent = FeParentChannel.get_or_insert_by_chid(chid)
    safeList = SafeFriendSet.get_or_insert_by_parent(parent=parent)
    listIds = safeList.listIds
    if len(listIds) >= 3 and action == 'Include':
        result = 'limit'
    elif action == 'Include':
        safeList.listIds.append(listId)
        safeList.put()
        result = 'Included'
    elif action == 'Exclude':
        safeList.listIds.remove(listId)
        safeList.put()
        result = 'Excluded'
    
    data = json.dumps(dict(result=result), indent=4)
    return HttpResponse(data, mimetype='application/javascript')


def sourceAccountSafeListHelp(request):
    view = FollowView()
    return render_to_response(view.template_path("safelist_help.html"), context_instance=RequestContext(request))


class AllFollowCampaignsView(FollowByAccountView):
    def __init__(self):
        FollowByAccountView.__init__(self)
        self.api_module_name = 'follow/all'

    def titleList(self):
        return "All Follow Campaigns"


class AllSuspendedFollowCampaignsView(FollowByAccountView):
    def __init__(self):
        FollowByAccountView.__init__(self)
        self.api_module_name = 'follow'

    def titleList(self):
        return "All Suspended Follow Campaigns"


def all_rule_list(request):
    show_search= True
    view = AllFollowCampaignsView()
    keyword=request.GET.get('query', '')
    sortBy = 'state'
    directType = 'asc'
    paginate_by = request.GET.get('paginate_by', view_const.DEFAULT_INITIAL_PAGE_SIZE)
    try:
        paginate_by = int(paginate_by)
    except:
        paginate_by = view_const.DEFAULT_INITIAL_PAGE_SIZE
    ret_url='fe/follow/all/rule/list/?query='+keyword
    if not keyword or keyword == '':    
        objects = FollowCampaignProcessor().query_base(set_ancestor=False).order(('-' if directType == 'desc' else '')+sortBy)
    else:
        objects = FollowCampaign.search_index.search(keyword)
    page=request.GET.get('page','1')
    paginate_by=paginate_by
    total_number=len(objects)
    total_pages=total_number/paginate_by+1
    if total_pages<int(page):
        page=total_pages
    show_list_info='True'
    if total_number<5:
        show_list_info='False' 
    form = AllFollowCampaignSortByForm()
    params=dict(view=view,form=form, title=view.titleList(),show_list_info=show_list_info,ret_url=ret_url,keyword=keyword,
                show_search=show_search, current_page=str(page),sortBy=sortBy, directType=directType, paginate_by= paginate_by,post_path='/fe/follow/all/rule/list/'+'?sortby='+sortBy+'&directType='+directType+'&paginate_by='+str(paginate_by)+'&query='+keyword)    
    return object_list( request, 
                        objects,
                        paginate_by=paginate_by,
                        page=page,
                        extra_context=params,
                        template_name=view.template_path("list.html")
                       )
    

def suspended_followrule(request):
    view = AllSuspendedFollowCampaignsView()
    rules = FollowCampaignProcessor().query_base(set_ancestor=False).filter('state', camp_const.CAMPAIGN_STATE_SUSPENDED).order('-suspendedTime')
    post_path = '/fe/follow/suspend/rule/list/?paginate_by=20'
    params = dict(view=view, title=view.titleList(), post_path=post_path)
    return object_list( request, 
                        rules,
                        paginate_by=20,
                        extra_context=params,
                        template_name=view.template_path("suspended_list.html"),
                       )
    

def followacctrule_admin_delete(request):
    return followacctrule_delete(request)
    
    
def update_channel_status(request):
    try:
        rid = int(request.REQUEST.get('rid'))
        status = int(request.REQUEST.get('status'))
        userEmail = request.REQUEST.get('user')
        user = db_core.User.get_by_key_name(db_core.User.keyName(userEmail))
        rule = FollowCampaign.get_by_id(rid, parent=user)
        channel = rule.src_channel()
        rule.deleted = False
        channel.deleted = False
        if status==channel_const.CHANNEL_STATE_SUSPENDED:
            channel.suspend()
            rule.state = camp_const.CAMPAIGN_STATE_SUSPENDED
        elif status==channel_const.CHANNEL_STATE_NORMAL:
            channel.restore()
            rule.state = camp_const.CAMPAIGN_STATE_ACTIVATED
        else:
            return HttpResponse('Failed')  
        db.put([channel, rule])
        return HttpResponse('Succeeded')  
    except:
        logging.exception("Error when updating channel status:")
        return HttpResponse('Failed')  


def reactivate_protected(request):
    return _reactivate_all(request, camp_const.CAMPAIGN_STATE_ONHOLD)


def reactivate_suspended(request):
    return _reactivate_all(request, camp_const.CAMPAIGN_STATE_SUSPENDED)


def _reactivate_all(request, state):
    utcnow = datetime.utcnow()
    rules = FollowCampaignProcessor().query_base(set_ancestor=False).filter('state', state).filter('scheduleNext < ', utcnow).order('scheduleNext')
    count = 0
    failed = 0
    for rule in rules:
        try:
            FollowCampaignProcessor().activate(rule)
            count += 1
        except:
            logging.exception("Failed re-activating " % rule.basic_info())
            failed += 1
    return HttpResponse("Reactivated %d campaigns with %d failures, out of total %d." % (count, failed, len(rules)))  


def config_main(request):
    view = FollowView()
    config = Config.get_config()
    if config.skip_stats:
        statsMsg = 'Inactive'
        statsAction = 'Resume Follow Stats'
    else:
        statsMsg = 'Active'
        statsAction = 'Stop Follow Stats'
    if config.manually_stopped:
        followMsg = 'Stopped'
        followAction = 'Resume Follow Cron'
    else:
        followMsg = 'Active'
        followAction = 'Stop Follow Cron'
    form_p = {}
    form_p['stop_on_suspension'] = config.stop_on_suspension
    form_p['stop_in_weekend'] = config.stop_in_weekend
    form = SystemSettingsForm(initial=form_p)
    return render_to_response(view.template_path("system_settings.html"),
                              dict(view = view,
                                   config = config,
                                   statsMsg = statsMsg,
                                   statsAction = statsAction,
                                   followMsg = followMsg,
                                   followAction = followAction,
                                   title = 'System Settings',
                                   form = form, 
                                   ), 
                              context_instance=RequestContext(request))


def config_toggle(request):
    config = Config.get_config()
    attr = request.REQUEST.get('attr')
    old_value = getattr(config, attr)
    new_value = not old_value
    setattr(config, attr, new_value)
    if attr == 'manually_stopped':
        config.suspension_detected = False
        config.msg = None
    Config.set_config(config)
    return HttpResponse(str(new_value))  


def config_update(request):
    view = FollowView()
    config = Config.get_config()
    if request.method =='GET':
        attr = request.GET.get('attr')
        value = getattr(config, attr)
        return render_to_response(view.template_path("count.html"), dict(attr=attr, begin_hour=config.begin_hour, hours=config.hours, value=value), context_instance=RequestContext(request))
    elif request.method =='POST':
        attr = request.POST.get('attr')
        if attr == 'begin_hour':
            config.begin_hour = int(request.POST.get('begin_hour'))
            config.hours = int(request.POST.get('hours'))
        else:
            value = int(request.POST.get('value'))
            setattr(config, attr, value)
        Config.set_config(config)
        return HttpResponse('ok')


def config_reset(request):
    Config.reset_config()
    return HttpResponse('ok')  


