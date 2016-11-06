
from django import template    

from sns.chan import consts as channel_const
from snsstringfiltertags import displayNone
from datetime import datetime
from common.utils import timezone as ctz_util
from sns.core.core import get_user
from common.dateutil.parser import parser

register = template.Library()    
   
@register.filter('displayNoneAvatar')    
def displayNoneAvatar(value, noneAvatarUrl=channel_const.DEFAULT_TWITTER_AVATAR_URL):
    if noneAvatarUrl is None :
        return displayNone(value)
    return displayNone(value, noneAvatarUrl)

@register.filter('friendTime')     
def friendTime(time):
    """
    Returns the friend add time of a twitter acc
    """
    
    try:
        utcthen=parser().parse(time)
        user = get_user()
        utcnow = datetime.utcnow() 
        usernow = ctz_util.to_tz(utcnow, user.timeZone)
        userthen = ctz_util.to_tz(utcthen, user.timeZone)
        
        dayDiff = (usernow-userthen).days
        secondDiff = (usernow-userthen).seconds
        if dayDiff == 0:
            if secondDiff<60:
                return "right now"
            elif 60<=secondDiff<3600:
                minuteDiff = secondDiff/60
                return str(minuteDiff)+" minutes ago"
            else:
                hourDiff = secondDiff/3600
                return "about "+str(hourDiff)+" hours ago"
        else:
            userthen = datetime(year=userthen.year,month=userthen.month,day=userthen.day,hour=userthen.hour,minute=userthen.minute,second=userthen.second)
            return userthen

    except (ValueError, TypeError):
        return 'Unknown'

@register.filter('twitterUrlize')
def twitterUrlize(text):
    """
    let url can be showed in a new page
    """
    twitterLink=text.replace('<a','<a target="_blank"')
    return twitterLink