import datetime

from django import template 

from common import consts as common_const
from common.utils import string as str_util
from sns.serverutils import memcache
from soup.topic.api import get_topic_name_by_key
from cake import consts as cake_const


register = template.Library()   

@register.filter('articleCountInfo')    
def articleCountInfo(articleInfo):
    counter = articleInfo.counter
    format =    "Click Count: %s; Shared Count: %s; Score: %s "
    return format % (counter.c365d, counter.sharedCount, counter.hotScore())
    

@register.filter('cakeTopicName') 
def cakeTopicName(key):
    return get_topic_name_by_key(key)

@register.filter('topicClass')    
def topicClass(topicName):
    if topicName is None or len(topicName)<11 :
        return "topic-length-1"
    elif len(topicName)<14 :
        return "topic-length-2"
    elif len(topicName)<17 :
        return "topic-length-3"
    else :
        return "topic-length-4"
 
@register.filter('topicSlice')    
def topicSlice(topicName):
    """
    Returns a slice of the list.
    """
    try:        
        return str_util.slice(topicName, '0:18')
    except (ValueError, TypeError):
        return topicName # Fail silently.

@register.filter('isImage')
def isImage(type):
    ''' Compare GlobalUrlCounter.mediaType with MEDIA_TYPE_IMAGE '''
    return type == common_const.MEDIA_TYPE_IMAGE

@register.filter('isVideo')
def isVideo(type):
    ''' Compare GlobalUrlCounter.mediaType with MEDIA_TYPE_VIDEO '''
    return type == common_const.MEDIA_TYPE_VIDEO