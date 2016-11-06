from datetime import datetime, timedelta

from django.shortcuts import render_to_response
from django.template import RequestContext
from django.template.defaultfilters import date
from common.ofc2 import openFlashChart
from common.ofc2.openFlashChart_varieties import Line_Dot, value, x_axis_labels
from common.ofc2.openFlashChart_elements import tooltip

from sns.core import consts as core_const
from fe import consts as fe_const


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

MAX_SEARCH_RESULT=5

def getCounterChart(counters,timeUnit,units,startTime,endTime,week=None,extraCounter=None,extraInfo=None,noLabel=False,isClick=True,title="Total Clicks",dot_title="Clicks",type=None,count_type=None):   
    chartstart = datetime(year=startTime.year,month=startTime.month,day=startTime.day,hour=startTime.hour)
    chartend   = datetime(year=endTime.year,month=endTime.month,day=endTime.day,hour=endTime.hour)
    data = counters   
    datetime_format = fe_const.FE_UI_DATETIME_FORMAT

    if timeUnit==core_const.TIME_UNIT_MINUTE:        
        """calculate 60 minute list before now"""  
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
            if num == units:
                break
            num = num + 1
        chartstart = datetime(year=startTime.year,month=startTime.month,day=startTime.day,hour=startTime.hour,minute=startTime.minute)
        chartend   = datetime(year=endTime.year,month=endTime.month,day=endTime.day,hour=endTime.hour,minute=endTime.minute)    
    elif timeUnit==core_const.TIME_UNIT_HOUR :        
        """calculate 24 hour list before now"""    
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
            if num == units:
                break
            num = num + 1
        
        length_data=len(data)
        if length_data>24:
            if length_data<=3*24:
                steps=3
            elif length_data>3*24:
                steps=6
            i=0
            while True:
                if i==length_data:
                    break
                if int(showPoint[i])%steps != 0:
                    showPoint[i]=''
                i+=1                   
    elif timeUnit==core_const.TIME_UNIT_DAY and week is not None : 
        datetime_format = fe_const.FE_UI_DATE_FORMAT      
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
    elif timeUnit==core_const.TIME_UNIT_DAY:     
        datetime_format = fe_const.FE_UI_DATE_FORMAT   
        """calculate n(units) days list before now"""  
        showPoint = []
        showPointDetail = []
        month = {"1":"Jan.","2":"Feb.","3":"Mar.","4":"Apr.","5":"May.","6":"Jun.","7":"Jul.","8":"Aug.","9":"Sep.","10":"Oct.","11":"Nov.","12":"Dec.",}
        num = 1
        if units <= 31:
            '''seperated by 1 day'''
            while True:
                showPointDetail.append(date(endTime, datetime_format))
                showPoint.append(str(endTime.day))
                if num == units:
                    break            
                days = timedelta(days=1)
                endTime = endTime - days
                num = num + 1
        elif 31 < units <= 200:
            '''seperated by 10 days'''
            while True:
                showPointDetail.append(date(endTime, datetime_format))
                if endTime.day%10:
                    if endTime.month==2 and endTime.day==28:
                        showPoint.append(month[str(endTime.month)]+str(endTime.day))
                    else:
                        showPoint.append("")
                else:
                    showPoint.append(month[str(endTime.month)]+str(endTime.day))
                
                if num == units:
                    break            
                days = timedelta(days=1)
                endTime = endTime - days
                num = num + 1
        else: 
            '''seperated by 1 month'''
            while True:
                showPointDetail.append(date(endTime, datetime_format))
                if endTime.day == 1:
                    showPoint.append(month[str(endTime.month)]+str(endTime.day))                    
                else:
                    showPoint.append("")
                
                if num == units:
                    break            
                days = timedelta(days=1)
                endTime = endTime - days
                num = num + 1
    if count_type is None:            
        total = 0
        for i in range(0, len(counters)) :
            total += int(counters[i])
    else:
        if count_type == 'follower_rule':
            total = max(counters)
            
    y_max = max(counters)

    showPointDetail.reverse()
    line_date = []
    for i in range(0,len(counters)):
        if isClick:
            tooltip="Clicks: #val#<br>"+showPointDetail[i]
        else:
            tooltip=dot_title+": #val#<br>"+showPointDetail[i]
        value_line = value(str(counters[i]),'#FFA500',tooltip)
        line_date.append(value_line)
    
    l = Line_Dot(fontsize = 20, values = line_date)      
    l.set_colour('#FF9900')
    #l.set_tooltip('Clicks: #val#<br>#x_label#')
    if extraInfo is not None:
        l.set_text(extraInfo[0])
    l.set_dot_size(getNodeSize(counters))
    l.set_halo_size(0)
    l.set_on_click("getCheckPointTweets")
    showPoint.reverse()
    if type is not None:
        if type=='user':
            chart = openFlashChart.template('')
    else:
        if isClick:
            chart = openFlashChart.template(title+" : " + str(total))
        else:
            chart = openFlashChart.template("Total : " + str(total))  
    chart.set_bg_colour('#FFFFFF') 
    chart.add_element(l) 
    if extraCounter is not None:
        line_date_extra = []
        for i in range(0,len(extraCounter)):
            if isClick:
                tooltip="Clicks: #val#<br>"+showPointDetail[i]
            else:
                tooltip=dot_title+": #val#<br>"+showPointDetail[i]
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
    chart.set_x_axis(labels = x_axis_labels(labels=showPoint), grid_colour = '#E0FFFF')
    chart.set_x_legend("from "+date(chartstart, datetime_format)+" to "+date(chartend, datetime_format)) 
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
        

def getNodeSize(counters):
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

def blankDetail(request):
    return render_to_response("report/blank.html", context_instance=RequestContext(request));

