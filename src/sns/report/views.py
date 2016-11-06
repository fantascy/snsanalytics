#! /usr/bin/env python
# -*- coding: utf-8 -*-
import logging
import urllib
from datetime import datetime,timedelta

from google.appengine.ext import db
from google.appengine.api import users
from django.views.generic.simple import direct_to_template
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.views.generic.list_detail import object_list
from django.template.defaultfilters import date
from django.http import HttpResponse

from common.ofc2 import openFlashChart
from common.ofc2.openFlashChart_varieties import (Line,
                                                    Line_Dot,
                                                    Line_Hollow,
                                                    Bar,
                                                    Bar_Filled,
                                                    Bar_Glass,
                                                    Bar_3d,
                                                    Bar_Sketch,
                                                    HBar,
                                                    Bar_Stack,
                                                    Area_Line,
                                                    Area_Hollow,
                                                    Pie,
                                                    Scatter,
                                                    Scatter_Line)
from common.ofc2.openFlashChart_varieties import (dot_value,
                                                    hbar_value,
                                                    bar_value,
                                                    bar_3d_value,
                                                    bar_glass_value,
                                                    bar_sketch_value,
                                                    bar_stack_value,
                                                    pie_value,
                                                    value,
                                                    scatter_value,
                                                    x_axis_labels,
                                                    x_axis_label)
from common.ofc2.openFlashChart_elements import (title,
                                                    x_legend,
                                                    y_legend,
                                                    x_axis,
                                                    y_axis,
                                                    radar_axis,
                                                    tooltip)

import context
from common import consts as common_const
from sns.core.core import get_user, UserClickParent, ChannelParent, ContentParent, get_user_id
from sns.api.facade import iapi
from common.utils import string as str_util
from common.utils import datetimeparser
from sns.usr import timezone as utz_util
from common.utils import iplocation
from sns.camp.models import CampaignClickCounter
from sns.view import consts as view_const
from sns.api import consts as api_const
from sns.core import consts as core_const
from sns.core import core as db_core
from sns.usr.models import UserClickCounter
from sns.chan.models import ChannelClickCounter, TAccount, FAccount, FAdminPage
from sns.chan.api import TAccountProcessor, FAccountProcessor, FAdminPageProcessor
from sns.cont.models import FeedCC, Feed
from sns.cont.api import FeedProcessor, MessageProcessor
from sns.post.models import SPost
from sns.post.api import QuickMessageCampaignProcessor, FeedCampaignProcessor
from sns.url.models import ShortUrlClickCounter, GlobalShortUrl
from sns.view.controllerview import ControllerView
from sns.post import views as posting_views
from forms import ReportBasicForm, SurlTopForm, UrlTopForm, ChannelTopForm, FChannelTopForm, \
                  FeedTopForm, CampaignTopForm, ChannelFailureTopForm, FChannelFailureTopForm, \
                  MessageFailureTopForm, FeedFailureTopForm, CampaignFailureTopForm, FailureBasicForm 


class ReportControllerView(ControllerView):
    def __init__(self):
        ControllerView.__init__(self, "Reports")
        
class DashBoardControllerView(ControllerView):
    def __init__(self):
        context.get_context().set_login_required(False)
        ControllerView.__init__(self, viewName="Home")

REPORT_TYPES = {0:'User',1:'Surl',2:'Url',3:'Channel',4:'Feed',5:'Campaign',7:'FAccount',8:'Campaign',}

TIME_RANGES = [
    ('minute',    '1 hour'),
    ('day',    '1 day'),
    ('week',  '1 week'),
    ('month',    '1 month'),                
    ('max',    'Max'),                
              ]
INFO_TYPES = [
     ('information','Basic info'),
     ('country','Click locations'),
     ('referrer','Click referrers'),                
              ]

TIME_RANGES_WITH_ONE_HOUR = [('hour',    '1 hour')] + TIME_RANGES                  

RANKING_TIME_RANGES = [               
    ('hour',    'Current hour'),                   
    ('day',    'Today'),
    ('week',  'This week'),
    ('month',    'This month'),                
    ('max',    'Life time'),                
              ]

FAILURE_TIME_RANGES = TIME_RANGES_WITH_ONE_HOUR

REFERER_TWITTER = "Twitter.com"
REFERER_DIRECT = "Direct clicks"
REFERER_WEBSITES = {'twitter':'Twitter.com',
                    'tweetdeck':'Tweetdeck.com',
                    'seesmic':'Tweetdeck.com',
                    'cotweet':'Cotweet.com',
                    'tweetie':'Tweetie.com',
                    'facebook':'Facebook.com',
                    'google':'Google.com',
                    'yahoo':'Yahoo.com',
                    'direct':'Direct clicks',}

MAX_SEARCH_RESULT=5
PIE_CHART_COLOR=['#000080','#FFFF00','#008000','#8B4513','#800080','#FF0000','#808080','#FFA500','#A52A2A','#008B8B','#9400D3']

def chart_data(request):
    url=request.GET.get('url')
    timeRange=request.GET.get('timeRange')
    plot = Pie(start_angle = 35, animate = True, values = [2, 3, pie_value(6.5, ('hello (6.5)', '#FF33C9', 12),'#FF33C9','AAAAA')], colours = ['#D01F3C', '#356AA0', '#C79810'], label_colour = '#432BAF')
    plot.set_tooltip('#val# of #total#<br>#percent# of 100%')
    plot.set_gradient_fill(True)
    plot.set_on_click('plot1')
    plot.set_no_labels(False)
    #pie_data.append(pie_value(val=28,label=("CLickName",'#FF33C9', 24)))    
    #plot = Pie(values=[5,8,10])

    chart = openFlashChart.template("Pie chart")
    chart.add_element(plot)
    return HttpResponse(chart.encode())

def haveClickChart(clickCounter, timeUnit, units,week=None,extraCounter=None,noLabel=False,type=None):
    if clickCounter is None :
        return "False"

    modelUser = get_user()
    userNow = utz_util.to_usertz(datetime.utcnow())
    if timeUnit==core_const.TIME_UNIT_HOUR :
        timeWindow = timedelta(hours=units-1)
    elif timeUnit==core_const.TIME_UNIT_MINUTE :
        timeWindow = timedelta(minutes=units-1)
    else :
        timeWindow = timedelta(days=units-1) 
    timeWindowStart = userNow - timeWindow
    counters = clickCounter.normalizedCounters(timeUnit, units)
    tag = "True"
    if type is not None:
        if type == 'user':
            total=0
            if len(counters)==0:
                tag = "False"
            else:
                for counter in counters:
                    total+=counter
            logging.info("haveClickChart total:%s" % str(total))
            return tag,total
    if len(counters)==0:
        tag = "False"
    return tag
        

def getClickChart(clickCounter, timeUnit, units,week=None,extraCounter=None,noLabel=False,isClick=True,type=None,html5=False):
    userNow = utz_util.to_usertz(datetime.utcnow())
    if timeUnit==core_const.TIME_UNIT_HOUR :
        timeWindow = timedelta(hours=units-1)
    elif timeUnit==core_const.TIME_UNIT_MINUTE :
        timeWindow = timedelta(minutes=units-1)
    else :
        timeWindow = timedelta(days=units-1) 
    timeWindowStart = userNow - timeWindow
    counters = clickCounter.normalizedCounters(timeUnit, units)
    extraInfo = None
    if extraCounter is not None:
        if extraCounter.__class__.__name__ in ['CampaignClickCounter','FeedCC','DMCampaignClickCounter']:
            model = db.get(clickCounter.keyNameStrip())
            compareModel = db.get(extraCounter.keyNameStrip())
            extraInfo = [model.name,compareModel.name]
        elif extraCounter.__class__.__name__ == 'ChannelClickCounter':
            if clickCounter.key().name().startswith(TAccount.keyNamePrefix()):
                channel = TAccount.get_by_key_name(clickCounter.key().name(), ChannelParent.get_or_insert_parent())
            elif clickCounter.key().name().startswith(FAccount.keyNamePrefix()):
                channel = FAccount.get_by_key_name(clickCounter.key().name(), ChannelParent.get_or_insert_parent())
            elif clickCounter.key().name().startswith(FAdminPage.keyNamePrefix()):
                channel = FAdminPage.get_by_key_name(clickCounter.key().name(), ChannelParent.get_or_insert_parent())
            
            if extraCounter.key().name().startswith(TAccount.keyNamePrefix()):
                extraChannel = TAccount.get_by_key_name(extraCounter.key().name(), ChannelParent.get_or_insert_parent())
            elif extraCounter.key().name().startswith(FAccount.keyNamePrefix()):
                extraChannel = FAccount.get_by_key_name(extraCounter.key().name(), ChannelParent.get_or_insert_parent())
            elif extraCounter.key().name().startswith(FAdminPage.keyNamePrefix()):
                extraChannel = FAdminPage.get_by_key_name(extraCounter.key().name(), ChannelParent.get_or_insert_parent())
            extraInfo = [channel.name,extraChannel.name]
                
        extraCounter = extraCounter.normalizedCounters(timeUnit, units)

    chart=getCounterChart(counters,timeUnit,units,timeWindowStart,userNow,week=week,
                                       extraCounter=extraCounter,extraInfo=extraInfo,noLabel=noLabel,isClick=isClick,type=type,html5=html5)
    return chart
    
def getCounterChart(counters,timeUnit,units,startTime,endTime,week=None,extraCounter=None,extraInfo=None,noLabel=False,isClick=True,title="Total Clicks",type=None,html5=False):   
    chartstart = datetime(year=startTime.year,month=startTime.month,day=startTime.day,hour=startTime.hour)
    chartend   = datetime(year=endTime.year,month=endTime.month,day=endTime.day,hour=endTime.hour)

    format = common_const.UI_DATETIME_FORMAT
    conjunction = 'on' 

    if timeUnit==core_const.TIME_UNIT_MINUTE :        
        """calculate 60 minute list before now""" 
        conjunction = 'at' 
        currentHour = endTime.hour  
        endMinute = endTime.minute
        timeNow = endTime 
        showPoint = []
        showPointDetail = []
        num = 1
        while True:
            if endMinute < 10:
                showPointDetail.append(str(currentHour)+":0"+str(endMinute))
            else:
                showPointDetail.append(str(currentHour)+":"+str(endMinute))
            if endMinute%5:
                showPoint.append("")
            else:
                if endMinute < 10:
                    showPoint.append(str(currentHour)+":0"+str(endMinute))
                else:
                    showPoint.append(str(currentHour)+":"+str(endMinute))
            endMinute = endMinute - 1
            if endMinute < 0:
                hours = timedelta(hours=1)
                timeNow = timeNow - hours
                currentHour = timeNow.hour 
                endMinute = endMinute + 60
            if num >= units:
                break
            num = num + 1
        #pointString = "|"
        #for eachPoint in showPoint:
        #    pointString = "|" + eachPoint + pointString

        chartstart = datetime(year=startTime.year,month=startTime.month,day=startTime.day,hour=startTime.hour,minute=startTime.minute)
        chartend   = datetime(year=endTime.year,month=endTime.month,day=endTime.day,hour=endTime.hour,minute=endTime.minute)    
        
    elif timeUnit==core_const.TIME_UNIT_HOUR :        
        """calculate 24 hour list before now""" 
        conjunction = 'at'     
        endHour = endTime.hour + 1
        if endHour == 24:
            endHour = 0        
        hourPoint = endHour 
        num = 1  
        showPoint = []
        showPointDetail = []
        while True:
            hourPoint = hourPoint - 1;
            if hourPoint < 0:
                hourPoint = hourPoint + 24
            showPoint.append(str(hourPoint))
            showPointDetail.append(str(hourPoint)+":00")
            if num >= units:
                break
            num = num + 1
                            
        #pointString = "|"
        #for eachPoint in showPoint:
        #    pointString = "|" + eachPoint + pointString
                    
    elif timeUnit==core_const.TIME_UNIT_DAY and week is not None : 
        format = "N j, Y"      
        """calculate 7 days list in a week before now"""    
        endWeekday = endTime.weekday() + 1
        weekdayPoint = endWeekday   
        showPoint = []
        showPointDetail = []
        while True:        
            weekday = {"1":"Mon.","2":"Tue.","3":"Wed.","4":"Thu.","5":"Fri.","6":"Sat.","7":"Sun.",} 
            showPoint.append(weekday[str(weekdayPoint)])
            showPointDetail.append(weekday[str(weekdayPoint)])
            weekdayPoint = weekdayPoint - 1;
            if weekdayPoint == 0:
                weekdayPoint = weekdayPoint + 7            
            if weekdayPoint == endWeekday:
                break           
        
        #pointString = "|"
        #for eachPoint in showPoint:
        #    pointString = "|" + weekday[eachPoint] + pointString
        
    elif timeUnit==core_const.TIME_UNIT_DAY :     
        format = "N j, Y"   
        """calculate n(units) days list before now"""  
        showPoint = []
        showPointDetail = []
        month = {"1":"Jan.","2":"Feb.","3":"Mar.","4":"Apr.","5":"May.","6":"Jun.","7":"Jul.","8":"Aug.","9":"Sep.","10":"Oct.","11":"Nov.","12":"Dec.",}
        num = 1
        if units <= 31:
            '''seperated by 1 day'''
            while True:
                showPointDetail.append(date(endTime, format))
                showPoint.append(str(endTime.day))
                if num >= units:
                    break            
                days = timedelta(days=1)
                endTime = endTime - days
                num = num + 1
                
        elif 31 < units <= 200:
            '''seperated by 10 days'''
            while True:
                showPointDetail.append(date(endTime, format))
                if endTime.day%10:
                    if endTime.month==2 and endTime.day==28:
                        showPoint.append(month[str(endTime.month)]+str(endTime.day))
                    else:
                        showPoint.append("")
                else:
                    showPoint.append(month[str(endTime.month)]+str(endTime.day))
                
                if num >= units:
                    break            
                days = timedelta(days=1)
                endTime = endTime - days
                num = num + 1
                
        else: 
            '''seperated by 1 month'''
            while True:
                showPointDetail.append(date(endTime, format))
                if endTime.day == 1:
                    showPoint.append(month[str(endTime.month)]+str(endTime.day))                    
                else:
                    showPoint.append("")
                
                if num >= units:
                    break            
                days = timedelta(days=1)
                endTime = endTime - days
                num = num + 1
        
        #pointString = "|"
        #for eachPoint in showPoint:
        #    pointString = "|" + eachPoint + pointString
    
    total = 0
    for i in range(0, len(counters)) :
        total += int(counters[i])
    y_max = max(counters)

    showPointDetail.reverse()
    showPoint.reverse()
    
    if html5:
        start=date(chartstart, format)
        end=date(chartend, format)
        showPointDetailText=[]
        for i in range(0,len(counters)):
            if isClick:
                if counters[i]<=1:
                    showPointDetailText.append(str(str_util.numberDisplay(str(counters[i]))+' click '+conjunction+' '+showPointDetail[i]))
                else:
                    showPointDetailText.append(str(str_util.numberDisplay(str(counters[i]))+' clicks '+conjunction+' '+showPointDetail[i]))
            else:
                if counters[i]<=1:
                    showPointDetailText.append(str(str_util.numberDisplay(str(counters[i]))+' tweet '+conjunction+' '+showPointDetail[i]))
                else:
                    showPointDetailText.append(str(str_util.numberDisplay(str(counters[i]))+' tweets '+conjunction+' '+showPointDetail[i]))
        dot_size=getNodeSizeHtml5(counters)        
        x_range=str("from "+date(chartstart, format)+" to "+date(chartend, format))
        showPointDetailTextExtra=[]
        if extraCounter is not None:
            for i in range(0,len(extraCounter)):                
                if isClick:
                    if extraCounter[i]<=1:
                        showPointDetailTextExtra.append(str(str_util.numberDisplay(str(extraCounter[i]))+' click '+conjunction+' '+showPointDetail[i]))
                    else:
                        showPointDetailTextExtra.append(str(str_util.numberDisplay(str(extraCounter[i]))+' clicks '+conjunction+' '+showPointDetail[i]))
                else:
                    if extraCounter[i]<=1:
                        showPointDetailTextExtra.append(str(str_util.numberDisplay(str(extraCounter[i]))+' tweet '+conjunction+' '+showPointDetail[i]))
                    else:
                        showPointDetailTextExtra.append(str(str_util.numberDisplay(str(extraCounter[i]))+' tweets '+conjunction+' '+showPointDetail[i]))
            key=[extraInfo[0].encode('utf-8'),extraInfo[1].encode('utf-8')]
            showPointDetailText.extend(showPointDetailTextExtra)
            y_max_extra = max(extraCounter)
            y_max = max(y_max,y_max_extra)
            return (str([str(counters),str(showPoint),str(showPointDetailText),str(start),str(end),total,y_max,dot_size,x_range]),str([str(extraCounter),str(showPointDetailText),str(key)])),total
        return (str([str(counters),str(showPoint),str(showPointDetailText),str(start),str(end),total,y_max,dot_size,x_range]),'extra_counters'),total
    else:
        line_date = []
        for i in range(0,len(counters)):
            if isClick:
                tooltip="Clicks: #val#<br>"+showPointDetail[i]
            else:
                tooltip="Tweets: #val#<br>"+showPointDetail[i]
            value_line = value(str(counters[i]),'#FFA500',tooltip)
            line_date.append(value_line)
        
        l = Line_Dot(fontsize = 20, values = line_date)      
        l.set_colour('#FF9900')
        #l.set_tooltip('Clicks: #val#<br>#x_label#')
        if extraInfo is not None:
            l.set_text(extraInfo[0])
        l.set_dot_size(getNodeSize(counters))
        l.set_halo_size(0)        
        if type is not None:
            if type=='user':
                chart = openFlashChart.template('')
        else:
            if isClick:
                chart = openFlashChart.template(title+" : " + str_util.numberDisplay(str(total)))
            else:
                chart = openFlashChart.template("Total : " + str_util.numberDisplay(str(total)))  
        chart.set_bg_colour('#FFFFFF') 
        chart.add_element(l) 
        if extraCounter is not None:
            line_date_extra = []
            for i in range(0,len(extraCounter)):
                if isClick:
                    tooltip="Clicks: #val#<br>"+showPointDetail[i]
                else:
                    tooltip="Tweets: #val#<br>"+showPointDetail[i]
                value_line = value(str(extraCounter[i]),'#8EC1DA',tooltip)
                line_date_extra.append(value_line)
            l_extra = Line_Dot(fontsize = 20, values = line_date_extra)
            #l_extra.set_tooltip('#val#<br>#x_label#')      
            l_extra.set_colour('#8EC1DA')
            l_extra.set_text(extraInfo[1])
            l_extra.set_dot_size(getNodeSize(counters))
            l_extra.set_halo_size(0)
            chart.add_element(l_extra)
            y_max_extra = max(extraCounter)
            y_max = max(y_max,y_max_extra)
        if y_max==0:
            y_max=5
        chart.set_x_axis(labels = x_axis_labels(labels=showPoint), grid_colour = '#E0FFFF')
        chart.set_x_legend("from "+date(chartstart, format)+" to "+date(chartend, format)) 
        chart.set_y_axis(max = y_max,steps = get_y_axis_steps(y_max), grid_colour = '#E0FFFF')
    
        return chart.encode()


def get_y_axis_steps(y_max):
    steps=1
    while True:
        y_max=y_max/10
        if y_max<10:
            if y_max<2:
                steps*=1
                break
            elif y_max<4:
                steps*=2
                break
            else:
                steps*=5
                break
        steps=steps*10
    return steps
 
def getNodeSizeHtml5(counters):
    if len(counters)==0:
        return 2.5
    return min(2.5,50.0/len(counters))         

def getNodeSize(counters):
    if len(counters)==0:
        return 4.0
    return min(4.0,200.0/len(counters))  

def mergeCounters(counters,scale,total=True):
    days_f=[]
    day_index=0    
    hour_index=0
    hour_count=0
    while hour_index<len(counters):       
        if hour_count==0:
            days_f.append(counters[hour_index])
        else:
            if total:
                days_f[day_index]+=counters[hour_index]
        hour_index +=1
        hour_count +=1
        if hour_count==scale:
            hour_count=0
            day_index+=1
    return days_f

def haveChannelPieChart(timeUnit,units):
    tag = False    
    parent = ChannelParent.get_or_insert_parent()
    channels = TAccount.all().ancestor(parent).filter('deleted', False).order('nameLower').fetch(limit=1000)
    fchannels = FAccount.all().ancestor(parent).order('nameLower').fetch(limit=1000)
    pchannels = FAdminPage.all().ancestor(parent).order('nameLower').fetch(limit=1000)
    for fchannel in fchannels:
        channels.append(fchannel)
    for pchannel in pchannels:
        channels.append(pchannel)
    for channel in channels:
        keyname=channel.key().name()
        clickCounter = ChannelClickCounter.get_or_insert_update(keyname, parent=UserClickParent.get_or_insert_parent())
        total = getClickNumber(clickCounter, timeUnit, units)
        if total>0:
            tag = True
            break
    return tag

def haveFeedPieChart(timeUnit,units):
    tag = False   
    feeds = Feed.all().ancestor(ContentParent.get_or_insert_parent()).fetch(limit=1000)
    for feed in feeds:
        clickCounter = FeedCC.get_or_insert_update_by_feed(feed)
        total = getClickNumber(clickCounter, timeUnit, units)
        if total>0: 
            tag = True
            break
    return tag

def getPieChartParams(request):    
    timeRange = request.GET.get("timeRange",None)
    if timeRange is None :
        timeRange = 'day'
        timeUnit = core_const.TIME_UNIT_HOUR
        units = 24
    else:
        timeRange = str_util.strip(timeRange)
        if timeRange=='minute':
            timeUnit = core_const.TIME_UNIT_MINUTE
            units = 60
        elif timeRange=='day':
            timeUnit = core_const.TIME_UNIT_HOUR
            units = 24
        elif timeRange=='week':
            timeUnit = core_const.TIME_UNIT_DAY
            units = 7
        elif timeRange=='month':
            timeUnit = core_const.TIME_UNIT_DAY
            units = 31
        else:
            modelUser=get_user()
            time_length=datetime.utcnow()-modelUser.firstVisit
            unit, number =getLifeTimeUnit(time_length)
            
            timeUnit = unit
            units = number
            
    return timeUnit,units  

def channelPieChartData(request,timeUnit=None,units=None,html5=False):
    if html5:
        pass
    else:
        timeUnit,units = getPieChartParams(request)     
    data={}
    
    parent = ChannelParent.get_or_insert_parent()
    channels = TAccount.all().ancestor(parent).filter('deleted', False).order('nameLower').fetch(limit=1000)
    fchannels = FAccount.all().ancestor(parent).order('nameLower').fetch(limit=1000)
    pchannels = FAdminPage.all().ancestor(parent).order('nameLower').fetch(limit=1000)
    for fchannel in fchannels:
        channels.append(fchannel)
    for pchannel in pchannels:
        channels.append(pchannel)
    deletedTotal=0
    for channel in channels:
        keyname=channel.key().name()
        clickCounter = ChannelClickCounter.get_or_insert_update(keyname,parent=UserClickParent.get_or_insert_parent())
        total = getClickNumber(clickCounter, timeUnit, units)
        if total>0:
            if channel.deleted==True:
                deletedTotal+=total
            else:
                if channel.className() == 'TAccount':
                    data["(t) "+channel.login()]=total
                else:
                    data["(f) "+channel.name]=total
    if deletedTotal>0:
        data['Deleted accts']=deletedTotal  
    if html5:        
        return getPieChartData(data,html5=html5)        
    else:
        return HttpResponse(getPieChartData(data))     

def feedPieChartData(request,timeUnit=None,units=None,html5=False):
    if html5:
        pass
    else:
        timeUnit,units = getPieChartParams(request) 
            
    data={}
    feeds = Feed.all().ancestor(ContentParent.get_or_insert_parent()).fetch(limit=1000)
    feedTotal=0
    deletedTotal=0
    for feed in feeds:
        clickCounter = FeedCC.get_or_insert_update_by_feed(feed)
        total = getClickNumber(clickCounter, timeUnit, units)
        if total>0:            
            feedTotal+=total
            if feed.deleted==True:
                deletedTotal+=total
            else:
                data[feed.name]=total
            
    uid =get_user_id()
    userCounter = UserClickCounter.get_or_insert_update(UserClickCounter.keyName(uid), UserClickParent.get_or_insert_parent())
    articleTotal = getClickNumber(userCounter, timeUnit, units)-feedTotal
    if articleTotal>0:
        data['Non feed msgs']=articleTotal
    if deletedTotal>0:
        data['Deleted feeds']=deletedTotal  
    if html5:        
        return getPieChartData(data,html5=html5)        
    else:
        return HttpResponse(getPieChartData(data))
 
def pieChartDataModify(data):
    dataModified={}
    total=0
    others=0
    for i in range(0, len(data)):
        total += int(data[i][1])
    for i in range(0, len(data)):
        if len(data[i][0])>13:
            cutPoint=13
            while True:
                try:
                    #data[i]=((data[i][0][0:cutPoint]+"...").replace("u'","SubstituteChartInfo"),data[i][1],(data[i][0]).replace("u'","SubstituteChartInfo"),round(float(data[i][1]*100)/total,2))
                    data[i]=((data[i][0][0:cutPoint]+"..."),data[i][1],(data[i][0]),round(float(data[i][1]*100)/total,2))
                    break
                except:
                    cutPoint+=1
        elif len(data[i][0])<=13:
            #data[i]=((data[i][0].ljust(10)).replace("u'","SubstituteChartInfo"),data[i][1],(data[i][0]).replace("u'","SubstituteChartInfo"),round(float(data[i][1]*100)/total,2))
            data[i]=((data[i][0].ljust(10)),data[i][1],(data[i][0]),round(float(data[i][1]*100)/total,2))
    while len(data)>=3:
        if data[-1][1]*100/total<5:
            others+=data[-1][1]
            data.pop()            
        else:
            break           
            
    return data,total,others  
    
def getPieChartData(data,html5=False):
    data=sorted(data.items(), key=lambda d: d[1],reverse=True)
    data,total,others=pieChartDataModify(data)
    if len(data)>10:
        data=data[:10]
        for i in range(0,len(data)-10):
            others+=data[10+i][1]
    if others!=0:
        data.append(('Others',others,'Others',round(float(others*100)/total,2)))   
        
    if html5:
        pie_data=[]
        pie_label=[]
        tooltips=[]
        for item in data:
            pie_data.append(item[1])
            pie_label.append((item[0] if len(item[0])<=10 else item[0][0:11]+'+').encode('utf-8'))
            text=item[2]
            if len(text)>30:
                text=text[0:28]+"..."
            tooltips.append((text+" : "+str_util.numberDisplay(str(item[1]))+"("+str(item[3])+"%) out of total "+str_util.numberDisplay(str(total))).encode('utf-8'))
        return [pie_data,pie_label,tooltips]
    else:
        pie_data=[]
        i=0
        for item in data:
            text=unicode(item[2])
            if len(text)>30:
                text=text[0:28]+"..."
            tooltip=text+"<br>"+unicode(item[1])+"("+unicode(item[3])+"%) in total:"+str_util.numberDisplay(unicode(total))
            pie_data.append(pie_value(item[1],(item[0],'#000000', 9),PIE_CHART_COLOR[i],tooltip))    
            i+=1
        plot = Pie(values=pie_data,start_angle = 360)
        chart = openFlashChart.template("")
        chart.add_element(plot)
        chart.set_bg_colour('#FFFFFF')   
        return chart.encode()


def haveCountryBarChart(clickCounter):
    if clickCounter.countryBracket:
        country=eval(clickCounter.countryBracket)
        #country=clickCounter.countryBracket
        #country=country.replace("'",'"')
        #country=country.replace('u"','"')
        #country=json.loads(country)  
         
    return haveBarChart(country)    

def haveReferrerBarChart(clickCounter):
    referrer=eval(clickCounter.referrerBracket)
    
    return haveBarChart(referrer)

def haveBarChart(counters):
    tag = "False"
    if len(counters)>0:
        for key in counters.keys():
            if counters[key]>0:
                tag = "True"
                break
    return tag
    
def countryBarChartData(clickCounter,html5=False):
    clickCounter.checkCountersDataAndModify(report=True)    
    if clickCounter.countryBracket:
        country=eval(clickCounter.countryBracket)
        #country=country.replace("'",'"')
        #country=country.replace('u"','"')
        #country=json.loads(country)    
        
        #To treat 'XX' as 'US'
        if country.has_key('xx'):
            if country.has_key('us'):
                country['us']=country['us']+country['xx']
            else:
                country['us']=country['xx']
            del country['xx']
        
        
        country=sorted(country.items(), key=lambda d: d[1])
        country.reverse()
        
        show=5
        geo={}
        if len(country)>show:
            other_total=0
            for i in range(0,show):
                obj=country[i]
                name=iplocation.get_country_name(obj[0])
                geo[name]=int(obj[1])
            for t in range(show,len(country)):
                obj=country[t]
                other_total+=obj[1]
            geo[iplocation.COUNTRY_NAME_OTHERS]=int(other_total)
        else:
            for i in range(0,len(country)):
                obj=country[i]
                name=iplocation.get_country_name(obj[0])
                geo[name]=int(obj[1])
    else:
        geo={}

    geo=sorted(geo.items(), key=lambda d: d[1]) 
    return getBarChartData(geo,'Click-throughs by Country.', html5=html5)
    

def referrerBarChartData(clickCounter,html5=False):
    clickCounter.checkCountersDataAndModify(report=True) 
    other_total=0
    if clickCounter.referrerBracket:
        referrer=eval(clickCounter.referrerBracket)
        refer={}
        for key in referrer.keys():
            if referrer[key]!=0:
                if key=="Others":                    
                    other_total+=int(referrer[key])
                else:
                    refer[key]=referrer[key]
    else:
        refer={}
    sorted_referrer=sorted(refer.items(), key=lambda d: d[1])    
    sorted_referrer.reverse()
        
    show=5
    data=[]
    if len(sorted_referrer)>show:
        for i in range(0,show):
            obj=sorted_referrer[i]
            data.append((obj[0],int(obj[1])))
        for t in range(show,len(sorted_referrer)):
            obj=sorted_referrer[t]
            other_total+=int(obj[1])
        #data.append(('Others',other_total))
    else:
        for i in range(0,len(sorted_referrer)):
            obj=sorted_referrer[i]
            data.append((obj[0],int(obj[1])))
    if other_total!=0:
        data.append(('Others',other_total))                 
    return getBarChartData(data,'Click-throughs by Referrer.',html5=html5)


def getBarChartData(data,title,html5=False):
    values=[]
    names=[]
    totalClicks=0
    for single in data:
        if single[1]!=0:
            values.append(single[1])
            names.append(single[0])
            totalClicks+=single[1] 
    if html5:
        tooltips=[]
        names=[]
        for item in data:
            if len(item[0])>15:
                names.append(str(item[0][0:15]+'+'))
            else:
                names.append(str(item[0]))
            if item[1]<=1:
                tooltips.append(str(str_util.numberDisplay(str(item[1]))+" click from "+item[0]))
            else: 
                tooltips.append(str(str_util.numberDisplay(str(item[1]))+" clicks from "+item[0]))
        y_max=max(values)
        title=str("%s Life time clicks: %s" % (title, str_util.numberDisplay(str(totalClicks))))
        return [values,names,tooltips,totalClicks,y_max,title]
    else:             
        plot=Bar(values=values)
        
        chart=openFlashChart.template("%s Life time clicks: %s" % (title, str_util.numberDisplay(str(totalClicks))))
        chart.add_element(plot)
        chart.set_x_axis(labels=x_axis_labels(labels=names,rotate=40))
        
        y_max=max(values)
        chart.set_y_axis(max = y_max,steps=get_y_axis_steps(y_max))
        chart.set_bg_colour('#FFFFFF')
     
        return chart.encode()    


def getClickNumber(clickCounter, timeUnit, units):
    total=0;
    counters = clickCounter.normalizedCounters(timeUnit, units)
    for number in counters:
        total+=number
    return total


def getShortUrlMinutelyClickChart(clickCounter, urlHash=None, units=60, html5=False):
    return getClickChart(clickCounter, core_const.TIME_UNIT_MINUTE, units, html5=html5)

def getShortUrlHourlyClickChart(clickCounter, urlHash=None, units=24, html5=False):
    return getClickChart(clickCounter, core_const.TIME_UNIT_HOUR, units, html5=html5)


def getShortUrlDailyClickChart(clickCounter, urlHash=None, units=31, week=None, html5=False):
    if week is None:
        return getClickChart(clickCounter, core_const.TIME_UNIT_DAY, units, html5=html5)
    else:
        return getClickChart(clickCounter, core_const.TIME_UNIT_DAY, units, week=week, html5=html5)

def getUrlMinutelyClickChart(clickCounter, units=60,html5=False):
    return getClickChart(clickCounter, core_const.TIME_UNIT_MINUTE, units,html5=html5)

def getUrlHourlyClickChart(clickCounter, units=24,html5=False):
    return getClickChart(clickCounter, core_const.TIME_UNIT_HOUR, units,html5=html5)


def getUrlDailyClickChart(clickCounter, units=31,week=None,html5=False):
    if week is None:
        return getClickChart(clickCounter, core_const.TIME_UNIT_DAY, units, html5=html5)
    else:
        return getClickChart(clickCounter, core_const.TIME_UNIT_DAY, units, week=week, html5=html5)

def getChannelClickCounter(channelId):
    return ChannelClickCounter.get_or_insert_update(TAccount.keyName(channelId), UserClickParent.get_or_insert_parent())

def getChannelMinutelyClickChart(channel=None,channelCompare='None', units=60, html5=False):
    clickCounter = getChannelClickCounter(channel)
    if channelCompare == 'None':
        extraCounter = None
    else:
        extraCounter = getChannelClickCounter(channelCompare)
    return getClickChart(clickCounter, core_const.TIME_UNIT_MINUTE, units, extraCounter=extraCounter, html5=html5)

def getChannelHourlyClickChart(channel=None,channelCompare='None', units=24,html5=False):
    clickCounter = getChannelClickCounter(channel)
    if channelCompare == 'None':
        extraCounter = None
    else:
        extraCounter = getChannelClickCounter(channelCompare)
    return getClickChart(clickCounter, core_const.TIME_UNIT_HOUR, units,extraCounter=extraCounter,html5=html5)

def getChannelDailyClickChart(channel=None,channelCompare='None', units=31,week=None,html5=False):
    clickCounter = getChannelClickCounter(channel)
    if channelCompare == 'None':
        extraCounter = None
    else:
        extraCounter = getChannelClickCounter(channelCompare)
    if week is None:
        return getClickChart(clickCounter, core_const.TIME_UNIT_DAY, units, extraCounter=extraCounter, html5=html5)
    else:
        return getClickChart(clickCounter, core_const.TIME_UNIT_DAY, units, week, extraCounter=extraCounter, html5=html5)

def getFAccountClickCounter(fchannel):
    fchannelClickCounter = ChannelClickCounter.get_or_insert_update(fchannel.key().name(), UserClickParent.get_or_insert_parent())
    if fchannel.__class__ == FAccount:
        type = 'fchannel'
    else:
        type = 'fpage'
    return fchannelClickCounter,type
        
def getFAccountMinutelyClickChart(fchannel,fchannelCompare='None', units=60, html5=False):
    clickCounter,type = getFAccountClickCounter(fchannel)
    if fchannelCompare == 'None':
        extraCounter = None
    else:
        extraCounter,type = getFAccountClickCounter(fchannelCompare)
    return getClickChart(clickCounter, core_const.TIME_UNIT_MINUTE, units, extraCounter=extraCounter, html5=html5)

def getFAccountHourlyClickChart(fchannel,fchannelCompare='None', units=24, html5=False):
    clickCounter,type = getFAccountClickCounter(fchannel)
    if fchannelCompare == 'None':
        extraCounter = None
    else:
        extraCounter,type = getFAccountClickCounter(fchannelCompare)
    return getClickChart(clickCounter, core_const.TIME_UNIT_HOUR, units,extraCounter=extraCounter, html5=html5)

def getFAccountDailyClickChart(fchannel,fchannelCompare='None', units=31,week=None,html5=False):
    clickCounter,type = getFAccountClickCounter(fchannel)
    if fchannelCompare == 'None':
        extraCounter = None
    else:
        extraCounter,type = getFAccountClickCounter(fchannelCompare)
    if week is None:
        return getClickChart(clickCounter, core_const.TIME_UNIT_DAY, units, extraCounter=extraCounter, html5=html5)
    else:
        return getClickChart(clickCounter, core_const.TIME_UNIT_DAY, units, week, extraCounter=extraCounter, html5=html5)

def getFeedClickCounter(feed):
    return FeedCC.get_or_insert_update_by_feed(feed)

def getFeedMinutelyClickChart(feed, feedCompare='None', units=60, html5=False):
    clickCounter = getFeedClickCounter(feed)
    if feedCompare == 'None':
        extraCounter = None
    else:
        extraCounter = getFeedClickCounter(feedCompare)
    return getClickChart(clickCounter, core_const.TIME_UNIT_MINUTE, units, extraCounter=extraCounter, html5=html5)
    
def getFeedHourlyClickChart(feed, feedCompare='None', units=24, html5=False):
    clickCounter = getFeedClickCounter(feed)
    if feedCompare == 'None':
        extraCounter = None
    else:
        extraCounter = getFeedClickCounter(feedCompare)
    return getClickChart(clickCounter, core_const.TIME_UNIT_HOUR, units, extraCounter=extraCounter ,html5=html5)

def getFeedDailyClickChart(feed, feedCompare='None', units=31, week=None, html5=False):
    clickCounter = getFeedClickCounter(feed)
    if feedCompare == 'None':
        extraCounter = None
    else:
        extraCounter = getFeedClickCounter(feedCompare)
    if week is None:
        return getClickChart(clickCounter, core_const.TIME_UNIT_DAY, units, extraCounter=extraCounter, html5=html5)
    else:
        return getClickChart(clickCounter, core_const.TIME_UNIT_DAY, units, week=week, extraCounter=extraCounter, html5=html5)

def getCampaignClickCounter(campaignId):
    return CampaignClickCounter.get_or_insert_update(CampaignClickCounter.keyName(campaignId), UserClickParent.get_or_insert_parent()) 

def getCampaignMinutelyClickChart(campaign=None,campaignCompare='None', units=60, html5=False):
    clickCounter = getCampaignClickCounter(campaign)
    if campaignCompare == 'None':
        extraCounter = None
    else:
        extraCounter = getCampaignClickCounter(campaignCompare)
    return getClickChart(clickCounter, core_const.TIME_UNIT_MINUTE, units,extraCounter=extraCounter,html5=html5)

def getCampaignHourlyClickChart(campaign=None,campaignCompare='None', units=24, html5=False):
    clickCounter = getCampaignClickCounter(campaign)
    if campaignCompare == 'None':
        extraCounter = None
    else:
        extraCounter = getCampaignClickCounter(campaignCompare)
    return getClickChart(clickCounter, core_const.TIME_UNIT_HOUR, units,extraCounter=extraCounter, html5=html5)


def getCampaignDailyClickChart(campaign=None,campaignCompare='None', units=31,week=None,html5=False):
    clickCounter = getCampaignClickCounter(campaign)
    if campaignCompare == 'None':
        extraCounter = None
    else:
        extraCounter = getCampaignClickCounter(campaignCompare)
    if week is None:
        return getClickChart(clickCounter, core_const.TIME_UNIT_DAY, units,extraCounter=extraCounter,html5=html5)
    else:
        return getClickChart(clickCounter, core_const.TIME_UNIT_DAY, units, week=week,extraCounter=extraCounter,html5=html5)


def Chart(request):
    timeRange = request.REQUEST.get("timeRange", TIME_RANGES[1][0])
    infoType = request.REQUEST.get("infoType", INFO_TYPES[0][0])
    reportType = request.GET.get('type',0)
    user = users.get_current_user()
    if user is not None:
        uid = get_user_id()
    else:
        return direct_to_template(request, 'sns/index.html', dict(view = DashBoardControllerView()))
    clickCounter = UserClickCounter.get_or_insert_update(UserClickCounter.keyName(uid), UserClickParent.get_or_insert_parent()) 
        
    form=initial_report_form(request)
    
    return render_to_response("sns/report/list.html", dict(view=ReportControllerView(),
                                                       title='Click-through Chart',
                                                       form=form,
                                                       urlMapping=clickCounter,
                                                       timeRange=timeRange,
                                                       infoType=infoType,
                                                       timeRanges=TIME_RANGES,
                                                       infoTypes=INFO_TYPES,
                                                       reportType=reportType,
                                                       notShowToggle=('True' if(reportType==1 or reportType==2) else 'False'),
                                                       ), context_instance=RequestContext(request))


def surlChartTopform(request):
    params={'surl':request.GET.get('surl','')}
    form=SurlTopForm(initial=params)
    return render_to_response("sns/report/surl/top_form.html",dict(form=form), context_instance=RequestContext(request));

def urlChartTopform(request):
    params={'url':request.GET.get('url','')}
    form=UrlTopForm(initial=params)
    return render_to_response("sns/report/url/top_form.html",dict(form=form), context_instance=RequestContext(request));

def userChartTopform(request):
    return render_to_response("sns/report/user/top_form.html", context_instance=RequestContext(request));

def channelChartTopform(request):
    channel=request.POST.get('channel')
    if channel is not None:
        form=ChannelTopForm(initial={'channel':channel})
    else:
        form=ChannelTopForm()
    if len(form.fields['channel'].choices)==0:
        return render_to_response("sns/report/null_error.html",dict(objType="Twitter account"),context_instance=RequestContext(request));
    else:
        return render_to_response("sns/report/channel/top_form.html",dict(form=form), context_instance=RequestContext(request));

def fchannelChartTopform(request):
    fchannel=request.POST.get('fchannel')
    if fchannel is not None:
        form=FChannelTopForm(initial={'fchannel':fchannel})
    else:
        form=FChannelTopForm()
    if len(form.fields['fchannel'].choices)==0:
        return render_to_response("sns/report/null_error.html",dict(objType="Facebook account"),context_instance=RequestContext(request));
    else:
        return render_to_response("sns/report/fchannel/top_form.html",dict(form=form), context_instance=RequestContext(request));


def feedChartTopform(request):
    feed=request.POST.get('feed')
    if feed is not None:
        form=FeedTopForm(initial={'feed':feed})
    else:
        form=FeedTopForm()
    if len(form.fields['feed'].choices)==0:
        return render_to_response("sns/report/null_error.html",dict(objType="feed"),context_instance=RequestContext(request));
    else:
        return render_to_response("sns/report/feed/top_form.html",dict(form=form), context_instance=RequestContext(request));

def campaignChartTopform(request):
    campaign=request.POST.get('campaign')
    if campaign is not None:
        form=CampaignTopForm(initial={'campaign':campaign})
    else:
        form=CampaignTopForm()
    if len(form.fields['campaign'].choices)==0:
        return render_to_response("sns/report/null_error.html",dict(objType="campaign"),context_instance=RequestContext(request));
    else:
        return render_to_response("sns/report/campaign/top_form.html",dict(form=form), context_instance=RequestContext(request));

def blankDetail(request):
    return render_to_response("sns/report/blank.html", context_instance=RequestContext(request));

def getLifeTimeUnit(time):
    if time<timedelta(days=2):
        unit=core_const.TIME_UNIT_HOUR
        number=time.days*24+time.seconds/3600+2
    else:
        unit=core_const.TIME_UNIT_DAY
        number=time.days+2
    if number < 1:
        number = 1
    return unit,number

def userChartDetailHTML5(request):
    view = ReportControllerView()
    modelUser = get_user()
    uid = modelUser.key().id()
    clickCounter = UserClickCounter.get_or_insert_update(UserClickCounter.keyName(uid), UserClickParent.get_or_insert_parent())    
    timeRange = request.POST["timeRange"]
    timeRange = str_util.strip(timeRange)
    if timeRange is None :
        timeRange = 'day'
        
    if timeRange=='minute':
        response_chart,total = getClickChart(clickCounter, core_const.TIME_UNIT_MINUTE, 60, type='user', html5=True)
        chart_info = response_chart[0]
        feedPieChart = haveFeedPieChart(core_const.TIME_UNIT_MINUTE, 60)
        if feedPieChart:            
            feedPieChart = feedPieChartData(request,core_const.TIME_UNIT_MINUTE,60,html5=True)
        channelPieChart = haveChannelPieChart(core_const.TIME_UNIT_MINUTE, 60)
        if channelPieChart:    
            channelPieChart = channelPieChartData(request,core_const.TIME_UNIT_MINUTE,60,html5=True)
    elif timeRange=='day':
        response_chart,total = getClickChart(clickCounter, core_const.TIME_UNIT_HOUR, 24, type='user', html5=True)
        chart_info = response_chart[0]
        feedPieChart = haveFeedPieChart(core_const.TIME_UNIT_HOUR, 24)
        if feedPieChart:
            feedPieChart = feedPieChartData(request,core_const.TIME_UNIT_HOUR,24,html5=True)
        channelPieChart = haveChannelPieChart(core_const.TIME_UNIT_HOUR, 24)
        if channelPieChart: 
            channelPieChart = channelPieChartData(request,core_const.TIME_UNIT_HOUR,24,html5=True)
    elif timeRange=='week':
        response_chart,total = getClickChart(clickCounter, core_const.TIME_UNIT_DAY, units=7,week="week", type='user', html5=True)
        chart_info = response_chart[0]
        feedPieChart = haveFeedPieChart(core_const.TIME_UNIT_DAY, 7)
        if feedPieChart:
            feedPieChart = feedPieChartData(request,core_const.TIME_UNIT_DAY,7,html5=True)
        channelPieChart = haveChannelPieChart(core_const.TIME_UNIT_DAY, 7)
        if channelPieChart: 
            channelPieChart = channelPieChartData(request,core_const.TIME_UNIT_DAY,7,html5=True)
    elif timeRange=='month':
        response_chart,total = getClickChart(clickCounter, core_const.TIME_UNIT_DAY, units=31, type='user', html5=True)
        chart_info = response_chart[0]
        feedPieChart = haveFeedPieChart(core_const.TIME_UNIT_DAY, 31)
        if feedPieChart:
            feedPieChart = feedPieChartData(request,core_const.TIME_UNIT_DAY,31,html5=True)
        channelPieChart = haveChannelPieChart(core_const.TIME_UNIT_DAY, 31)
        if channelPieChart: 
            channelPieChart = channelPieChartData(request,core_const.TIME_UNIT_DAY,31,html5=True)
    else:
        time_length=datetime.utcnow()-modelUser.firstVisit
        unit, number =getLifeTimeUnit(time_length)
    
        response_chart,total = getClickChart(clickCounter, unit, units=number, type='user', html5=True)
        chart_info = response_chart[0]
        feedPieChart = haveFeedPieChart(unit, number)
        if feedPieChart:
            feedPieChart = feedPieChartData(request,unit,number,html5=True)
        channelPieChart = haveChannelPieChart(unit, number)
        if channelPieChart: 
            channelPieChart = channelPieChartData(request,unit,number,html5=True)
                     
    return render_to_response("sns/report/user/his_detail_html5.html", dict(view=view, home=False,total=total,urlMapping=clickCounter, timeRange=timeRange, timeRanges=TIME_RANGES,
                                                                    user=modelUser, chart_info=chart_info, feed_pie_chart_info=feedPieChart, channel_pie_chart_info=channelPieChart, ), context_instance=RequestContext(request))
    

def userChartDetail(request):
    view = ReportControllerView()
    modelUser = get_user()
    uid = modelUser.key().id()
    clickCounter = UserClickCounter.get_or_insert_by_uid_update(UserClickCounter.keyName(uid))    
    timeRange = request.POST["timeRange"]
    timeRange = str_util.strip(timeRange)
    if timeRange is None :
        timeRange = 'day'
        
    if timeRange=='minute':
        channelPieChart = haveChannelPieChart(core_const.TIME_UNIT_MINUTE, 60)
        feedPieChart = haveFeedPieChart(core_const.TIME_UNIT_MINUTE, 60)
        hisChart,total = haveClickChart(clickCounter, core_const.TIME_UNIT_MINUTE, 60, type='user')
    elif timeRange=='day':
        channelPieChart = haveChannelPieChart(core_const.TIME_UNIT_HOUR, 24)
        feedPieChart = haveFeedPieChart(core_const.TIME_UNIT_HOUR, 24)
        hisChart,total = haveClickChart(clickCounter, core_const.TIME_UNIT_HOUR, 24, type='user')
    elif timeRange=='week':
        channelPieChart = haveChannelPieChart(core_const.TIME_UNIT_DAY, units=7)
        feedPieChart = haveFeedPieChart(core_const.TIME_UNIT_DAY, units=7)
        hisChart,total = haveClickChart(clickCounter, core_const.TIME_UNIT_DAY, units=7,week="week", type='user')
    elif timeRange=='month':
        channelPieChart = haveChannelPieChart(core_const.TIME_UNIT_DAY, units=31)
        feedPieChart = haveFeedPieChart(core_const.TIME_UNIT_DAY, units=31)
        hisChart,total = haveClickChart(clickCounter, core_const.TIME_UNIT_DAY, units=31, type='user')
    else:
        time_length=datetime.utcnow()-modelUser.firstVisit
        unit, number =getLifeTimeUnit(time_length)
    
        channelPieChart = haveChannelPieChart(unit, units=number)
        feedPieChart = haveFeedPieChart(unit, units=number)
        hisChart,total = haveClickChart(clickCounter, unit, units=number, type='user')
            
    return render_to_response("sns/report/user/his_detail.html", dict(view=view, home=False,total=total,urlMapping=clickCounter, timeRange=timeRange, timeRanges=TIME_RANGES,
                                                                    user=modelUser, channelPieChart=channelPieChart, feedPieChart=feedPieChart,), context_instance=RequestContext(request))
def userClickChartData(request):
    modelUser = get_user()
    uid = modelUser.key().id()
    clickCounter = UserClickCounter.get_or_insert_update(UserClickCounter.keyName(uid),UserClickParent.get_or_insert_parent())
    timeRange = request.GET.get("timeRange",None)
    timeRange = str_util.strip(timeRange)
    if timeRange is None :
        timeRange = 'day'
                     
    #try:
    if timeRange=='minute':
        hisChart = getClickChart(clickCounter, core_const.TIME_UNIT_MINUTE, 60, type='user')
    elif timeRange=='day':
        hisChart = getClickChart(clickCounter, core_const.TIME_UNIT_HOUR, 24, type='user')
    elif timeRange=='week':
        hisChart = getClickChart(clickCounter, core_const.TIME_UNIT_DAY, units=7,week="week", type='user')
    elif timeRange=='month':
        hisChart = getClickChart(clickCounter, core_const.TIME_UNIT_DAY, units=31, type='user')
    else:
        time_length=datetime.utcnow()-modelUser.firstVisit
        unit, number =getLifeTimeUnit(time_length)
    
        hisChart = getClickChart(clickCounter, unit, units=number, type='user')
                     
    return HttpResponse(hisChart)


def surlChartDetailHTML5(request):
    view = ReportControllerView() 
    urlHash = request.POST["urlHash"]
    timeRange = request.POST["timeRange"]
    timeRange = str_util.strip(timeRange)
    modelUser = get_user()
    if timeRange is None :
        timeRange = 'day'
    
    if urlHash is not None:
        urlHash = urlHash.strip()
        if len(urlHash)==0 :
            urlHash = None
    
    if urlHash == None:
        return blankDetail(request)              
    
    clickCounter = ShortUrlClickCounter.getClickCounter(urlHash)   
    if clickCounter == None:
        return render_to_response("sns/report/error.html", dict(objType='Short URL or keyword'), context_instance=RequestContext(request))      
    if timeRange=='minute':
        response_chart,total = getShortUrlMinutelyClickChart(clickCounter,urlHash,units=60, html5=True)
        chart_info = response_chart[0]
    elif timeRange=='day':
        response_chart,total = getShortUrlHourlyClickChart(clickCounter,urlHash, html5=True)
        chart_info = response_chart[0]
    elif timeRange=='week':
        response_chart,total = getShortUrlDailyClickChart(clickCounter,urlHash, units=7,week="week", html5=True)
        chart_info = response_chart[0]
    elif timeRange=='month':
        response_chart,total = getShortUrlDailyClickChart(clickCounter,urlHash, units=31, html5=True)
        chart_info = response_chart[0]
    else:
        time_length=datetime.utcnow()-ShortUrlClickCounter.getClickCounter(urlHash).createdTime
        unit, number =getLifeTimeUnit(time_length)
        if unit==core_const.TIME_UNIT_HOUR:
            response_chart,total = getShortUrlHourlyClickChart(clickCounter, urlHash, units=number, html5=True)
        else:
            response_chart,total = getShortUrlDailyClickChart(clickCounter, urlHash, units=number, html5=True) 
    
        chart_info = response_chart[0]
        
    if urlHash is None:
        urlHash=""
        
    return render_to_response("sns/report/his_detail_html5.html", dict(view=view, home=False,urlMapping=clickCounter, timeRange=timeRange, timeRanges=TIME_RANGES,
                                                                    user=modelUser, chart_info=chart_info, chart_compare_info="extra_counters" ), context_instance=RequestContext(request))

def surlChartDetail(request):
    urlHash = request.POST["urlHash"]
    timeRange = request.POST["timeRange"]
    timeRange = str_util.strip(timeRange)
    if timeRange is None :
        timeRange = 'day'
    
    if urlHash is not None:
        urlHash = urlHash.strip()
        if len(urlHash)==0 :
            urlHash = None
    
    if urlHash == None:
        return blankDetail(request)
 
    view = ReportControllerView()
    clickCounter = ShortUrlClickCounter.getClickCounter(urlHash) 
    if timeRange=='minute':
        hisChart = haveClickChart(clickCounter, core_const.TIME_UNIT_MINUTE, units=60)        
    elif timeRange=='day':
        hisChart = haveClickChart(clickCounter, core_const.TIME_UNIT_HOUR,24)
    elif timeRange=='week':
        hisChart = haveClickChart(clickCounter, core_const.TIME_UNIT_DAY, units=7,week="week")
    elif timeRange=='month':
        hisChart = haveClickChart(clickCounter, core_const.TIME_UNIT_DAY, units=31)
    else:
        time_length=datetime.utcnow()-ShortUrlClickCounter.getClickCounter(urlHash).createdTime
        unit, number =getLifeTimeUnit(time_length)
        if unit==core_const.TIME_UNIT_HOUR:
            hisChart = haveClickChart(clickCounter, unit, units=number)
        else:
            hisChart = haveClickChart(clickCounter, unit, units=number)            
    
    if urlHash is None:
        urlHash=""
    
    return render_to_response("sns/report/surl/his_detail.html", dict(view=view, urlMapping=clickCounter, timeRange=timeRange, timeRanges=TIME_RANGES, hisChart=hisChart, timerange_urlhash=timeRange+" "+urlHash), context_instance=RequestContext(request));

def surlClickChartData(request):
    timeRange = request.GET.get("timerange_urlhash").split(" ")[0]
    urlHash = request.GET.get("timerange_urlhash").split(" ")[1]
    timeRange = str_util.strip(timeRange)
    if timeRange is None :
        timeRange = 'day'
    if urlHash is not None:
        if len(urlHash)!=0 :
            urlHash = urlHash.strip()
        else:
            urlHash = None        
    clickCounter = ShortUrlClickCounter.getClickCounter(urlHash)
    
    if timeRange=='minute':
        hisChart = getShortUrlMinutelyClickChart(clickCounter,urlHash,units=60)
    elif timeRange=='day':
        hisChart = getShortUrlHourlyClickChart(clickCounter,urlHash)
    elif timeRange=='week':
        hisChart = getShortUrlDailyClickChart(clickCounter,urlHash, units=7,week="week")
    elif timeRange=='month':
        hisChart = getShortUrlDailyClickChart(clickCounter,urlHash, units=31)
    else:            
        time_length=datetime.utcnow()-ShortUrlClickCounter.getClickCounter(urlHash).createdTime
        unit, number =getLifeTimeUnit(time_length)
        if unit==core_const.TIME_UNIT_HOUR:
            hisChart = getShortUrlHourlyClickChart(clickCounter, urlHash, units=number)
        else:
            hisChart = getShortUrlDailyClickChart(clickCounter, urlHash, units=number)             
    return HttpResponse(hisChart)

def channelChartDetail(request):
    try:
        channel = request.POST["channel"]
        channelCompare = request.POST["channelCompare"]
        timeRange = request.POST.get("timeRange")
        timeRange = str_util.strip(timeRange)
        if timeRange is None :
            timeRange = 'day'
        
        if channel is not None:
            channel = channel.strip()
            if len(channel)==0 :
                channel = None
    
        view = ReportControllerView()
        clickCounter = getChannelClickCounter(channel)
        if timeRange=='minute':
            hisChart = haveClickChart(clickCounter, core_const.TIME_UNIT_MINUTE, 60)
        elif timeRange=='day':
            hisChart = haveClickChart(clickCounter, core_const.TIME_UNIT_HOUR, 24)
        elif timeRange=='week':
            hisChart = haveClickChart(clickCounter, core_const.TIME_UNIT_DAY, units=7,week="week")
        elif timeRange=='month':
            hisChart = haveClickChart(clickCounter, core_const.TIME_UNIT_DAY, units=31)
        else:
            time_length=datetime.utcnow()-clickCounter.createdTime
            unit, number =getLifeTimeUnit(time_length)
        
            hisChart = haveClickChart(clickCounter, unit, units=number)
        
        if channel is None:
            channel = ""
        if channelCompare is None:
            channelCompare = ""
            
        return render_to_response("sns/report/channel/his_detail.html", dict(hisChart=hisChart, view=view, urlMapping=clickCounter, timeRange=timeRange, timeRanges=TIME_RANGES, timerange_channel_comparechannel=timeRange+" "+channel+" "+channelCompare), context_instance=RequestContext(request));
    except:
        return blankDetail(request)

def channelClickChartData(request):
    re = request.GET.get("timerange_channel_comparechannel").split(" ")
    timeRange = re[0]
    channel = re[1]
    channelCompare = re[2]
    timeRange = str_util.strip(timeRange)
    if timeRange is None :
        timeRange = 'day'
    if channel is not None:
        channel = channel.strip()
        if len(channel)==0 :
            channel = None 
    if channelCompare is not None:
        if len(channelCompare)==0 :
            channelCompare = None 
            
    clickCounter = getChannelClickCounter(channel)     
    if timeRange=='minute':
        hisChart = getChannelMinutelyClickChart(channel,channelCompare,units=60)
    elif timeRange=='day':
        hisChart = getChannelHourlyClickChart(channel,channelCompare)
    elif timeRange=='week':
        hisChart = getChannelDailyClickChart(channel,channelCompare, units=7,week="week")
    elif timeRange=='month':
        hisChart = getChannelDailyClickChart(channel,channelCompare, units=31)
    else:            
        time_length=datetime.utcnow()-clickCounter.createdTime
        unit, number =getLifeTimeUnit(time_length)
        
        if unit==core_const.TIME_UNIT_HOUR:
            hisChart = getChannelHourlyClickChart(channel,channelCompare, units=number)
        else:
            hisChart = getChannelDailyClickChart(channel,channelCompare, units=number)  
    return HttpResponse(hisChart) 

def channelChartDetailHTML5(request):
    try:
        modelUser=get_user()
        channel = request.POST["channel"]
        channelCompare = request.POST["channelCompare"]
        timeRange = request.POST.get("timeRange")
        timeRange = str_util.strip(timeRange)
        if timeRange is None :
            timeRange = 'day'
        
        if channel is not None:
            channel = channel.strip()
            if len(channel)==0 :
                channel = None
    
        view = ReportControllerView()
        clickCounter = getChannelClickCounter(channel)
        
        if timeRange=='minute':
            response_chart,total = getChannelMinutelyClickChart(channel,channelCompare,units=60, html5=True)
        elif timeRange=='day':
            response_chart,total = getChannelHourlyClickChart(channel,channelCompare, html5=True)
        elif timeRange=='week':
            response_chart,total = getChannelDailyClickChart(channel,channelCompare, units=7,week="week", html5=True)
        elif timeRange=='month':
            response_chart,total = getChannelDailyClickChart(channel,channelCompare, units=31, html5=True)
        else:
            time_length=datetime.utcnow()-clickCounter.createdTime
            unit, number =getLifeTimeUnit(time_length)
            if unit==core_const.TIME_UNIT_HOUR:
                response_chart,total = getChannelHourlyClickChart(channel,channelCompare, units=number, html5=True)
            else:
                response_chart,total = getChannelDailyClickChart(channel,channelCompare, units=number, html5=True)  
        
        chart_info = response_chart[0]
        chart_compare_info = response_chart[1]
            
        return render_to_response("sns/report/his_detail_html5.html", dict(view=view, home=False,urlMapping=clickCounter, timeRange=timeRange, timeRanges=TIME_RANGES,
                                                                        user=modelUser, chart_info=chart_info, chart_compare_info=chart_compare_info ), context_instance=RequestContext(request))
    except:
        return blankDetail(request)          
    

def fchannelChartDetail(request):
    try:
        fchannel = request.POST["fchannel"]
        fchannelCompare = request.POST["fchannelCompare"]
        timeRange = request.POST.get("timeRange")
        timeRange = str_util.strip(timeRange)
        if timeRange is None :
            timeRange = 'day'
        
        if fchannel is not None:
            fchannel = fchannel.strip()
            if len(fchannel)==0 :
                fchannel = None
                
        view = ReportControllerView()
            
        if fchannel:
            fchannelModel=db.get(fchannel)  
            clickCounter,type = getFAccountClickCounter(fchannelModel)
            if timeRange=='minute':
                hisChart = haveClickChart(clickCounter, core_const.TIME_UNIT_MINUTE, 60)
            elif timeRange=='day':
                hisChart = haveClickChart(clickCounter, core_const.TIME_UNIT_HOUR, 24)
            elif timeRange=='week':
                hisChart = haveClickChart(clickCounter, core_const.TIME_UNIT_DAY, units=7,week="week")
            elif timeRange=='month':
                hisChart = haveClickChart(clickCounter, core_const.TIME_UNIT_DAY, units=31)
            else:
                time_length=datetime.utcnow()-clickCounter.createdTime
                unit, number =getLifeTimeUnit(time_length)
            
                hisChart = haveClickChart(clickCounter, unit, units=number)
        else:
            hisChart = 'False'  
            clickCounter = getFAccountClickCounter()  
        if fchannel is None:
            fchannel = ""
        if fchannelCompare is None:
            fchannelCompare = ""
            
        return render_to_response("sns/report/fchannel/his_detail.html", dict(hisChart=hisChart, view=view, urlMapping=clickCounter, timeRange=timeRange, timeRanges=TIME_RANGES, timerange_fchannel_comparefchannel=timeRange+"..."+fchannel+"..."+fchannelCompare), context_instance=RequestContext(request));
    except:
        return blankDetail(request)  

def fchannelClickChartData(request):
    re = request.GET.get("timerange_fchannel_comparefchannel").split("...")
    timeRange = re[0]
    fchannel = re[1]
    fchannelCompare = re[2]
    timeRange = str_util.strip(timeRange)
    if timeRange is None :
        timeRange = 'day'
    if fchannel is not None:
        fchannel = fchannel.strip()
        if len(fchannel)==0 :
            fchannel = None 
    if fchannelCompare is not None:
        if len(fchannelCompare)==0 :
            fchannelCompare = 'None' 
            
    fchannelModel=db.get(fchannel) 
    clickCounter,type = getFAccountClickCounter(fchannelModel)
    if fchannelCompare != 'None':
        fchannelCompare=db.get(fchannelCompare)
    if timeRange=='minute':
        hisChart = getFAccountMinutelyClickChart(fchannelModel,fchannelCompare,units=60)
    elif timeRange=='day':
        hisChart = getFAccountHourlyClickChart(fchannelModel,fchannelCompare)
    elif timeRange=='week':
        hisChart = getFAccountDailyClickChart(fchannelModel,fchannelCompare, units=7,week="week")
    elif timeRange=='month':
        hisChart = getFAccountDailyClickChart(fchannelModel,fchannelCompare, units=31)
    else:            
        time_length=datetime.utcnow()-clickCounter.createdTime
        unit, number =getLifeTimeUnit(time_length)
        
        if unit==core_const.TIME_UNIT_HOUR:
            hisChart = getFAccountHourlyClickChart(fchannelModel,fchannelCompare, units=number)
        else:
            hisChart = getFAccountDailyClickChart(fchannelModel,fchannelCompare, units=number)  
    return HttpResponse(hisChart)      

def fchannelChartDetailHTML5(request):
    try:
        fchannel = request.POST["fchannel"]
        fchannelCompare = request.POST["fchannelCompare"]
        timeRange = request.POST.get("timeRange")
        timeRange = str_util.strip(timeRange)
        if timeRange is None :
            timeRange = 'day'
        
        if fchannel is not None:
            fchannel = fchannel.strip()
            if len(fchannel)==0 :
                fchannel = None
                
        view = ReportControllerView()
            
        fchannelModel=db.get(fchannel)    
        clickCounter,type = getFAccountClickCounter(fchannelModel)
        if fchannelCompare != 'None':
            fchannelCompare=db.get(fchannelCompare)
            
        if timeRange=='minute':
            response_chart,total = getFAccountMinutelyClickChart(fchannelModel,fchannelCompare,units=60, html5=True)
        elif timeRange=='day':
            response_chart,total = getFAccountHourlyClickChart(fchannelModel,fchannelCompare, html5=True)
        elif timeRange=='week':
            response_chart,total = getFAccountDailyClickChart(fchannelModel,fchannelCompare, units=7,week="week", html5=True)
        elif timeRange=='month':
            response_chart,total = getFAccountDailyClickChart(fchannelModel,fchannelCompare, units=31, html5=True)
        else:
            time_length=datetime.utcnow()-clickCounter.createdTime
            unit, number =getLifeTimeUnit(time_length)
            if unit==core_const.TIME_UNIT_HOUR:
                response_chart,total = getFAccountHourlyClickChart(fchannelModel,fchannelCompare, units=number, html5=True)
            else:
                response_chart,total = getFAccountDailyClickChart(fchannelModel,fchannelCompare, units=number, html5=True)  
        
        chart_info = response_chart[0]
        chart_compare_info = response_chart[1]
            
        return render_to_response("sns/report/his_detail_html5.html", dict(view=view, home=False,urlMapping=clickCounter, timeRange=timeRange, timeRanges=TIME_RANGES, 
                                                                         chart_info=chart_info, chart_compare_info=chart_compare_info ), context_instance=RequestContext(request))
    except:
        return blankDetail(request)            

def feedChartDetail(request):
    feed = request.POST["feed"]
    feedCompare = request.POST["feedCompare"]
    timeRange = request.POST.get("timeRange")
    timeRange = str_util.strip(timeRange)
    if timeRange is None :
        timeRange = 'day'
    
    if feed is not None:
        feed = feed.strip()
        if len(feed)==0 :
            feed = None
    if feedCompare is None:
        feedCompare = ""

    view = ReportControllerView()
        
    if feed:
        feedModel=db.get(feed)
        clickCounter = getFeedClickCounter(feedModel)
        if timeRange=='minute':
            hisChart = haveClickChart(clickCounter, core_const.TIME_UNIT_MINUTE, 60)
        elif timeRange=='day':
            hisChart = haveClickChart(clickCounter, core_const.TIME_UNIT_HOUR, 24)
        elif timeRange=='week':
            hisChart = haveClickChart(clickCounter, core_const.TIME_UNIT_DAY, units=7,week="week")
        elif timeRange=='month':
            hisChart = haveClickChart(clickCounter, core_const.TIME_UNIT_DAY, units=31)
        else:
            time_length=datetime.utcnow()-clickCounter.createdTime
            unit, number =getLifeTimeUnit(time_length)
        
            hisChart = haveClickChart(clickCounter, unit, units=number)
    else:
        hisChart = 'False'    
        clickCounter = getFeedClickCounter()
    if feed is not None:
        feed=feed.replace("http://","charturlreplace")
    else:
        feed=""  
        
    return render_to_response("sns/report/feed/his_detail.html", dict(hisChart=hisChart, view=view, urlMapping=clickCounter, timeRange=timeRange, timeRanges=TIME_RANGES, timerange_feed_comparefeed=timeRange+" "+feed+" "+feedCompare), context_instance=RequestContext(request));

def feedClickChartData(request):
    re = request.GET.get("timerange_feed_comparefeed").split(" ")
    timeRange = re[0]
    feed = re[1]
    feedCompare = re[2]
    timeRange = str_util.strip(timeRange)
    if timeRange is None :
        timeRange = 'day'
    if feed is not None:
        if len(feed)!=0 :
            feed=feed.replace("charturlreplace","http://") 
            feed = feed.strip()
        else:
            feed = None  
            
    feedModel=db.get(feed)    
    clickCounter = getFeedClickCounter(feedModel)
            
    if feedCompare is not None:
        if len(feedCompare)==0 :
            feedCompare = 'None'             
    if feedCompare != 'None':
        feedCompare=db.get(feedCompare)
        
    if timeRange=='minute':
        hisChart = getFeedMinutelyClickChart(feedModel,feedCompare,units=60)
    elif timeRange=='day':
        hisChart = getFeedHourlyClickChart(feedModel,feedCompare)
    elif timeRange=='week':
        hisChart = getFeedDailyClickChart(feedModel,feedCompare, units=7,week="week")
    elif timeRange=='month':
        hisChart = getFeedDailyClickChart(feedModel,feedCompare, units=31)
    else:            
        time_length=datetime.utcnow()-clickCounter.createdTime
        unit, number =getLifeTimeUnit(time_length)
        
        if unit==core_const.TIME_UNIT_HOUR:
            hisChart = getFeedHourlyClickChart(feedModel,feedCompare, units=number)
        else:
            hisChart = getFeedDailyClickChart(feedModel,feedCompare, units=number)       
    return HttpResponse(hisChart) 

def feedChartDetailHTML5(request):
    view = ReportControllerView()
    feed = request.POST["feed"]
    feedCompare = request.POST["feedCompare"]
    timeRange = request.POST.get("timeRange")
    timeRange = str_util.strip(timeRange)
    modelUser = get_user()
    if timeRange is None :
        timeRange = 'day'
    
    if feed is not None:
        feed = feed.strip()
        if len(feed)==0 :
            feed = None

    if feedCompare is not None:
        if len(feedCompare)==0 :
            feedCompare = 'None'             
    if feedCompare != 'None':
        feedCompare=db.get(feedCompare)
        
    feedModel=db.get(feed)
    clickCounter = getFeedClickCounter(feedModel)    
    if timeRange=='minute':
        response_chart,total = getFeedMinutelyClickChart(feedModel,feedCompare,units=60, html5=True)
    elif timeRange=='day':
        response_chart,total = getFeedHourlyClickChart(feedModel,feedCompare, html5=True)
    elif timeRange=='week':
        response_chart,total = getFeedDailyClickChart(feedModel,feedCompare, units=7, week="week", html5=True)
    elif timeRange=='month':
        response_chart,total = getFeedDailyClickChart(feedModel,feedCompare, units=31, html5=True)
    else:
        time_length=datetime.utcnow()-clickCounter.createdTime
        unit, number =getLifeTimeUnit(time_length)
        if unit==core_const.TIME_UNIT_HOUR:
            response_chart,total = getFeedHourlyClickChart(feedModel,feedCompare, units=number, html5=True)
        else:
            response_chart,total = getFeedDailyClickChart(feedModel,feedCompare, units=number, html5=True)
    
    chart_info = response_chart[0]
    chart_compare_info = response_chart[1]
        
    return render_to_response("sns/report/his_detail_html5.html", dict(view=view, home=False,urlMapping=clickCounter, timeRange=timeRange, timeRanges=TIME_RANGES, 
                                                                    user=modelUser, chart_info=chart_info, chart_compare_info=chart_compare_info ), context_instance=RequestContext(request))

def campaignChartDetail(request):
    campaign = request.POST["campaign"]
    campaignCompare = request.POST["campaignCompare"]
    timeRange = request.POST.get("timeRange")
    timeRange = str_util.strip(timeRange)
    view = ReportControllerView()
        
    if timeRange is None :
        timeRange = 'day'
    
    if campaign is not None:
        campaign = campaign.strip()
        if len(campaign)==0 :
            campaign = None
            
    if campaign:
        clickCounter = getCampaignClickCounter(campaign)
        if timeRange=='minute':
            hisChart = haveClickChart(clickCounter, core_const.TIME_UNIT_MINUTE, 60)
        elif timeRange=='day':
            hisChart = haveClickChart(clickCounter, core_const.TIME_UNIT_HOUR, 24)
        elif timeRange=='week':
            hisChart = haveClickChart(clickCounter, core_const.TIME_UNIT_DAY, units=7,week="week")
        elif timeRange=='month':
            hisChart = haveClickChart(clickCounter, core_const.TIME_UNIT_DAY, units=31)
        else:
            time_length=datetime.utcnow()-clickCounter.createdTime
            unit, number =getLifeTimeUnit(time_length)
        
            hisChart = haveClickChart(clickCounter, unit, units=number)
    else:
        hisChart = 'False'    
        clickCounter = getCampaignClickCounter(campaign)
    if campaign is None:
        campaign = ""
    if campaignCompare is None:
        campaignCompare = ""
        
    return render_to_response("sns/report/campaign/his_detail.html", dict(hisChart=hisChart, view=view, urlMapping=clickCounter, timeRange=timeRange, timeRanges=TIME_RANGES, timerange_campaign_comparecampaign=timeRange+" "+campaign+" "+campaignCompare), context_instance=RequestContext(request));

def campaignClickChartData(request):
    re = request.GET.get("timerange_campaign_comparecampaign").split(" ")
    timeRange = re[0]
    campaign = re[1]
    campaignCompare = re[2]
    timeRange = str_util.strip(timeRange)
    if timeRange is None :
        timeRange = 'day'
    if campaign is not None:
        campaign = campaign.strip()
        if len(campaign)==0 :
            campaign = None 
    if campaignCompare is not None:
        if len(campaignCompare)==0 :
            campaignCompare = None 
            
    clickCounter = getCampaignClickCounter(campaign)  
      
    if timeRange=='minute':
        hisChart = getCampaignMinutelyClickChart(campaign,campaignCompare,units=60)
    elif timeRange=='day':
        hisChart = getCampaignHourlyClickChart(campaign,campaignCompare)
    elif timeRange=='week':
        hisChart = getCampaignDailyClickChart(campaign,campaignCompare, units=7,week="week")
    elif timeRange=='month':
        hisChart = getCampaignDailyClickChart(campaign,campaignCompare, units=31)
    else:            
        time_length=datetime.utcnow()-clickCounter.createdTime
        unit, number =getLifeTimeUnit(time_length)
        
        if unit==core_const.TIME_UNIT_HOUR:
            hisChart = getCampaignHourlyClickChart(campaign,campaignCompare, units=number)
        else:
            hisChart = getCampaignDailyClickChart(campaign,campaignCompare, units=number) 
    return HttpResponse(hisChart)


def campaignChartDetailHTML5(request):
    campaign = request.POST["campaign"]
    campaignCompare = request.POST["campaignCompare"]
    timeRange = request.POST.get("timeRange")
    timeRange = str_util.strip(timeRange)
    view = ReportControllerView()
        
    if timeRange is None :
        timeRange = 'day'
    
    if campaign is not None:
        campaign = campaign.strip()
        if len(campaign)==0 :
            campaign = None

    clickCounter = getCampaignClickCounter(campaign)
    
    if timeRange=='minute':
        response_chart,total = getCampaignMinutelyClickChart(campaign,campaignCompare,units=60, html5=True)
    elif timeRange=='day':
        response_chart,total = getCampaignHourlyClickChart(campaign,campaignCompare, html5=True)
    elif timeRange=='week':
        response_chart,total = getCampaignDailyClickChart(campaign,campaignCompare, units=7,week="week", html5=True)
    elif timeRange=='month':
        response_chart,total = getCampaignDailyClickChart(campaign,campaignCompare, units=31, html5=True)
    else:
        time_length=datetime.utcnow()-clickCounter.createdTime
        unit, number =getLifeTimeUnit(time_length)
        if unit==core_const.TIME_UNIT_HOUR:
            response_chart,total = getCampaignHourlyClickChart(campaign,campaignCompare, units=number, html5=True)
        else:
            response_chart,total = getCampaignDailyClickChart(campaign,campaignCompare, units=number, html5=True)  
    
    chart_info = response_chart[0]
    chart_compare_info = response_chart[1]
        
    return render_to_response("sns/report/his_detail_html5.html", dict(view=view, home=False,urlMapping=clickCounter, timeRange=timeRange, timeRanges=TIME_RANGES, 
                                                                     chart_info=chart_info, chart_compare_info=chart_compare_info ), context_instance=RequestContext(request))         

def click_ranking(request):
    timeRange = request.REQUEST.get("timeRange", RANKING_TIME_RANGES[0][0])
    return render_to_response("sns/report/ranking/list.html", dict(view=ReportControllerView(),
                                                               title='Click-through Ranking',
                                                               timeRange=timeRange,
                                                               timeRanges=RANKING_TIME_RANGES), context_instance=RequestContext(request))

def click_ranking_hour_list(request):
    uid = get_user_id()
    return ShortUrlClickCounter.all()\
            .filter('uid',uid)\
            .filter("lastUpdateHour", datetimeparser.intHour(datetime.utcnow()))\
            .order("-hour")

def click_ranking_hour(request):
    urlCountList = click_ranking_hour_list(request)
    
    page=request.GET.get('page','1')
    home=request.GET.get('home','')
    paginate_by=(int(request.GET.get('limit','10')) if home!='' else view_const.DEFAULT_INITIAL_PAGE_SIZE)
    total_number=len(urlCountList)
    total_pages=total_number/paginate_by+1
    if total_pages<int(page):
        page=total_pages
    show_list_info='True'
    if total_number<5:
        show_list_info='False'
    
    params=dict(home=home,view=ReportControllerView(), show_list_info=show_list_info, current_page=str(page), paginate_by= paginate_by,post_path='/graph/clickranking/hour?paginate_by='+str(paginate_by))
    
    return object_list(request, 
                       urlCountList,
                       page=page,
                       extra_context = params,
                       paginate_by=paginate_by, 
                       template_name='sns/report/ranking/hour.html' 
                       )
    
def click_ranking_today_list(request):
    uid = get_user_id()
    return ShortUrlClickCounter.all()\
            .filter('uid',uid)\
            .filter("lastUpdateDay", datetimeparser.intDay(utz_util.to_usertz(datetime.utcnow())))\
            .order("-day")

def click_ranking_today(request):
    urlCountList = click_ranking_today_list(request)
    
    page=request.GET.get('page','1')
    home=request.GET.get('home','')
    paginate_by=(int(request.GET.get('limit','10')) if home!='' else view_const.DEFAULT_INITIAL_PAGE_SIZE)
    total_number=len(urlCountList)
    total_pages=total_number/paginate_by+1
    if total_pages<int(page):
        page=total_pages
    show_list_info='True'
    if total_number<5:
        show_list_info='False'
  
    params=dict(home=home,view=ReportControllerView(), show_list_info=show_list_info, current_page=str(page), paginate_by= paginate_by,post_path='/graph/clickranking/today?paginate_by='+str(paginate_by))
    
    return object_list(request, 
                       urlCountList,                       
                       page=page,
                       extra_context = params,
                       paginate_by=paginate_by, 
                       template_name='sns/report/ranking/today.html' 
                       )
    
def click_ranking_week_list(request):
    uid = get_user_id()
    return ShortUrlClickCounter.all()\
             .filter('uid',uid)\
             .filter("lastUpdateWeek", datetimeparser.intWeek(utz_util.to_usertz(datetime.utcnow())))\
             .order("-week")

def click_ranking_week(request):
    urlCountList = click_ranking_week_list(request)
    
    page=request.GET.get('page','1')
    home=request.GET.get('home','')
    paginate_by=(int(request.GET.get('limit','10')) if home!='' else view_const.DEFAULT_INITIAL_PAGE_SIZE)
    total_number=len(urlCountList)
    total_pages=total_number/paginate_by+1
    if total_pages<int(page):
        page=total_pages
    show_list_info='True'
    if total_number<5:
        show_list_info='False'
   
    params=dict(home=home,view=ReportControllerView(), show_list_info=show_list_info, current_page=str(page), paginate_by= paginate_by,post_path='/graph/clickranking/week?paginate_by='+str(paginate_by))
    
    return object_list(request, 
                       urlCountList,
                       page=page,
                       extra_context = params,
                       paginate_by=paginate_by, 
                       template_name='sns/report/ranking/week.html' 
                       )
    
def click_ranking_month_list(request):
    uid = get_user_id()
    return ShortUrlClickCounter.all()\
            .filter('uid',uid)\
            .filter("lastUpdateMonth", datetimeparser.intMonth(utz_util.to_usertz(datetime.utcnow())))\
            .order("-month")

def click_ranking_month(request):
    urlCountList = click_ranking_month_list(request)
    
    page=request.GET.get('page','1')
    home=request.GET.get('home','')
    paginate_by=(int(request.GET.get('limit','10')) if home!='' else view_const.DEFAULT_INITIAL_PAGE_SIZE)
    total_number=len(urlCountList)
    total_pages=total_number/paginate_by+1
    if total_pages<int(page):
        page=total_pages
    show_list_info='True'
    if total_number<5:
        show_list_info='False'
 
    params=dict(home=home,view=ReportControllerView(), show_list_info=show_list_info, current_page=str(page), paginate_by= paginate_by,post_path='/graph/clickranking/month?paginate_by='+str(paginate_by))
    
    return object_list(request, 
                       urlCountList,
                       page=page,
                       extra_context = params,
                       paginate_by=paginate_by, 
                       template_name='sns/report/ranking/month.html' 
                       )



def click_ranking_life_time_list(request):
    uid = get_user_id()
    return ShortUrlClickCounter.all()\
            .filter('uid',uid)\
            .order("-life")

def click_ranking_life_time(request):
    urlCountList = click_ranking_life_time_list(request)

    page=request.GET.get('page','1')
    home=request.GET.get('home','')
    paginate_by=(int(request.GET.get('limit','10')) if home!='' else view_const.DEFAULT_INITIAL_PAGE_SIZE)
    total_number=len(urlCountList)
    total_pages=total_number/paginate_by+1
    if total_pages<int(page):
        page=total_pages
        
    show_list_info='True'
    if total_number<5:
        show_list_info='False'
  
    params=dict(home=home,view=ReportControllerView(),show_list_info=show_list_info, current_page=str(page), paginate_by= paginate_by,post_path='/graph/clickranking/lifetime?paginate_by='+str(paginate_by))
    return object_list(request, 
                       urlCountList,
                       page=page,
                       extra_context = params,
                       paginate_by=paginate_by, 
                       template_name='sns/report/ranking/life_time.html'
                       )
    


def post_failure(request):
    timeRange = request.REQUEST.get("timeRange", "max")
    form = initial_failure_form(request)
    return render_to_response("sns/report/failure/list.html", dict(view=ReportControllerView(),
                                                               form=form,
                                                               title='Post Failures'), context_instance=RequestContext(request))


def post_failure_list(request, type, obj=None):
    query = iapi(api_const.API_M_POSTING_POST).failedPostQuery()
    if type=='channel':
        query.filter("channel", TAccount.get_by_key_name(TAccount.keyName(obj), ChannelParent.get_or_insert_parent()))
    elif type=='fchannel':
        query.filter('channel', db_core.normalize_2_key(obj))
    elif type=='article':
        query.filter('content', db_core.normalize_2_key(obj))
    elif type=='feed':
        query.filter('content', db_core.normalize_2_key(obj))
    elif type=='campaign':
        query.filter('campaign', db_core.normalize_2_key(obj))
    page = request.GET.get('page', '1')
    paginate_by = view_const.DEFAULT_INITIAL_PAGE_SIZE
    total_number = query.count(10000)
    total_pages = total_number/paginate_by+1
    if total_pages<int(page):
        page = total_pages
    show_list_info='True'
    if total_number<5:
        show_list_info='False'
    params=dict(view=ReportControllerView(), current_page=str(page), paginate_by= paginate_by, show_list_info=show_list_info)
    return object_list(request,
                       query,
                       page=page,
                       extra_context = params,
                       paginate_by=view_const.DEFAULT_INITIAL_PAGE_SIZE, 
                       template_name='sns/report/failure/his_detail.html',
                       )
   

def post_failure_list_all(request):
    return post_failure_list(request, 'all')

def post_failure_list_channel(request):
    channel = request.GET.get('channel','')
    return post_failure_list(request, 'channel', channel)

def post_failure_list_fchannel(request):
    fchannel = request.GET.get('fchannel','')
    return post_failure_list(request, 'fchannel', fchannel)

def post_failure_list_article(request):
    article = request.GET.get('article','')
    return post_failure_list(request, 'article', article)

def post_failure_list_feed(request):
    feed = request.GET.get('feed','')
    return post_failure_list(request, 'feed', feed)

def post_failure_list_campaign(request):
    campaign = request.GET.get('campaign','')
    return post_failure_list(request, 'campaign', campaign)

def post_failure_topform_channel(request):
    form=ChannelFailureTopForm()
    if len(form.fields['channelFailure'].choices)==0:
        return render_to_response("sns/report/null_error.html",dict(objType="Twitter account"),context_instance=RequestContext(request));
    else:
        return render_to_response("sns/report/failure/channel_top_form.html",dict(form=form), context_instance=RequestContext(request));

def post_failure_topform_fchannel(request):
    form=FChannelFailureTopForm()
    if len(form.fields['fchannelFailure'].choices)==0:
        return render_to_response("sns/report/null_error.html",dict(objType="Twitter account"),context_instance=RequestContext(request));
    else:
        return render_to_response("sns/report/failure/fchannel_top_form.html",dict(form=form), context_instance=RequestContext(request));
        
def post_failure_topform_article(request):
    form=MessageFailureTopForm()
    if len(form.fields['articleFailure'].choices)==0:
        return render_to_response("sns/report/null_error.html",dict(objType="message"),context_instance=RequestContext(request));
    else:       
        return render_to_response("sns/report/failure/article_top_form.html",dict(form=form), context_instance=RequestContext(request));

def post_failure_topform_feed(request):
    form=FeedFailureTopForm()
    if len(form.fields['feedFailure'].choices)==0:
        return render_to_response("sns/report/null_error.html",dict(objType="feed"),context_instance=RequestContext(request));
    else:
        return render_to_response("sns/report/failure/feed_top_form.html",dict(form=form), context_instance=RequestContext(request));

def post_failure_topform_campaign(request):
    form=CampaignFailureTopForm()
    if len(form.fields['campaignFailure'].choices)==0:
        return render_to_response("sns/report/null_error.html",dict(objType="campaign"),context_instance=RequestContext(request));
    else:
        return render_to_response("sns/report/failure/campaign_top_form.html",dict(form=form), context_instance=RequestContext(request));

def initial_report_form(request):
    params={}
       
    type = request.GET.get('type','')
    if type:
        params['type']=type
        params['surl_value']=request.GET.get('surl','')
        params['url_value']=urllib.unquote_plus(request.GET.get('url',''))

    feedList = FeedProcessor().query(dict(limit=1))
    if len(feedList)==0 :
        feed = None
    else :
        feed = feedList[0].id
    params['feed']=request.GET.get('feed',feed)
    params['feed_value']=request.GET.get('feed',feed)
    
    campaignList = FeedCampaignProcessor().query(dict(limit=1))
    if len(campaignList)==0 :
        campaign = None
    else :
        campaign = campaignList[0].id
    params['campaign']=request.GET.get('campaign',campaign)
    params['campaign_value']=request.GET.get('campaign',campaign)
    
    directList = QuickMessageCampaignProcessor().query({'nameLower':posting_views.QUICK_POST_RULE_NAME.lower()})
    if len(directList)==0 :
        rule = createDirectRule()
        direct = rule.id
    else :
        direct = directList[0].id
    params['direct_value']=request.GET.get('direct',direct)
    
    channelList = TAccountProcessor().query(dict(limit=1))
    if len(channelList)==0 :
        channel = None
    else :
        channel = channelList[0].keyNameStrip()
    channel_name=request.GET.get('channel',channel)
    params['channel']=channel_name
    params['channel_value']=channel_name
        
    fchannelList = FAccountProcessor().query(dict(limit=1))
    fpageList = FAdminPageProcessor().query(dict(limit=1))
    if len(fchannelList)==0 :
        if len(fpageList)==0:
            fchannel = None
        else:
            fchannel = fpageList[0].id
    else :
        fchannel = fchannelList[0].id
    params['fchannel']=request.GET.get('fchannel',fchannel)
    params['fchannel_value']=request.GET.get('fchannel',fchannel)
            
    form=ReportBasicForm(initial=params)
    return form


def initial_failure_form(request):
    params={}
    channel=''
    article=''
    feed=''
    campaign=''
    fchannel=''

    channels = TAccountProcessor().query(dict(limit=1))
    if len(channels)!=0:
        channel=channels[0].keyNameStrip()
            
    articles = MessageProcessor().query(dict(limit=1))
    if len(articles)!=0:
        article=articles[0].id
        
    feeds = FeedProcessor().query(dict(limit=1))
    if len(feeds)!=0:
        feed=feeds[0].id
    
    campaigns = FeedCampaignProcessor().query(dict(limit=1))
    if len(campaigns)!=0:
        campaign=campaigns[0].id
        
    fchannels = FAccountProcessor().query(dict(limit=1))
    if len(fchannels)!=0:
        fchannel = fchannels[0].id
    else:
        pchannels = FAdminPageProcessor().query(dict(limit=1))
        if len(pchannels)!=0:
            fchannel = pchannels[0].id   
    
    params['channel_failure_value']=channel
    params['fchannel_failure_value']=fchannel
    params['article_failure_value']=article
    params['feed_failure_value']=feed
    params['campaign_failure_value']=campaign
    
    form=FailureBasicForm(initial=params)
    return form    

def userReferrerBarChart(request):
    infoType=request.POST.get("infoType","")
    uid = get_user_id()
    clickCounter=UserClickCounter.get_or_insert_update(UserClickCounter.keyName(uid), UserClickParent.get_or_insert_parent()) 
    barChart=haveReferrerBarChart(clickCounter)
    view = ReportControllerView()
    return render_to_response("sns/report/user/bar_chart.html",dict(barChart=barChart,view=view,infoTypes=INFO_TYPES,infoType=infoType), context_instance=RequestContext(request));

def userCountryBarChart(request):
    infoType=request.POST.get("infoType","")
    uid = get_user_id()
    clickCounter=UserClickCounter.get_or_insert_update(UserClickCounter.keyName(uid), UserClickParent.get_or_insert_parent()) 
    barChart=haveCountryBarChart(clickCounter)
    view = ReportControllerView()
    return render_to_response("sns/report/user/bar_chart.html",dict(barChart=barChart,view=view,infoTypes=INFO_TYPES,infoType=infoType), context_instance=RequestContext(request));

def userBarChartData(request):
    infoType=request.GET.get("infoType","")
    if infoType=="country":
        return HttpResponse(userCountryBarChartData(request))
    elif infoType=="referrer":
        return HttpResponse(userReferrerBarChartData(request))    

def userCountryBarChartData(request):
    uid = get_user_id()
    clickCounter=UserClickCounter.get_or_insert_update(UserClickCounter.keyName(uid), UserClickParent.get_or_insert_parent()) 
    return countryBarChartData(clickCounter)

def userReferrerBarChartData(request):
    uid = get_user_id()
    clickCounter=UserClickCounter.get_or_insert_update(UserClickCounter.keyName(uid), UserClickParent.get_or_insert_parent()) 
    return referrerBarChartData(clickCounter)

def userBarChartHTML5(request):
    view=ReportControllerView()
    infoType=request.POST.get("infoType","")
    uid = get_user_id()
    clickCounter=UserClickCounter.get_or_insert_update(UserClickCounter.keyName(uid), UserClickParent.get_or_insert_parent()) 
    if infoType=="country":                 
        barChart=haveCountryBarChart(clickCounter)
        if barChart=='True':
            barChart=countryBarChartData(clickCounter,html5=True)
    elif infoType=="referrer":         
        barChart=haveReferrerBarChart(clickCounter)
        if barChart=='True':
            barChart=referrerBarChartData(clickCounter,html5=True)
    return render_to_response("sns/report/bar_chart_html5.html",dict(barChart=barChart,view=view,infoTypes=INFO_TYPES,infoType=infoType), context_instance=RequestContext(request));

def userDetailInfo(request):
    infoType=request.POST.get("infoType","")
    uid = get_user_id()
    clickCounter=UserClickCounter.get_or_insert_update(UserClickCounter.keyName(uid), UserClickParent.get_or_insert_parent()) 
    return render_to_response("sns/report/user/info.html",dict(urlMapping=clickCounter,infoTypes=INFO_TYPES,infoType=infoType), context_instance=RequestContext(request));

def surlBarChartData(request):
    response = request.GET.get("infotype_urlhash").split(" ")
    urlHash = response[1]
    infoType = response[0]
    if urlHash is not None:
        if len(urlHash)!=0 :
            urlHash = urlHash.strip()
        else:
            urlHash = None 
    if infoType=="country":
        return HttpResponse(surlCountryBarChartData(urlHash))
    elif infoType=="referrer":
        return HttpResponse(surlReferrerBarChartData(urlHash))    

def surlCountryBarChartData(urlHash):
    clickCounter=ShortUrlClickCounter.getClickCounter(urlHash)
    return countryBarChartData(clickCounter)

def surlReferrerBarChartData(urlHash):
    clickCounter=ShortUrlClickCounter.getClickCounter(urlHash)
    return referrerBarChartData(clickCounter)

def surlReferrerBarChart(request):
    try:
        infoType=request.POST.get("infoType")
        urlHash = request.POST["urlHash"]
        clickCounter=ShortUrlClickCounter.getClickCounter(urlHash)
        barChart=haveReferrerBarChart(clickCounter)
        if urlHash is not None:
            if len(urlHash)!=0 :
                urlHash = urlHash.strip()
            else:
                urlHash = None   
        view = ReportControllerView()
        return render_to_response("sns/report/surl/bar_chart.html",dict(barChart=barChart,view=view,infoTypes=INFO_TYPES,infoType=infoType,infotype_urlhash=infoType+' '+urlHash), context_instance=RequestContext(request));
    except:
        return urlNotFoundView(request)

def surlCountryBarChart(request):
    try:
        infoType=request.POST.get("infoType")
        urlHash = request.POST["urlHash"]
        clickCounter=ShortUrlClickCounter.getClickCounter(urlHash)
        barChart=haveCountryBarChart(clickCounter)
        if urlHash is not None:
            if len(urlHash)!=0 :
                urlHash = urlHash.strip()
            else:
                urlHash = None
        view = ReportControllerView()
        return render_to_response("sns/report/surl/bar_chart.html",dict(barChart=barChart,view=view,infoTypes=INFO_TYPES,infoType=infoType,infotype_urlhash=infoType+' '+urlHash), context_instance=RequestContext(request));
    except:
        return urlNotFoundView(request)

def surlBarChartHTML5(request):
    view=ReportControllerView()
    infoType=request.POST.get("infoType")
    urlHash = request.POST["urlHash"]
    clickCounter=ShortUrlClickCounter.getClickCounter(urlHash)
    if clickCounter == None:
        return blankDetail(request)
    if infoType=="country":         
        barChart=haveCountryBarChart(clickCounter)
        if barChart=='True':
            barChart=countryBarChartData(clickCounter,html5=True)
    elif infoType=="referrer":         
        barChart=haveReferrerBarChart(clickCounter)
        if barChart=='True':
            barChart=referrerBarChartData(clickCounter,html5=True)
    return render_to_response("sns/report/bar_chart_html5.html",dict(barChart=barChart,view=view,infoTypes=INFO_TYPES,infoType=infoType), context_instance=RequestContext(request));


def surlDetailInfo(request):
    try:
        infoType=request.POST.get("infoType")
        urlHash = request.POST["urlHash"]
        clickCounter=ShortUrlClickCounter.getClickCounter(urlHash)
        if clickCounter == None:
            return blankDetail(request)
        globalShortUrl = GlobalShortUrl.get_by_surl(urlHash)
        post=SPost.get_by_key_name(SPost.keyName(urlHash), globalShortUrl.campaignParent)        
    except:
        return surlNotFoundView(request)
    return render_to_response("sns/report/surl/info.html",dict(urlMapping=clickCounter,infoTypes=INFO_TYPES,infoType=infoType,post=post), context_instance=RequestContext(request));

def channelBarChartData(request):
    response = request.GET.get("infotype_channel").split(" ")
    channel = response[1]
    infoType = response[0]
    if infoType=="country":
        return HttpResponse(channelCountryBarChartData(channel))
    elif infoType=="referrer":
        return HttpResponse(channelReferrerBarChartData(channel))    

def channelCountryBarChartData(channel):
    clickCounter=getChannelClickCounter(channel)
    return countryBarChartData(clickCounter)

def channelReferrerBarChartData(channel):
    clickCounter=getChannelClickCounter(channel)
    return referrerBarChartData(clickCounter)

def channelReferrerBarChart(request):
    try:
        infoType=request.POST.get("infoType")
        channel = request.POST["channel"]
        clickCounter=getChannelClickCounter(channel)
        barChart=haveReferrerBarChart(clickCounter)
        view = ReportControllerView()
        return render_to_response("sns/report/channel/bar_chart.html",dict(barChart=barChart,view=view,infoTypes=INFO_TYPES,infoType=infoType,infotype_channel=infoType+" "+channel), context_instance=RequestContext(request))
    except:
        return blankDetail(request)
    
def channelCountryBarChart(request):
    try:
        infoType=request.POST.get("infoType")
        channel = request.POST["channel"]
        clickCounter=getChannelClickCounter(channel)
        barChart=haveCountryBarChart(clickCounter)
        view = ReportControllerView()
        return render_to_response("sns/report/channel/bar_chart.html",dict(barChart=barChart,view=view,infoTypes=INFO_TYPES,infoType=infoType,infotype_channel=infoType+" "+channel), context_instance=RequestContext(request))
    except:
        return blankDetail(request)
 
def channelBarChartHTML5(request):
    try:
        view=ReportControllerView()
        infoType=request.POST.get("infoType")
        channel = request.POST["channel"]
        clickCounter=getChannelClickCounter(channel)
            
        if infoType=="country":         
            barChart=haveCountryBarChart(clickCounter)
            if barChart=='True':
                barChart=countryBarChartData(clickCounter,html5=True)
        elif infoType=="referrer":         
            barChart=haveReferrerBarChart(clickCounter)
            if barChart=='True':
                barChart=referrerBarChartData(clickCounter,html5=True)
        return render_to_response("sns/report/bar_chart_html5.html",dict(barChart=barChart,view=view,infoTypes=INFO_TYPES,infoType=infoType), context_instance=RequestContext(request));
    except:
        return blankDetail(request)

def channelDetailInfo(request):
    try:
        infoType=request.POST.get("infoType")
        channel = request.POST["channel"]
        clickCounter=getChannelClickCounter(channel)
        channelModel=TAccount.get_by_key_name(TAccount.keyName(channel), ChannelParent.get_or_insert_parent())   
        return render_to_response("sns/report/channel/info.html",dict(urlMapping=clickCounter,infoTypes=INFO_TYPES,infoType=infoType,channel=channelModel), context_instance=RequestContext(request));
    except:
        return blankDetail(request)
 
def fchannelBarChartData(request):
    response = request.GET.get("infotype_fchannel").split(" ")
    fchannel = response[1]
    fchannelModel=db.get(fchannel)
    infoType = response[0]
    if infoType=="country":
        return HttpResponse(fchannelCountryBarChartData(fchannelModel))
    elif infoType=="referrer":
        return HttpResponse(fchannelReferrerBarChartData(fchannelModel))    

def fchannelCountryBarChartData(fchannel):
    clickCounter,type=getFAccountClickCounter(fchannel)
    return countryBarChartData(clickCounter)

def fchannelReferrerBarChartData(fchannel):
    clickCounter,type=getFAccountClickCounter(fchannel)
    return referrerBarChartData(clickCounter)

def fchannelReferrerBarChart(request):
    try:
        infoType=request.POST.get("infoType")
        fchannel = request.POST["fchannel"]
        fchannelModel=db.get(fchannel)
        clickCounter,type=getFAccountClickCounter(fchannelModel)
        barChart=haveReferrerBarChart(clickCounter)
        view = ReportControllerView()
        return render_to_response("sns/report/fchannel/bar_chart.html",dict(barChart=barChart,view=view,infoTypes=INFO_TYPES,infoType=infoType,infotype_fchannel=infoType+" "+fchannel), context_instance=RequestContext(request))
    except:
        return blankDetail(request)
 
def fchannelCountryBarChart(request):
    try:
        infoType=request.POST.get("infoType")
        fchannel = request.POST["fchannel"]
        fchannelModel=db.get(fchannel)
        clickCounter,type=getFAccountClickCounter(fchannelModel)
        barChart=haveCountryBarChart(clickCounter)
        view = ReportControllerView()
        return render_to_response("sns/report/fchannel/bar_chart.html",dict(barChart=barChart,view=view,infoTypes=INFO_TYPES,infoType=infoType,infotype_fchannel=infoType+" "+fchannel), context_instance=RequestContext(request))
    except:
        return blankDetail(request)

def fchannelBarChartHTML5(request):
    try:
        view=ReportControllerView()
        infoType=request.POST.get("infoType")
        fchannel = request.POST["fchannel"]
        fchannelModel=db.get(fchannel)
        clickCounter,type=getFAccountClickCounter(fchannelModel)
            
        if infoType=="country":         
            barChart=haveCountryBarChart(clickCounter)
            if barChart=='True':
                barChart=countryBarChartData(clickCounter,html5=True)
        elif infoType=="referrer":         
            barChart=haveReferrerBarChart(clickCounter)
            if barChart=='True':
                barChart=referrerBarChartData(clickCounter,html5=True)
        return render_to_response("sns/report/bar_chart_html5.html",dict(barChart=barChart,view=view,infoTypes=INFO_TYPES,infoType=infoType), context_instance=RequestContext(request));
    except:
        return blankDetail(request)

def fchannelDetailInfo(request):
    try:
        infoType=request.POST.get("infoType")
        fchannel = request.POST["fchannel"]
        fchannelModel=db.get(fchannel)
        clickCounter,type=getFAccountClickCounter(fchannelModel)
        if fchannelModel is None:
            fchannelModel=FAdminPage.get_by_key_name(FAdminPage.keyName(fchannel), ChannelParent.get_or_insert_parent())  
        return render_to_response("sns/report/fchannel/info.html",dict(urlMapping=clickCounter,type=type,infoTypes=INFO_TYPES,infoType=infoType,fchannel=fchannelModel), context_instance=RequestContext(request));
    except:
        return blankDetail(request)   
     
def feedReferrerBarChart(request):
    infoType=request.POST.get("infoType")
    feed = request.POST["feed"]
    feedModel=db.get(feed)
    clickCounter=getFeedClickCounter(feedModel)
    barChart=haveReferrerBarChart(clickCounter)
    if feed is not None:
        feed=feed.replace("http://","charturlreplace")
    else:
        feed="" 
    view = ReportControllerView()
    return render_to_response("sns/report/feed/bar_chart.html",dict(barChart=barChart,view=view,infoTypes=INFO_TYPES,infoType=infoType,infotype_feed=infoType+" "+feed), context_instance=RequestContext(request));
 
def feedCountryBarChart(request):
    infoType=request.POST.get("infoType")
    feed = request.POST["feed"]
    feedModel=db.get(feed)
    clickCounter=getFeedClickCounter(feedModel)
    barChart=haveCountryBarChart(clickCounter)
    if feed is not None:
        feed=feed.replace("http://","charturlreplace")
    else:
        feed=""  
    view = ReportControllerView()
    return render_to_response("sns/report/feed/bar_chart.html",dict(barChart=barChart,view=view,infoTypes=INFO_TYPES,infoType=infoType,infotype_feed=infoType+" "+feed), context_instance=RequestContext(request));

def feedBarChartData(request):
    response = request.GET.get("infotype_feed").split(" ")
    feed = response[1]
    infoType = response[0]
    if feed is not None:
        if len(feed)==0 :
            feed = None 
    feedModel=db.get(feed)
    if infoType=="country":
        return HttpResponse(feedCountryBarChartData(feedModel))
    elif infoType=="referrer":
        return HttpResponse(feedReferrerBarChartData(feedModel))    

def feedCountryBarChartData(feed):
    clickCounter=getFeedClickCounter(feed)    
    return countryBarChartData(clickCounter)

def feedReferrerBarChartData(feed):
    clickCounter=getFeedClickCounter(feed)
    return referrerBarChartData(clickCounter)


def feedBarChartHTML5(request):
    view=ReportControllerView()
    infoType=request.POST.get("infoType")
    feed = request.POST["feed"]
    feedModel=db.get(feed)
    clickCounter=getFeedClickCounter(feedModel)
        
    if infoType=="country":         
        barChart=haveCountryBarChart(clickCounter)
        if barChart=='True':
            barChart=countryBarChartData(clickCounter,html5=True)
    elif infoType=="referrer":         
        barChart=haveReferrerBarChart(clickCounter)
        if barChart=='True':
            barChart=referrerBarChartData(clickCounter,html5=True)
    return render_to_response("sns/report/bar_chart_html5.html",dict(barChart=barChart,view=view,infoTypes=INFO_TYPES,infoType=infoType), context_instance=RequestContext(request));


def feedDetailInfo(request):
    infoType=request.POST.get("infoType")
    feed = request.POST["feed"]
    feedModel=db.get(feed)
    clickCounter=getFeedClickCounter(feedModel)
    feedModel=db.get(feed)
    return render_to_response("sns/report/feed/info.html",dict(urlMapping=clickCounter,infoTypes=INFO_TYPES,infoType=infoType,feed=feedModel), context_instance=RequestContext(request));
       
def campaignReferrerBarChart(request):
    infoType=request.POST.get("infoType")
    campaign = request.POST["campaign"]
    clickCounter=getCampaignClickCounter(campaign)
    barChart=haveReferrerBarChart(clickCounter)
    view = ReportControllerView()
    return render_to_response("sns/report/campaign/bar_chart.html",dict(barChart=barChart,view=view,infoTypes=INFO_TYPES,infoType=infoType,infotype_campaign=infoType+" "+campaign), context_instance=RequestContext(request));

def campaignCountryBarChart(request):
    infoType=request.POST.get("infoType")
    campaign = request.POST["campaign"]
    clickCounter=getCampaignClickCounter(campaign)
    barChart=haveCountryBarChart(clickCounter)
    view = ReportControllerView()
    return render_to_response("sns/report/campaign/bar_chart.html",dict(barChart=barChart,view=view,infoTypes=INFO_TYPES,infoType=infoType,infotype_campaign=infoType+" "+campaign), context_instance=RequestContext(request));
 
def campaignBarChartData(request):
    response = request.GET.get("infotype_campaign").split(" ")
    campaign = response[1]
    infoType = response[0]
    if infoType=="country":
        return HttpResponse(campaignCountryBarChartData(campaign))
    elif infoType=="referrer":
        return HttpResponse(campaignReferrerBarChartData(campaign))    

def campaignCountryBarChartData(campaign):
    clickCounter=getCampaignClickCounter(campaign)
    return countryBarChartData(clickCounter)


def campaignReferrerBarChartData(campaign):
    clickCounter=getCampaignClickCounter(campaign)
    return referrerBarChartData(clickCounter)

def campaignBarChartHTML5(request):
    view=ReportControllerView()
    infoType=request.POST.get("infoType")
    campaign = request.POST["campaign"]
    clickCounter=getCampaignClickCounter(campaign)
        
    if infoType=="country":         
        barChart=haveCountryBarChart(clickCounter)
        if barChart=='True':
            barChart=countryBarChartData(clickCounter,html5=True)
    elif infoType=="referrer":         
        barChart=haveReferrerBarChart(clickCounter)
        if barChart=='True':
            barChart=referrerBarChartData(clickCounter,html5=True)
    return render_to_response("sns/report/bar_chart_html5.html",dict(barChart=barChart,view=view,infoTypes=INFO_TYPES,infoType=infoType), context_instance=RequestContext(request));


def campaignDetailInfo(request):
    infoType=request.POST.get("infoType")
    campaign = request.POST["campaign"]
    clickCounter=getCampaignClickCounter(campaign)
    campaignModel=db.get(campaign) if campaign else None
    return render_to_response("sns/report/campaign/info.html",dict(urlMapping=clickCounter,infoTypes=INFO_TYPES,infoType=infoType,campaign=campaignModel), context_instance=RequestContext(request));
  
def surlNotFoundView(request):
    return render_to_response("sns/report/error.html",dict(objType="urlHash"),context_instance=RequestContext(request));

def urlNotFoundView(request):
    return render_to_response("sns/report/error.html",dict(objType="url"),context_instance=RequestContext(request));

def referrerDetail(request):
    return render_to_response("sns/report/referrer_detail.html", context_instance=RequestContext(request));
    
def createDirectRule():
    api_params = {}
    api_params['name'] = posting_views.QUICK_POST_RULE_NAME
    api_params['gaUseCampaignName'] = False
    api_params['gaCampaign'] = 'Quick Post'
    api_params['fbPostStyle']= common_const.FACEBOOK_POST_TYPE_QUICK
    rule = iapi(api_const.API_M_POSTING_RULE_QUICK).create(api_params)
    return rule
    
def directPostRecord(request):
    directList = QuickMessageCampaignProcessor().query({'nameLower':posting_views.QUICK_POST_RULE_NAME.lower()})
    if len(directList)==0 :
        rule = createDirectRule()
    else :
        rule = directList[0]
    result=iapi(api_const.API_M_POSTING_POSTING).query_base().ancestor(rule).order('-executionTime')
    return object_list(request, 
                       result,paginate_by=view_const.DEFAULT_INITIAL_PAGE_SIZE, 
                       template_name='sns/report/quick_post.html', 
                       extra_context={"ruleid":rule.id, 'view':ControllerView(), 
                                      'post_path':request.path+'?paginate_by='+str(view_const.DEFAULT_INITIAL_PAGE_SIZE),'title':'Quick Post Records'})
    
    
