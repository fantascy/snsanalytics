import csv
import StringIO
import urllib2
import urllib
import deploysoup
import datetime
import json
import logging

from google.appengine.api import users
from google.appengine.ext import db
from django.views.generic.list_detail import object_list
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.http import HttpResponseRedirect, HttpResponse, HttpResponseBadRequest
from twitter.api import TwitterApi

import context
from common.utils import string as str_util
from common.utils import timezone as ctz_util
from common.utils import twitter as twitter_util
from common.content import feedfetcher
from common.content.trove import consts as trove_const
from sns.serverutils import memcache, deferred
from sns.api import errors as api_error
from sns.core import core as db_core
from sns.chan import consts as channel_const
from sns.camp import consts as camp_const
from sns.cont import consts as cont_const
from sns.log import consts as log_const
from sns.chan.models import TAccount
from sns.post.models import FCampaign, SPost
from sns.log.api import getPatternValue
from sns.log.models import BlackList, Agent, CmpTwitterAcctStats, CmpTwitterAcctStatsCounter, GlobalStats, TopicStats, ContentSourceDailyStats
from sns.log.api import CmpTwitterAcctStatsProcessor, getBlackList, BlackListProcessor, getAgentIpList
from sns.log.globalstatsapi import GlobalStatsProcessor
from common.view import utils as view_util
from sns.view import consts as view_const
from sns.view.controllerview import ControllerView
from sns.log.forms import BlackListForm, DemoUserForm, GlobalStatsForm, CmpTwitterAcctStatsForm,\
    ChannelFollowStatsForm, TwitterUploadForm, ContentSourceDailyStatsForm


BOT_TYPES = [
     (log_const.PATTERN_FULL_NAME,'Full Name'),
     (log_const.PATTERN_KEY_WORD,'Key Word'),
     (log_const.PATTERN_IP_LIST,'Ip List'),    
     (log_const.PATTERN_USER_LIST,'User List'),  
     (log_const.PATTERN_DEMO_LIST,'Demo List'),    
     (log_const.PATTERN_GA_LIST,'GA List'),     
     (log_const.PATTERN_DOS_LIST,'DOS List'),  
     (log_const.PATTERN_AD_SITE,'Ads Blacklist'),  
     (log_const.PATTERN_FRAME_SITE,'IFRAME Blacklist'),          
              ]


def blacklist_list(request):
    if not users.is_current_user_admin():  
        raise api_error.ApiError(api_error.API_ERROR_ADMIN_PAGE)
        
    botType = request.REQUEST.get("botType", BOT_TYPES[0][0])
    ret_html="sns/log/black_list.html"
    if botType==log_const.PATTERN_GA_LIST:
        ret_html="sns/log/ga_black_list.html"
    elif botType==log_const.PATTERN_DOS_LIST:
        ret_html="sns/log/dos_black_list.html"
    elif botType==log_const.PATTERN_AD_SITE:
        ret_html="sns/log/adsite_black_list.html"
    elif botType==log_const.PATTERN_FRAME_SITE:
        ret_html="sns/log/framesite_black_list.html"
    elif botType == log_const.PATTERN_REDIRECT_USER:
        ret_html="sns/log/redirect_user_list.html"
    return render_to_response(ret_html,dict(botTypes=BOT_TYPES,botType=botType,view=ControllerView()), context_instance=RequestContext(request));
    

def blacklist_table(request):
    ltype = request.REQUEST.get("type")
    object_list=getPatternValue(ltype)
    return render_to_response("sns/log/black_table.html",dict(object_list=object_list, type=ltype, paginate_by=10,), context_instance=RequestContext(request));
    

class BlackListView:
    
    def __init__(self):
        self.update_form=BlackListForm
        
    def add(self, request, blacklist_type):
        if not users.is_current_user_admin(): 
            raise api_error.ApiError(api_error.API_ERROR_ADMIN_PAGE)
        if request.method=="GET":
            form=self.update_form()
            return render_to_response("sns/log/black_form.html",dict(form=form), context_instance=RequestContext(request,{"path":request.path}));
        elif request.method=='POST':
            form=self.update_form(request.POST)
            values=form.data['patternValue'].split()
            blacklist=getBlackList(blacklist_type)
            for value in values:
                if blacklist_type==log_const.PATTERN_GA_LIST or blacklist_type==log_const.PATTERN_DOS_LIST or blacklist_type==log_const.PATTERN_AD_SITE:
                    value = value.lower()
                if not value in blacklist:
                    blacklist.append(value)
            patternValue=str(blacklist)
            params = {
                    'id':BlackList.get_by_key_name(BlackList.keyName(blacklist_type)).id, 
                    'patternValue':patternValue,
                }
            BlackListProcessor().update(params)
            memcache.delete(BlackList.keyName(blacklist_type))
            if blacklist_type==log_const.PATTERN_GA_LIST or blacklist_type==log_const.PATTERN_DOS_LIST or blacklist_type==log_const.PATTERN_AD_SITE:
                return HttpResponseRedirect('/log/blacklist/table?botType='+blacklist_type)
            return HttpResponseRedirect('/log/blacklist?botType='+blacklist_type)
    
    def delete(self, request, blacklist_type):
        if not users.is_current_user_admin(): 
            raise api_error.ApiError(api_error.API_ERROR_ADMIN_PAGE)
        obj = request.GET.get('obj')
        blacklist=getBlackList(blacklist_type)
        blacklist.remove(obj)
        patternValue=str(blacklist)
        params={'id':BlackList.get_by_key_name(BlackList.keyName(blacklist_type)).id, 'patternValue':patternValue}
        BlackListProcessor().update(params)
        memcache.delete(BlackList.keyName(blacklist_type))
        return HttpResponseRedirect('/log/blacklist?botType='+blacklist_type)
           

blackListView=BlackListView()

def fullname_add(request):
    return blackListView.add(request,type=log_const.PATTERN_FULL_NAME)

def keyword_add(request):
    return blackListView.add(request,type=log_const.PATTERN_KEY_WORD)

def iplist_add(request):
    return blackListView.add(request,type=log_const.PATTERN_IP_LIST)

def user_add(request):
    return blackListView.add(request,type=log_const.PATTERN_USER_LIST)

def demo_add(request):
    return blackListView.add(request,type=log_const.PATTERN_DEMO_LIST)

def ga_add(request):
    return blackListView.add(request,type=log_const.PATTERN_GA_LIST)

def dos_add(request):
    return blackListView.add(request,type=log_const.PATTERN_DOS_LIST)

def adsite_add(request):
    return blackListView.add(request,type=log_const.PATTERN_AD_SITE)

def framesite_add(request):
    return blackListView.add(request,type=log_const.PATTERN_FRAME_SITE)

def redirect_user_add(request):
    return blackListView.add(request,type=log_const.PATTERN_REDIRECT_USER)

def adsite_export(request): 
    data = '' 
    object_list=getBlackList(log_const.PATTERN_AD_SITE) 
    for obj in object_list: 
        data += obj + ' ' 
    return render_to_response("sns/log/export.html",dict(data=data), context_instance=RequestContext(request,{"path":request.path}));
 
def framesite_export(request): 
    data = '' 
    object_list=getBlackList(log_const.PATTERN_FRAME_SITE) 
    for obj in object_list: 
        data += obj + ' ' 
    return render_to_response("sns/log/export.html",dict(data=data), context_instance=RequestContext(request,{"path":request.path}));

def fullname_delete(request):
    try:
        response = blackListView.delete(request, type=log_const.PATTERN_FULL_NAME)
        return response
    except Exception,ex:
        logging.error('Delete bot fullname list error:%s' % str(ex))
        return HttpResponse("Exception:"+str(ex))

def keyword_delete(request):
    try:
        response = blackListView.delete(request, type=log_const.PATTERN_KEY_WORD)
        return response
    except Exception,ex:
        logging.error('Delete bot keyword list error:%s' % str(ex))
        return HttpResponse("Exception:"+str(ex))

def iplist_delete(request):
    try:
        response = blackListView.delete(request, type=log_const.PATTERN_IP_LIST)
        return response
    except Exception,ex:
        logging.error('Delete bot ip list error:%s' % str(ex))
        return HttpResponse("Exception:"+str(ex))

def user_delete(request):
    try:
        response = blackListView.delete(request, type=log_const.PATTERN_USER_LIST)
        return response
    except Exception,ex:
        logging.error('Delete bot user list error:%s' % str(ex))
        return HttpResponse("Exception:"+str(ex))

def demo_delete(request):
    try:
        response = blackListView.delete(request, type=log_const.PATTERN_DEMO_LIST)
        return response
    except Exception,ex:
        logging.error('Delete bot demo list error:%s' % str(ex))
        return HttpResponse("Exception:"+str(ex))
    
def ga_delete(request):
    try:
        response = blackListView.delete(request, type=log_const.PATTERN_GA_LIST)
        return response
    except Exception,ex:
        logging.error('Delete ga blacklist error:%s' % str(ex))
        return HttpResponse("Exception:"+str(ex))
    
def dos_delete(request):
    try:
        response = blackListView.delete(request, type=log_const.PATTERN_DOS_LIST)
        return response
    except Exception,ex:
        logging.error('Delete dos blacklist error:%s' % str(ex))
        return HttpResponse("Exception:"+str(ex))
    
def adsite_delete(request):
    try:
        response = blackListView.delete(request, type=log_const.PATTERN_AD_SITE)
        return response
    except Exception,ex:
        logging.error('Delete adsite blacklist error:%s' % str(ex))
        return HttpResponse("Exception:"+str(ex))

def framesite_delete(request):
    try:
        response = blackListView.delete(request, type=log_const.PATTERN_FRAME_SITE)
        return response
    except Exception,ex:
        logging.error('Delete adsite blacklist error:%s' % str(ex))
        return HttpResponse("Exception:"+str(ex))

def redirect_user_delete(request):
    try:
        response = blackListView.delete(request, type=log_const.PATTERN_REDIRECT_USER)
        return response
    except Exception,ex:
        logging.error('Delete adsite blacklist error:%s' % str(ex))
        return HttpResponse("Exception:"+str(ex))

  
def agent_list(request):   
    if not users.is_current_user_admin():  
        raise api_error.ApiError(api_error.API_ERROR_ADMIN_PAGE)
    
    objects=Agent.all().order('-modifiedTime').fetch(limit=1000)
    params={'view':ControllerView(),'title':'Agents List'}
    
    #return render_to_response("sns/log/agent_list.html",dict(object_list=object_list,view=ControllerView()), context_instance=RequestContext(request));
    return object_list( request, 
                            objects,
                            paginate_by=view_const.DEFAULT_INITIAL_PAGE_SIZE,
                            extra_context = params,
                            template_name="sns/log/agent_list.html"
                           )

def agent_delete(request):
    try:
        name = request.GET.get('name')
        agent=Agent.get_by_key_name(Agent.keyName(name))
        agent.delete()
        return HttpResponse('Success')
    except Exception,ex:
        logging.error('Delete bot agent list error:%s' % str(ex))
        return HttpResponse("Exception:"+str(ex))

def agent_update(request):
    name = request.GET.get('name')
    agent_type = request.GET.get('type')
    agent=Agent.get_by_key_name(Agent.keyName(name))
    valueList=getBlackList(agent_type)
    changed=False
    if agent_type==log_const.PATTERN_FULL_NAME:
        value = agent.keyNameStrip()
        if value in valueList:
            pass
        else:
            changed=True
            valueList.append(value)
    elif agent_type==log_const.PATTERN_IP_LIST:
        values = getAgentIpList(name)
        for value in values:
            if value in valueList:
                pass
            else:
                changed=True
                valueList.append(value)
                  
    if changed:
        patternValue=str(valueList)
        params={'id':BlackList.get_by_key_name(BlackList.keyName(agent_type)).id, 'patternValue':patternValue}
        BlackListProcessor().update(params)
        memcache.delete(BlackList.keyName(agent_type))
        return HttpResponseRedirect('/log/agent')
        
def dataModify(request):
    if not users.is_current_user_admin():  
        raise api_error.ApiError(api_error.API_ERROR_ADMIN_PAGE)
    names = ['Twitter / CNNInternatDesk','ADHD Feeds Non-Filtered','Cholesterol Filtered','Cholesterol Unfiltered',
             'Frisky Feed',"WJZ - Baltimore, Maryland's Breaking News, Weather & Sports Station0.572446786123"]
    for name in names :
        rules = FCampaign.all().filter('name =',name).fetch(limit=1)
        if len(rules) == 1:
            rule = rules[0]
            rule.state = camp_const.CAMPAIGN_STATE_EXECUTING
            rule.put()
            logging.info('Date modify for rule %s'%name)
    return HttpResponse('OK', mimetype='application/javascript')

def demoUser(request):
    form = DemoUserForm()
    return render_to_response("sns/log/demo_form.html",dict(form=form), context_instance=RequestContext(request)); 

def systemSetting(request):
    builderMonitor = db_core.SystemStatusMonitor.get_system_monitor(cont_const.MONITOR_FEED_BUILDER_SWITCH)
    videoMonitor = db_core.SystemStatusMonitor.get_system_monitor(cont_const.MONITOR_SOUP_VIDEO_REDIRECT)
    imgMonitor = db_core.SystemStatusMonitor.get_system_monitor(cont_const.MONITOR_SOUP_IMG_REDIRECT)
    googleMonitor = db_core.SystemStatusMonitor.get_system_monitor(cont_const.MONITOR_GOOGLE_FEED_SWITCH)
    bingMonitor = db_core.SystemStatusMonitor.get_system_monitor(cont_const.MONITOR_BING_FEED_SWITCH)
    instagramMonitor = db_core.SystemStatusMonitor.get_system_monitor(cont_const.MONITOR_INSTAGRAM_FETCH)
    return render_to_response("sns/log/system.html",dict(view=ControllerView(),title = 'System Settings',builderMonitor=builderMonitor,instagramMonitor=instagramMonitor,
                                videoMonitor=videoMonitor, imgMonitor=imgMonitor, googleMonitor=googleMonitor, bingMonitor=bingMonitor ), context_instance=RequestContext(request));
                                                
def redirectMonitorChange(request):
    monitor_type = request.GET.get('type',None)
    if monitor_type == 'video':
        keyname = cont_const.MONITOR_SOUP_VIDEO_REDIRECT
    elif monitor_type == 'img':
        keyname = cont_const.MONITOR_SOUP_IMG_REDIRECT
    elif monitor_type == 'builder':
        keyname = cont_const.MONITOR_FEED_BUILDER_SWITCH
    elif monitor_type == 'google':
        keyname = cont_const.MONITOR_GOOGLE_FEED_SWITCH
    elif monitor_type == 'bing':
        keyname = cont_const.MONITOR_BING_FEED_SWITCH
    elif monitor_type == 'instagram':
        keyname = cont_const.MONITOR_INSTAGRAM_FETCH
    else:
        logging.error('unknown monitor type!')
        return HttpResponse('fail')
    monitor = db_core.SystemStatusMonitor.get_system_monitor(keyname)
    count = request.GET.get('count',None)
    if count == None:
        if monitor.work:
            monitor.work = False
        else:
            monitor.work = True
            if monitor_type == 'google' or monitor_type == 'bing':
                for userHashCode in range(0, db_core.User.USER_HASH_SIZE):
                    deferred.defer(resumeErrorRules, monitor_type, userHashCode)
        info = str(monitor.work)
    else:
        try:
            monitor.count = int(count)
        except:
            pass
        info = str(count)
    monitor.put()
    memcache.delete(keyname)
    return HttpResponse(info)   

def resumeErrorRules(rule_type, userHashCode):
    filterTime = datetime.datetime(year=1800,month=1,day=1)
    logging.info('Resume rules!')
    while True:
        rules = FCampaign.all().filter('deleted',False).filter('state', camp_const.CAMPAIGN_STATE_ERROR).filter('userHashCode',userHashCode).filter('scheduleNext > ', filterTime).order('scheduleNext')
        if len(rules) == 0:
            break
        for rule in rules:
            try:
                resume = False
                for fid in rule.contents:
                    feed = db.get(fid)
                    if rule_type == 'google' and feedfetcher.is_googlenews_feed(feed.url):
                        resume = True
                    elif rule_type == 'bing' and feedfetcher.is_bing_feed(feed.url) :
                        resume = True
                if resume:
                    rule.state = camp_const.CAMPAIGN_STATE_ACTIVATED
                    rule.put()
                    logging.info('Resume rule %s'%rule.name)
                filterTime = rule.scheduleNext
            except Exception:
                logging.exception('Unexpected error when resume rule %s'%rule.name)
            

def urlfetchTest(request):
    url = request.POST.get('url')
    urllib2.urlopen(url)
    return HttpResponse("Finished urllib2.urlopen(url) for %s" % url)  


def realtimePost(request):
    appid = deploysoup.FACEBOOK_OAUTH_MAP[context.get_context().application_id()]['id']
    token = deploysoup.FACEBOOK_OAUTH_MAP[context.get_context().application_id()]['access_token']
    params = {}
    params['object'] = 'user'
    params['callback_url'] = 'http://' + deploysoup.DOMAIN_MAP[context.get_context().application_id()] + '/brew/facebook/realtime/'
    params['fields'] = "name,email,location,friends,link"
    params['verify_token'] = log_const.FACEBOOK_REAL_TIME_VERIFY_TOKEN
    url = 'https://graph.facebook.com/%s/subscriptions?access_token=%s' %(appid,token)
    data = urllib.urlopen(url,  data=urllib.urlencode(params)).read()
    return HttpResponse(data) 


STATS_CHART_TIME_RANGE = 30


def _get_chart_data_for_stats(statsDate, statsCounts):
    counts = statsCounts[-STATS_CHART_TIME_RANGE:]
    counts = [count if count else 0 for count in counts]
    labels = []
    tips = []
    for i in range(0, len(counts)):
        date = statsDate - datetime.timedelta(days=len(counts)-i-1)
        labels.append(str(date.month)+'.'+str(date.day))
        tips.append(str(counts[i])+'--'+str(labels[i]))
    return counts, labels, tips


def _get_chart_data_for_global_stats(statsType):
    if statsType==log_const.GLOBAL_STATS_COMPARISON:
        return [], [], []
    stats = GlobalStats.get_or_insert_by_id(statsType)
    statsDate, statsCounts = stats.get_counter_info()
    if statsCounts is None:
        statsCounts = []
    if statsType in (log_const.GLOBAL_STATS_KLOUT_SCORE_100TH, log_const.GLOBAL_STATS_KLOUT_SCORE_1000TH):
        statsCounts = CmpTwitterAcctStatsCounter.real_klout_scores(statsCounts)
    return _get_chart_data_for_stats(statsDate, statsCounts)


class GlobalStatsChartView(ControllerView):
    pass

def global_stats_chart(request):
    statsType = int(request.GET.get('type', 0))
    if statsType != -1:
        counts, labels, tips = _get_chart_data_for_global_stats(statsType)
    else:
        counts = []
        labels = []
        tips = []
        for t in list(log_const.GLOBAL_STATS_DISPLAY_LIST)[:-1]:
            fcounts, flabels, ftips = _get_chart_data_for_global_stats(t)
            counts.append(fcounts)
            labels.append(flabels)
            tips.append(ftips)
    form = GlobalStatsForm(initial={'type':statsType})
    return render_to_response("sns/log/stats.html",dict(view=ControllerView(),counts=counts,labels=labels,tips=tips,form=form,type=statsType), context_instance=RequestContext(request))


class ChannelStatsListView(ControllerView):
    def lst(self, request):
        orderBy = request.REQUEST.get("orderby", "")
        orderType = request.REQUEST.get("type", "")
        pageSize = request.REQUEST.get("paginate_by")
        keyword = request.REQUEST.get("keyword", "")
        if pageSize is None or pageSize == "":
            pageSize = view_const.DEFAULT_INITIAL_PAGE_SIZE
        else:
            pageSize = int(pageSize)
        if keyword is not None and keyword != "":
            query = CmpTwitterAcctStats.searchIndex.search(keyword)
        else:
            query = CmpTwitterAcctStats.all()
            fields = ("latelyPost", "latelyClick", "latelyFollower", "latestKloutScore", "searchRank",  
                      'retweets', 'mentions', 'hashtags', 
                      "totalPost", "totalClick", 'totalRetweets', 'totalMentions', 'totalHashtags')
            for field in fields:
                if orderBy == field.lower():
                    if field=='searchRank':
                        query.filter('searchRank > ', 0)
                    if orderType == "asc":
                        query = query.order(field)
                    if orderType == "desc":
                        query = query.order("-" + field)
        post_path = self.path() + "?orderby=" + str(orderBy) + "&type=" + str(orderType) + "&paginate_by=" + str(pageSize) + "&keyword=" + str(keyword)
        return object_list(request,
                           query,
                           paginate_by=pageSize,
                           extra_context=dict(view=self, title=self.title(), orderBy=orderBy, orderType=orderType, post_path=post_path, pageSize=pageSize, keyword=keyword),
                           template_name=self.template())


class ChannelStatsListPublishingView(ChannelStatsListView):
    def title(self):
        return "CMP Account Click Stats"

    def template(self):
        return "sns/log/channel_stats_list_publishing.html"
    
    def path(self):
        return "/#/log/channelstats/"


class ChannelStatsListTseoView(ChannelStatsListView):
    def title(self):
        return "CMP Account TSEO Stats"

    def template(self):
        return "sns/log/channel_stats_list_tseo.html"

    def path(self):
        return "/#/log/channelstats/tseo/"


class ChannelStatsListFeView(ChannelStatsListView):
    def title(self):
        return "CMP Account FE Stats"

    def template(self):
        return "sns/log/channel_stats_list_fe.html"

    def path(self):
        return "/#/log/channelstats/fe/"

    def lst(self, request):
        state = int(request.GET.get('state',-1))
        server = request.GET.get('server','all')
        keyword = request.GET.get('query','')
        priority = int(request.GET.get('priority',-1))
        pagination = int(request.GET.get('pagination',20))
        query = CmpTwitterAcctStats.all().order('-feModifiedTime')
        if state != -1:
            query = query.filter('state', state)
        if server != 'all':
            query = query.filter('server', server)
        if state == 0 and priority != -1:
            query = query.filter('priority',priority)
        post_path = self.path() + "?state=" + str(state) + "&server=" + str(server) + "&priority=" + str(priority) + "&pagination=" + str(pagination)
        form = ChannelFollowStatsForm(initial={'state':state,'server':server,'priority':priority,'pagination':pagination})
        if keyword != '':
            query = CmpTwitterAcctStats.searchIndex.search(keyword, filters=('deleted = ', False))
        return object_list(request,
                           query,
                           paginate_by=pagination,
                           extra_context=dict(view=self, title=self.title(), post_path=post_path, form=form, state=state),
                           template_name=self.template())


def channel_stats_list_publishing(request):
    return ChannelStatsListPublishingView().lst(request)


def channel_stats_list_tseo(request):
    return ChannelStatsListTseoView().lst(request)


def channel_stats_list_fe(request):
    return ChannelStatsListFeView().lst(request)
    

def channel_follow_stats_set(request):
    logging.info("Received a follow engine status update request.")
    infos = request.POST.get('infos', '')
    succeeded = True
    try:
        infos = eval(infos)
        if type(infos) != list:
            succeeded = False
    except:
        succeeded = False
    if succeeded:
        deferred.defer(CmpTwitterAcctStatsProcessor.deferred_update_follow_stats, infos)
        return HttpResponse("Updated follow stats for %d accounts." % len(infos))
    else:
        logging.exception("Error when updating follow stats:")
        return HttpResponse("Update follow stats failed!")
    
    
def channel_follow_stats_update(request):
    priority = int(request.REQUEST.get("priority"))
    stats = db.get(request.REQUEST.get("id"))
    stats.priority = priority
    db.put(stats)
    return HttpResponse('OK')


def get_cmp_acct_basic_info(request):
    chids = []
    try:
        chids = GlobalStatsProcessor().get_all_chids()
    except:
        logging.exception("Error when getting complete cmp acct list:")
    return HttpResponse(str(chids))


def get_once_suspended_acct_list(request):
    chids = []
    try:
        chids = GlobalStatsProcessor().get_once_suspended_chids()
    except:
        logging.exception("Error when getting once suspended acct list:")
    return HttpResponse(str(chids))
    

def channel_stats_export_handle_id_map(request):
    try:
        cstats_list = CmpTwitterAcctStatsProcessor().execute_query_all(params={})
        handle_id_map = dict([(cstats.nameLower, cstats.chid) for cstats in cstats_list])
        return HttpResponse(json.dumps(handle_id_map, indent=4))  
    except Exception:
        return HttpResponse("Unexpected error when exporting Twitter account handle ID map!")

    
def channel_stats_export_all(requst):
    return _channel_stats_export()

    
def channel_stats_export_normal(request):
    return _channel_stats_export(channel_state=channel_const.CHANNEL_STATE_NORMAL)

    
def _channel_stats_export(channel_state=None):
    response = view_util.get_csv_response_base("SNS Analytics Twitter Accts")
    writer = csv.writer(response)
    writer.writerow(['ID', 'Handle', 'Created At', 'State', 'Topic', 
                     'User ID', 'User Email', 'Cohort', 'Feed Source', 'FE', 
                     'Followers', 'Clicks - 30D', 'Posts - 30D', ])
    try:
        cmp_users = db_core.User.all().filter('isContent', True).fetch(limit=1000)
        cmp_users_map = dict([(user.uid, user) for user in cmp_users])
        limit = 100
        cursor = None
        count = 0
        query = CmpTwitterAcctStats.all()
        if channel_state is not None:
            query = query.filter('chanState', channel_state)
        while True:
            if cursor:
                query.with_cursor(cursor)
            stats_list = query.fetch(limit=limit)
            count += len(stats_list)
            for stats in stats_list:
                uid = stats.uid
                user = cmp_users_map.get(uid, None)
                row_data = [int(stats.key().name()), stats.name, stats.acctCreatedTime, stats.chanState, str_util.encode_utf8_if_ok(stats.first_topic_name()), 
                            user.uid, user.mail, user.name, user.tags, stats.server, 
                            stats.latelyFollower, stats.totalClick, stats.totalPost,  
                            ]
                writer.writerow(row_data)
            cursor = query.cursor()
            logging.info("Queried total %d CMP acct stats. Current cursor is %s." % (count, cursor))
            if len(stats_list)<limit:
                break
    except Exception, ex:
        return HttpResponse("Unexpected error when exporting: %s" % str(ex), status=500)
    finally:
        logging.info("Completed exporting %d CmpTwitterAcctStats records." % count)
    return response

    
class ChannelStatsChart(ControllerView):
    def title(self):
        return "CMP Twitter Acct Stats Chart"

    def template(self):
        return "sns/log/channel_stats_chart.html"
    
    def path(self):
        return "/#/log/channelstats/"
    
    def chartType(self):
        pass
    
    def comparisonType(self):
        return log_const.CHANNEL_STATS_CHART_COMPARISON

    def attr(self):
        return log_const.CHANNEL_STATS_CHART_ATTR_MAP.get(self.chartType(), None)

    @classmethod
    def get_chart_type_by_attr(cls, attr):
        for t, a in log_const.CHANNEL_STATS_CHART_ATTR_MAP.items():
            if attr==a:
                return t
        return None

    def chart(self, request):
        csid = request.REQUEST.get("id")
        channelStats = db.get(csid)
        counter = channelStats.get_or_insert_counter()
        chid = channelStats.key().name()
        user = db_core.User.get_by_id(channelStats.uid)
        parent = db_core.ChannelParent.get_or_insert_parent(channelStats.uid)
        taccount = TAccount.get_by_key_name(TAccount.keyName(chid), parent)
        if channelStats.updd is None:
            return HttpResponseBadRequest()
        if self.chartType()==log_const.CHANNEL_STATS_CHART_COMPARISON:
            counts, labels, tips = [], [], [] 
            for chartType in log_const.CHANNEL_STATS_CHART_TYPES_NO_COMPARISION:
                attr = log_const.CHANNEL_STATS_CHART_ATTR_MAP[chartType]
                c, l, t = self._get_chart_data_for_channel_stats(counter, attr)
                counts.append(c)
                tips.append(t)
                if len(labels)==0:
                    labels = l
        else:
            counts, labels, tips = self._get_chart_data_for_channel_stats(counter, self.attr())
        form = CmpTwitterAcctStatsForm(initial={'type': self.chartType()})
        return render_to_response(self.template(),
                                  dict(view=self, counts=counts, labels=labels, tips=tips, form=form, id=csid, user=user, channel=taccount), 
                                  context_instance=RequestContext(request),
                                  )

    def _get_chart_data_for_channel_stats(self, counter, attr):
        statsDate, statsCounts = counter.getCounts(attr)
        if statsCounts is None:
            statsCounts = []
        if attr=='kloutScores':
            statsCounts = CmpTwitterAcctStatsCounter.real_klout_scores(statsCounts)
        return _get_chart_data_for_stats(statsDate, statsCounts)


class ChannelStatsChartPosts(ChannelStatsChart):
    def title(self):
        return "CMP Twitter Acct Posts"

    def chartType(self):
        return log_const.CHANNEL_STATS_CHART_POSTS
    

class ChannelStatsChartClicks(ChannelStatsChart):
    def title(self):
        return "CMP Twitter Acct Clicks"

    def chartType(self):
        return log_const.CHANNEL_STATS_CHART_CLICKS


class ChannelStatsChartFollowers(ChannelStatsChart):
    def title(self):
        return "CMP Twitter Acct Followers"

    def chartType(self):
        return log_const.CHANNEL_STATS_CHART_FOLLOWERS


class ChannelStatsChartKloutScores(ChannelStatsChart):
    def title(self):
        return "CMP Twitter Acct Klout Scores"

    def chartType(self):
        return log_const.CHANNEL_STATS_CHART_KLOUT_SCORES


class ChannelStatsChartSearchRanks(ChannelStatsChart):
    def title(self):
        return "CMP Twitter Acct Search Ranks"

    def chartType(self):
        return log_const.CHANNEL_STATS_CHART_SEARCH_RANKS


class ChannelStatsChartRetweets(ChannelStatsChart):
    def title(self):
        return "CMP Twitter Acct Retweets"

    def chartType(self):
        return log_const.CHANNEL_STATS_CHART_RETWEETS


class ChannelStatsChartMentions(ChannelStatsChart):
    def title(self):
        return "CMP Twitter Acct Mentions"

    def chartType(self):
        return log_const.CHANNEL_STATS_CHART_MENTIONS


class ChannelStatsChartHashtags(ChannelStatsChart):
    def title(self):
        return "CMP Twitter Acct Hashtags"

    def chartType(self):
        return log_const.CHANNEL_STATS_CHART_HASHTAGS


class ChannelStatsChartComparison(ChannelStatsChart):
    def title(self):
        return "CMP Twitter Acct Klout Scores"

    def chartType(self):
        return log_const.CHANNEL_STATS_CHART_COMPARISON


CHANNEL_STATS_CHART_VIEW_MAP = {
    log_const.CHANNEL_STATS_CHART_POSTS: ChannelStatsChartPosts, 
    log_const.CHANNEL_STATS_CHART_CLICKS: ChannelStatsChartClicks, 
    log_const.CHANNEL_STATS_CHART_FOLLOWERS: ChannelStatsChartFollowers, 
    log_const.CHANNEL_STATS_CHART_KLOUT_SCORES: ChannelStatsChartKloutScores, 
    log_const.CHANNEL_STATS_CHART_SEARCH_RANKS: ChannelStatsChartSearchRanks, 
    log_const.CHANNEL_STATS_CHART_RETWEETS: ChannelStatsChartRetweets, 
    log_const.CHANNEL_STATS_CHART_MENTIONS: ChannelStatsChartMentions, 
    log_const.CHANNEL_STATS_CHART_HASHTAGS: ChannelStatsChartHashtags, 
    log_const.CHANNEL_STATS_CHART_COMPARISON: ChannelStatsChartComparison, 
    }


def channel_stats_chart(request):
    csid = request.REQUEST.get("id")
    chartType = request.REQUEST.get("chartType")
    if chartType is None:
        attr = request.REQUEST.get("attr")
        chartType = ChannelStatsChart.get_chart_type_by_attr(attr)
    if chartType is not None:
        chartType = int(chartType)
    viewClass = CHANNEL_STATS_CHART_VIEW_MAP.get(chartType, None)
    if csid is None or viewClass is None:
        return HttpResponseBadRequest()
    return viewClass().chart(request)


class ContentSourceDailyStatsListView(ControllerView):
    def title(self):
        return "CMP Content Source Stats"

    def template(self):
        return "sns/log/cs_stats_list.html"
    
    @classmethod
    def path(cls):
        return "/#/log/csstats/"

    @classmethod
    def chart_path(cls):
        return "/#/log/cschart/"
    
    def lst(self, request):
        orderBy = request.REQUEST.get("orderby", "")
        orderType = request.REQUEST.get("type", "")
        pageSize = request.REQUEST.get("paginate_by")
        keyword = request.REQUEST.get("keyword", "")
        if pageSize is None or pageSize == "":
            pageSize = view_const.DEFAULT_INITIAL_PAGE_SIZE
        else:
            pageSize = int(pageSize)
        if keyword is not None and keyword != "":
            obj = ContentSourceDailyStats.get_by_name(keyword)
            query = [obj] if obj else []
        else:
            query = ContentSourceDailyStats.all()
            fields = ("clicks", "posts", "totalClicks", "totalPosts",)
            for field in fields:
                if orderBy == field.lower():
                    if orderType == "asc":
                        query = query.order(field)
                    if orderType == "desc":
                        query = query.order("-" + field)
        post_path = self.path() + "?orderby=" + str(orderBy) + "&type=" + str(orderType) + "&paginate_by=" + str(pageSize) + "&keyword=" + str(keyword)
        return object_list(request, query, paginate_by=pageSize,
                           extra_context=dict(view=self, title=self.title(), orderBy=orderBy, orderType=orderType, post_path=post_path, pageSize=pageSize, keyword=keyword),
                           template_name=self.template(),
                           )


def cs_stats_list(request):
    return ContentSourceDailyStatsListView().lst(request)


class ContentSourceDailyStatsChart(ControllerView):
    def title(self):
        return "Content Source Stats Chart"

    def template(self):
        return "sns/log/cs_stats_chart.html"
    
    def path(self):
        return ContentSourceDailyStatsListView.chart_path()
    
    def chartType(self):
        pass
    
    def comparisonType(self):
        return log_const.CS_STATS_CHART_COMPARISON

    def attr(self):
        return log_const.CS_STATS_CHART_ATTR_MAP.get(self.chartType(), None)

    @classmethod
    def get_chart_type_by_attr(cls, attr):
        for t, a in log_const.CS_STATS_CHART_ATTR_MAP.items():
            if attr == a:
                return t
        return None

    def chart(self, request):
        csstats_key = request.REQUEST.get("id")
        csstats = db.get(csstats_key)
        name = csstats.keyNameStrip()
        counter = csstats.get_or_insert_counter()
        if csstats.updd is None:
            return HttpResponseBadRequest()
        if self.chartType()==log_const.CS_STATS_CHART_COMPARISON:
            counts, labels, tips = [], [], [] 
            for chartType in log_const.CS_STATS_CHART_TYPES_NO_COMPARISION:
                attr = log_const.CS_STATS_CHART_ATTR_MAP[chartType]
                c, l, t = self._get_chart_data_for_cs_stats(counter, attr)
                counts.append(c)
                tips.append(t)
                if len(labels)==0:
                    labels = l
        else:
            counts, labels, tips = self._get_chart_data_for_cs_stats(counter, self.attr())
        form = ContentSourceDailyStatsForm(initial={'type': self.chartType()})
        return render_to_response(self.template(), 
                                  dict(view=self, counts=counts, labels=labels, tips=tips, form=form, id=csstats_key, name=name), 
                                  context_instance=RequestContext(request),
                                  )

    def _get_chart_data_for_cs_stats(self, counter, attr):
        statsDate, statsCounts = counter.getCounts(attr)
        if statsCounts is None:
            statsCounts = []
        return _get_chart_data_for_stats(statsDate, statsCounts)


class ContentSourceDailyStatsChartClicks(ContentSourceDailyStatsChart):
    def title(self):
        return "Content Source Clicks"

    def chartType(self):
        return log_const.CS_STATS_CHART_CLICKS
    

class ContentSourceDailyStatsChartPosts(ContentSourceDailyStatsChart):
    def title(self):
        return "Content Source Posts"

    def chartType(self):
        return log_const.CS_STATS_CHART_POSTS
    

class ContentSourceDailyStatsChartComparison(ContentSourceDailyStatsChart):
    def title(self):
        return "Content Source Comparison"

    def chartType(self):
        return log_const.CS_STATS_CHART_COMPARISON
    

CS_STATS_CHART_VIEW_MAP = {
    log_const.CS_STATS_CHART_POSTS: ContentSourceDailyStatsChartPosts, 
    log_const.CS_STATS_CHART_CLICKS: ContentSourceDailyStatsChartClicks, 
    log_const.CS_STATS_CHART_COMPARISON: ContentSourceDailyStatsChartComparison, 
    }


def cs_stats_chart(request):
    csstats_id = request.REQUEST.get("id")
    chartType = request.REQUEST.get("chartType")
    if chartType is None:
        attr = request.REQUEST.get("attr")
        chartType = ContentSourceDailyStatsChart.get_chart_type_by_attr(attr)
    if chartType is not None:
        chartType = int(chartType)
    viewClass = CS_STATS_CHART_VIEW_MAP.get(chartType, None)
    if csstats_id is None or viewClass is None:
        return HttpResponseBadRequest()
    return viewClass().chart(request)


def cs_stats_export_all(request):
    response = view_util.get_csv_response_base("SNS Analytics Content Source Stats")
    writer = csv.writer(response)
    writer.writerow(['Content Source', 'Clicks', 'Posts', 'Clicks - 30D', 'Posts - 30D', ])
    try:
        limit = 500
        cursor = None
        count = 0
        query = ContentSourceDailyStats.all()
        while True:
            if cursor:
                query.with_cursor(cursor)
            objs = query.fetch(limit=limit)
            count += len(objs)
            for obj in objs:
                row_data = [obj.keyNameStrip(), obj.clicks, obj.posts, obj.totalClicks, obj.totalPosts,] 
                writer.writerow(row_data)
            cursor = query.cursor()
            logging.info("Queried total %d objects. Current cursor is %s." % (count, cursor))
            if len(objs)<limit:
                break
    except Exception, ex:
        return HttpResponse("Unexpected error when exporting: %s" % str(ex), status=500)
    finally:
        logging.info("Completed exporting %d records." % count)
    return response
    

def cs_stats_export_one(request):
    cs = request.REQUEST['cs']
    response = view_util.get_csv_response_base("SNS Analytics CS Stats - %s" % cs)
    writer = csv.writer(response)
    writer.writerow(['Date', 'Clicks', 'Posts', ])
    try:
        counter = ContentSourceDailyStats.get_by_name(cs).get_or_insert_counter()
        if not counter:
            return HttpResponse("Stats not found for %s" % cs, status=404)
        usp_date, post_counts = counter.getPostCounts()
        usp_date, click_counts = counter.getClickCounts()
        for i in range(len(click_counts)):
            row_data = [datetime.datetime.strftime(usp_date, "%Y-%m-%d"), click_counts[-i-1], post_counts[-i-1], ]
            usp_date = usp_date - datetime.timedelta(days=1)
            writer.writerow(row_data)
    except Exception, ex:
        return HttpResponse("Unexpected error when exporting: %s" % str(ex), status=500)
    return response
    

def topic_stats_export(request):
    response = view_util.get_csv_response_base("SNS Analytics Level 1 Topic Stats")
    writer = csv.writer(response)
    writer.writerow(['Topic', 'Channels', 
                     'Followers', 'Clicks', 'Posts', 'Retweets', 'Mentions', 
                     'Clicks - 30D', 'Posts - 30D', 'Retweets - 30D', 'Mentions - 30D', ])
    try:
        limit = 100
        query = TopicStats.all()
        stats_list = query.fetch(limit=limit)
        count = len(stats_list)
        for stats in stats_list:
            row_data = [stats.keyNameStrip(), stats.channels, 
                        stats.latelyFollower, stats.latelyClick, stats.latelyPost, stats.retweets, stats.mentions, 
                        stats.totalClick, stats.totalPost, stats.totalRetweets, stats.totalMentions,  
                        ]
            writer.writerow(row_data)
        logging.info("Queried total %d topic stats." % count)
    except Exception, ex:
        return HttpResponse("Unexpected error when exporting: %s" % str(ex), status=500)
    finally:
        logging.info("Completed exporting %d TopicStats records." % count)
    return response
    

def trove_mention_export(request):
    mtype = request.REQUEST.get('mtype', None)
    mtypes = [mtype] if mtype else [trove_const.MENTION_BOTH, trove_const.MENTION_PICKER]
    end = int(request.REQUEST.get('end', 0))
    days = int(request.REQUEST.get('days', 1))
    response = view_util.get_csv_response_base("SNS Analytics Trove Mention Stats")
    writer = csv.writer(response)
    writer.writerow(['Date', 'Mention Type', 'Tweet URL', 'Tweet', ])
    for mtype in mtypes:
        _trove_mention_export(writer, mtype, end=end, days=days)
    return response


def _trove_mention_export(writer, mtype, end=0, days=1):
    today = ctz_util.uspacific_today()
    end_date = today - datetime.timedelta(days=end)
    start_date = end_date - datetime.timedelta(days=days)
    mtype_str = trove_const.MENTION_TYPE_MAP.get(mtype)
    logging.info("Retrieving posts for %s. start date %s end date %s" % (mtype_str, start_date, end_date))
    try:
        limit = 500
        cursor = None
        count = 0
        query = SPost.all().filter('troveMentionType', mtype).order('-modifiedTime')
        while True:
            if cursor:
                query.with_cursor(cursor)
            posts = query.fetch(limit=limit)
            logging.info("Retrieved %d posts for %s." % (len(posts), mtype_str))
            if not posts: break
            for post in posts:
                mod_date = ctz_util.to_uspacific(post.modifiedTime).date()
                if mod_date >= end_date: continue
                if start_date > mod_date: break
                row_data = [mod_date, mtype_str, twitter_util.tweet_id_2_url(post.tweetId), str_util.encode_utf8_if_ok(post.msg), ] 
                writer.writerow(row_data)
                count += 1
            cursor = query.cursor()
            logging.info("Queried total %d objects. Current cursor is %s." % (count, cursor))
    except Exception, ex:
        err_msg = "Unexpected error when exporting! %s" % str(ex)
        logging.error(err_msg)
        return HttpResponse(err_msg, status=500)
    finally:
        logging.info("Completed exporting %d records." % count)
    

def feed_campaigns_export_all(request):
    response = view_util.get_csv_response_base("SNS Analytics Feed Campaigns")
    writer = csv.writer(response)
    writer.writerow(['UID', 'Name', 'Twitter ID', 'Twitter Handle', 'State', 'Interval', ])
    try:
        limit = 500
        cursor = None
        count = 0
        query = FCampaign.all().filter('deleted', False)
        while True:
            if cursor:
                query.with_cursor(cursor)
            objs = query.fetch(limit=limit)
            count += len(objs)
            for obj in objs:
                if obj.state == camp_const.CAMPAIGN_STATE_INIT:
                    db.delete(obj)
                    logging.warn("Deleted an inactive feed campaign %s of user %d!" % (obj.name, obj.uid))
                    continue
                try:
                    channel = db_core.normalize_2_model(obj.channels[0])
                    chid = channel.chid_int()
                    channel_name = channel.name
                except:
                    chid = None
                    channel_name = None
                    logging.error("FCampaign %s of user %d does not have right channel!" % (obj.name, obj.uid))
                row_data = [obj.uid, obj.name, chid, channel_name, obj.state, obj.scheduleInterval,]
                writer.writerow(row_data)
            cursor = query.cursor()
            logging.info("Queried total %d objects. Current cursor is %s." % (count, cursor))
            if len(objs)<limit:
                break
    except Exception, ex:
        return HttpResponse("Unexpected error when exporting: %s" % str(ex), status=500)
    finally:
        logging.info("Completed exporting %d records." % count)
    return response
    

def twitter_upload(request):
    if request.method == 'POST':
        twitterFile = request.FILES['file']
        data = StringIO.StringIO(twitterFile.read())
        deferred.defer(setTwitterProfile,data)
        return HttpResponse('succeeded')
    else:
        form = TwitterUploadForm()
    return render_to_response('sns/log/twitter_upload.html', {'form':form, 'view':ControllerView(), 'title':'Import Twitter Profiles'}, context_instance=RequestContext(request,{"path":request.path}))


PROFILE_API_MAP = {'Name':'name','URL':'url','Location':'location','Bio':'description'}
IMAGE_API_MAP = {'Avatar':'image'}
def setTwitterProfile(data):
    def _t_exception(handle, msg):
        logging.exception("Twitter profile update - %s: %s" % (handle, msg))    
    
    def _t_error(handle, msg):
        logging.error("Twitter profile update - %s: %s" % (handle, msg))    
    
    def _t_info(handle, msg):
        logging.info("Twitter profile update - %s: %s" % (handle, msg))    
    
    try:
        rows = csv.reader(data)
        titles = rows.next()
        titleMap = {}
        index = 0
        for title in titles:
            titleMap[index] = title
            index += 1
        while True:
            try:
                objs = rows.next()
            except:
                break
            index = 0
            profile = {}
            try:
                for obj in objs:
                    profile[titleMap[index]] = obj
                    index +=1
                handle = profile['Handle']
                nameLower = handle.lower()
                channel = TAccount.all().filter('deleted', False).filter('nameLower', nameLower).fetch(limit=1)
                if len(channel) == 0:
                    _t_error(handle, "Handle not found!")
                    continue
                twitter = TwitterApi(oauth_access_token=channel[0].oauthAccessToken)
                    
                try:
                    params = {'include_entities':'true','skip_status':'true'}
                    for key in PROFILE_API_MAP.keys():
                        if profile.has_key(key) and profile[key] != '':
                            params[PROFILE_API_MAP[key]] = profile[key]
                    twitter.account.update_profile(**params)
                    _t_info(handle, "Name, URL, Location, Bio updated.")
                except Exception:
                    _t_exception(handle, "Name, URL, Location, Bio update failed!")
                    
                continue
            
                if profile.has_key('Background') and str_util.strip(profile['Background']) is not None:
                    try:
                        params = {'include_entities':'true','skip_status':'true','image':profile.pop('Background')}
                        twitter.account.update_profile_background_image(**params)
                        _t_info(handle, "Background updated.")
                    except Exception:
                        _t_exception(handle, "Background update failed!")
                        
                if profile.has_key('Avatar') and str_util.strip(profile['Avatar']) is not None :
                    try:
                        params = {'include_entities':'true','skip_status':'true','image':profile.pop('Avatar')}
                        twitter.account.update_profile_image(**params)
                        _t_info(handle, "Avatar updated.")
                    except Exception:
                        _t_exception(handle, "Avatar update failed!")
                
            except Exception:
                _t_exception('all', "Unexpected error when updating Twitter profiles!")
    except Exception:
        _t_exception('all', "Unexpected error when updating Twitter profiles!")
    
