import datetime
import logging

from django import template 
from sns.serverutils import memcache
from soup import consts as soup_const
from soup.commonutils.cookie import fbCookieName
from soup.user import consts as user_const
from soup.topic.api import get_topic_name_by_key


register = template.Library()   


@register.filter('loginStatus')    
def loginStatus(view):
    request = view.ctx().request()
    fb_key = fbCookieName()
    cookie = request.COOKIES
    if cookie.has_key(fb_key):  
        return 1
    else:
        return 0
    

@register.filter('displayMediaTypeName')    
def displayMediaTypeName(mediaType):
    return soup_const.MEDIA_TYPE_DISPLAY_NAME[mediaType]
 

@register.filter('displayVideoImg')    
def displayVideoImg(img):
    if img is None:
        return "http://cdn4.diggstatic.com/img/items/image_t.716b8023.png"
    else:
        return img
 

@register.filter('displayBio')    
def displayBio(bio):
    if bio is None:
        return "Bio is not supplied yet."
    else:
        return bio
 

@register.filter('timeAgo')    
def timeAgo(time):
    if time is None or time=='' or datetime.datetime.utcnow() < time:
        return 'unknown time'
    delta = datetime.datetime.utcnow() - time
    days = delta.days
    seconds = delta.seconds
    months = days/30
    days = days - months*30
    hours = seconds/3600
    minutes = (seconds - 3600*hours)/60
    display = ''
    if months >= 1:
        display += _timeStr(months,'month')
    elif days >= 1:
        display += _timeStr(days,'day')
    elif hours >= 1 :
        display += _timeStr(hours,'hour')
    elif minutes >=1 :
        display += _timeStr(minutes,'minute')
    else:
        display += 'less than a minute'
    return display + ' ago'
        
        
def _timeStr(number,unit):
    info = str(number) + ' ' + unit
    if number > 1:
        info += 's'
    return info


@register.filter('rankType')    
def rankType(rtype):
    return soup_const.RANK_TYPE_MAP.get(rtype)


@register.filter('articleUrl')    
def articleUrl(articleInfo):
    globalUrl = articleInfo.globalUrl()
    if globalUrl is None :
        logging.error("Global URL is none for counter: %s" % articleInfo.counter.url())
    if articleInfo.counter.mediaType == soup_const.MEDIA_TYPE_VIDEO :
        return "/soup/%s" % globalUrl.titleKey
    else :
        return globalUrl.url()


@register.filter('articleListTypeStr')    
def articleListTypeStr(atype):
    return user_const.USER_OBJ_LIST_MAP[int(atype)]


@register.filter('articleFollowAction')    
def articleFollowAction(followed):
    if followed :
        return 'Unfollow'
    else :
        return 'Follow'


@register.filter('userRating')    
def userRating(urlKey):
    from soup.api import consts as api_const
    from soup.api.facade import iapi
    userRating = iapi(api_const.SOUP_API_M_USER).get_article_rating({'id':urlKey})
    if userRating is None :
        return None
    else :
        return userRating
    
    
@register.filter('userRatingLabel')    
def userRatingLabel(rating, ratingCount):
    from soup.user.models import UserArticleRating
    if type(rating)==UserArticleRating :
        rating = rating.rating
    if ratingCount==0 :
        return "Be the first to rate:"
    if rating is None or rating=='' or rating==0 :
        return "Your rating:"
    else :
        return "Your rating:"


@register.filter('ratingIconClass')    
def ratingIconClass(rating, iconId):
    """
    rating - from 0 to 5; can be fractional like 4.3
    iconId - from 1 to 5 
    """
    from soup.user.models import UserArticleRating
    if type(rating)==UserArticleRating :
        rating = rating.rating
    if rating is None or rating == '' or rating+1 <= iconId:
        return "icon-16-star-empty"
    elif rating >= iconId:
        return "icon-16-star-full"
    else :
        return "icon-16-star-half"
    

@register.filter('uiStateClass')    
def uiStateClass(currentValue, targetValue):
    if currentValue==targetValue :
        return "ui-state-active"
    else :
        return "ui-state-default"

@register.filter('autoPlay')    
def autoPlay(url):
    if url.startswith('http://www.youtube.com'):
        url += '&autoplay=1'
    elif url.startswith('http://vimeo.com'):
        url += '&autoplay=1'
    elif url.startswith('http://www.metacafe.com'):
        url += '?autoPlay=true'
    elif url.startswith('http://www.dailymotion.com'):
        url += '?autoPlay=1'
    return url

@register.filter('videoUrlConvert')
def videoUrlConvert(url):
    if url is None :
        return None
    if url.startswith('http://player.vimeo.com'):
        s = url.split('?')[0].split('/')
        vid = s[len(s) - 1]
        url = 'http://vimeo.com/moogaloop.swf?clip_id=' + vid + '&server=vimeo.com'
    return url

@register.filter('soupTopicName') 
def soupTopicName(key):
    return get_topic_name_by_key(key)

@register.filter('friendCount') 
def friendCount(count):
    return count/3

@register.filter('textDisplay') 
def textDisplay(text):
    if text is None:
        return ''
    else:
        while text.find('<') !=-1 :
            begin = text.find('<')
            end = text.find('>')
            if end == -1:
                text = text[:begin]
            elif end < begin :
                text = text[end+1:]
            else:
                text = text[:begin] + text[end+1:]
        return text

@register.filter('getTopCount') 
def getTopCount(counter,info):
    rankRange = info.split(':')[0]
    max_key =  info.split(':')[1]
    sync   = soup_const.TIME_SYNCS[rankRange]
    base = sync(counter)
    max_value = memcache.get(max_key)
    if max_value is None:
        max_value = 0
    return counter.topScore(base, max_value)

@register.filter('getTopClick') 
def getTopClick(counter,info):
    rankRange = info.split(':')[0]
    sync   = soup_const.TIME_SYNCS[rankRange]
    return sync(counter)

@register.filter('pagePath') 
def pagePath(path,page):
    if path.find('?') == -1:
        return path + '?page='+ str(page)
    else:
        return path + '&page='+ str(page)

@register.filter('lessThan')
def lessThan(x, y):
    ''' Return True when x < y '''
    return x < y

@register.filter('greaterThan')
def greaterThan(x, y):
    ''' Return x > y '''
    return x > y

@register.filter('divide')
def divide(x, y):
    ''' Return x / y '''
    return x / y

@register.filter('isNotNone')
def isNotNone(x):
    ''' Return x is not None '''
    return x is not None

@register.filter('firstName')
def firstName(name):
    ''' Return first name '''
    return name.split(' ')[0]

@register.filter('keyId')
def keyId(obj):
    ''' Return key id of object '''
    return obj.key().id()