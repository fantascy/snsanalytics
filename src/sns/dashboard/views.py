import datetime

from django.views.generic.simple import direct_to_template
from django.shortcuts import render_to_response
from django.template import RequestContext

from common.utils import string as str_util
from sns.core import consts as core_const
from sns.core.core import get_user, UserClickParent
from sns.api import consts as api_const
import context 
from sns.api.facade import iapi
from sns.view.controllerview import ControllerView
from sns.usr.models import UserClickCounter,UserExecuteCounter
from sns.report.views import RANKING_TIME_RANGES, TIME_RANGES
from sns.report.views import getClickChart, getLifeTimeUnit


class DashBoardControllerView(ControllerView):
    def __init__(self):
        context.get_context().set_login_required(False)
        ControllerView.__init__(self, viewName="Home")
        

def main(request):
    return direct_to_template(request, 'sns/layout/contents.html', dict(view = DashBoardControllerView()))


def home(request):
    context.get_context().set_login_required(False)
    user = get_user()
    old = request.REQUEST.get('old', False)
    if request.path == '/' and user is not None:
        return direct_to_template(request, 'sns/layout/contents.html', dict(view = DashBoardControllerView()))
    if user is not None:
        userCounters = iapi(api_const.API_M_USER).getUserCounters().update()  
        userDailyPostLimit = iapi(api_const.API_M_USER).getUserDailyPostLimit(dict(user=user))
        remainingLimit = userDailyPostLimit - userCounters.postCounter.day
        timeRange = request.REQUEST.get("timeRange", TIME_RANGES[1][0])
        if remainingLimit <= 0 :
            limited = True
        else:
            limited=False
        userDailyExecutionLimit = iapi(api_const.API_M_USER).getUserDailyExecutionLimit(dict(user=user))
        uid = user.uid
        executionCounter = UserExecuteCounter.get_or_insert(UserExecuteCounter.keyName(uid), parent = user)
        executionCounter.update()
        if executionCounter.day >= userDailyExecutionLimit:
            executionLimited = True
        else:
            executionLimited = False
        userClickCounter = UserClickCounter.get_or_insert_by_uid_update(uid)
        return direct_to_template(request, 'sns/dashboard.html', dict(userCounters = userCounters,
                                                                      clickCounter = userClickCounter,
                                                                    timeRange = timeRange,
                                                                    timeRanges = TIME_RANGES,
                                                                    limited=limited,
                                                                    executionLimited=executionLimited,
                                                                    executionLimit = userDailyExecutionLimit,
                                                                    limit=userDailyPostLimit,
                                                                    timeRangeRanking = 'day',
                                                                    timeRangesRanking = RANKING_TIME_RANGES,
                                                                    view = DashBoardControllerView()))
    elif old:
        return direct_to_template(request, 'sns/old_index.html', dict(view = DashBoardControllerView()))
    else:
        return direct_to_template(request, 'sns/index.html', dict(view = DashBoardControllerView()))


def homeChartDetailHTML5(request):
    view = DashBoardControllerView()
    context.get_context().set_login_required(True)
    modelUser = get_user()
    clickCounter = UserClickCounter.get_or_insert(UserClickCounter.keyName(modelUser.key().id()),parent=UserClickParent.get_or_insert_parent())
     
    timeRange = request.POST["timeRange"]
    timeRange = str_util.strip(timeRange)
    if timeRange is None :
        timeRange = 'day'
         
    #try:
    if timeRange=='minute':
        response_chart,total = getClickChart(clickCounter, core_const.TIME_UNIT_MINUTE, 60, type='user', html5=True)
    elif timeRange=='day':
        response_chart,total = getClickChart(clickCounter, core_const.TIME_UNIT_HOUR, 24, type='user', html5=True)
    elif timeRange=='week':
        response_chart,total = getClickChart(clickCounter, core_const.TIME_UNIT_DAY, units=7,week="week", type='user', html5=True)
    elif timeRange=='month':
        response_chart,total = getClickChart(clickCounter, core_const.TIME_UNIT_DAY, units=31, type='user', html5=True)
    else:
        time_length=datetime.datetime.utcnow()-modelUser.firstVisit
        unit, number =getLifeTimeUnit(time_length)
     
        response_chart,total = getClickChart(clickCounter, unit, units=number, type='user', html5=True)
    chart_info = response_chart[0]
                      
    return render_to_response("sns/report/user/his_detail_html5.html", dict(view=view, home=True,total=total,urlMapping=clickCounter, timeRange=timeRange, timeRanges=TIME_RANGES,
                                                                    user=modelUser, chart_info=chart_info, ), context_instance=RequestContext(request))
     


