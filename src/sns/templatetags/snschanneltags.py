import urllib
import string
from datetime import datetime

from django import template    

from common.utils import timezone as ctz_util, twitter as twitter_util
from sns.chan import consts as channel_const
from snsstringfiltertags import displayNone
from sns.core.core import get_user, ChannelParent, User
from sns.chan.models import TAccount
from common.dateutil.parser import parser
from sns.cont.models import Topic
from sns.core import consts as core_const

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

@register.filter('cutMsgUrl')
def cutMsgUrl(text,length):
    """
    let url can be showed in a new page
    """
    try:  
        length = string.atoi(length)
        pieces = text.split(u'&')
        if len(pieces)>1:
            pieces_cut = []
            for piece in pieces:
                s = piece
                tag = 0
                while True:
                    if len(s) > length:
                        s1 = s[0:length]
                        s2 = s[length:]
                        piece = s1 + "\n"
                        s = s2
                        tag += 1
                    elif len(s) <= length and tag == 0:
                        break
                    else:
                        piece += s
                        break
                pieces_cut.append(piece)
            text = '&amp;'.join(pieces_cut) 
    except:
        pass               
    return text

@register.filter('usertime')
def usertime(time):
    
    """
    Returns the friend add time of a twitter acc
    """
    
    try:
        utcthen=parser().parse(time)
        user = get_user()
        userthen = ctz_util.to_tz(utcthen, user.timeZone)
        
        userthen = datetime(year=userthen.year,month=userthen.month,day=userthen.day,hour=userthen.hour,minute=userthen.minute,second=userthen.second)
        return userthen

    except (ValueError, TypeError):
        return 'Unknown'
    
@register.filter('unquote')   
def unquote(url):
    try:
        return urllib.unquote(url)
    except:
        return url
    
@register.filter('feeddisplay')   
def feeddisplay(feed):
    coding = feed.encoding
    if coding is None or coding == '':
        coding = 'utf-8'
    try:
        url = str(feed.url)
        return urllib.unquote_plus(url).decode(coding) 
    except:
        return feed.url

@register.filter('length')   
def length(list):
    return len(list)

@register.filter('topicName')   
def topicName(keys):
    names = []
    for key in keys:
        topic = Topic.get_by_key_name(Topic.keyName(key))
        if topic is not None:
            names.append(topic.name)
    return ', '.join(names)    

@register.filter('avatarUrl')
def avatarUrl(keyName):
    ''' Get avatarUrl of TAccount from channel stats object keyname. '''
    userID = int(keyName.split(":")[1])
    chId = str(keyName.split(":")[0])
    parent = ChannelParent.get_or_insert_parent(userID)
    taccount = TAccount.get_by_key_name(TAccount.keyName(chId), parent)
    return taccount.avatarUrl

@register.filter('channelFollowStats')   
def channelFollowStats(state):
    if core_const.FOLLOW_STATS_MAP.has_key(state):
        return core_const.FOLLOW_STATS_MAP[state]
    else:
        return 'Unknown'
    
@register.filter('suspendedTime')   
def suspendedTime(channel):
    if channel.suspendedTime is None:
        return channel.modifiedTime
    else:
        return channel.suspendedTime

@register.filter('restoredTime')   
def restoredTime(channel):
    if channel.restoredTime is None:
        return None
    else:
        return channel.restoredTime

@register.filter('statusTime')   
def statusTime(channel, status):
    if status=='suspended':
        return suspendedTime(channel)
    else:
        return restoredTime(channel)

@register.filter('topic')   
def topic(channel):
    if len(channel.topics)>0:
        return '|'.join(channel.topics)
    else:
        return 'None'
    
@register.filter('userEmail')   
def userEmail(channel):
    try:
        uid = channel.parent().uid
        user = User.get_by_id(uid)
        return user.mail
    except:
        return ''
    
@register.filter('feUserEmailIfDiff')   
def feUserEmailIfDiff(stats):
    try:
        if stats.feUserEmail and stats.feUserEmail!=stats.userEmail:
            return stats.feUserEmail
    except:
        pass
    return ''

@register.filter('twitterPeopleSearchUrl')   
def twitterPeopleSearchUrl(term):
    return twitter_util.get_people_search_url(term)
