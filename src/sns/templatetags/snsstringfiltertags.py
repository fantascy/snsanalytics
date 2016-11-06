from django import template    
from common.utils import string as str_util
from sns.usr import timezone as utz_util
from sns.serverutils import url as url_serverutil 
from common.dateutil.parser import parser
from sns.mgmt import consts as mgmt_const

import urllib

register = template.Library()    
   
@register.filter('slic')    
def slic(value, arg):
    """
    Returns a slice of the list.
    """
    try:        
        return str_util.slice(value, arg)
    except (ValueError, TypeError):
        return value # Fail silently.

@register.filter('diplay_empty_as_empty')    
def diplay_empty_as_empty(value):
    return value if value else ''
    
@register.filter('displayNone')    
def displayNone(value, noneStr='None'):
    """
    Returns a display string for 'value', replace empty and none values to the value of 'noneStr'. 
    """
    try:        
        stripped = str_util.strip(value)
        if stripped is None :
            return noneStr
        else :
            return stripped
    except:
        return value

@register.filter('displayList')    
def displayList(l):
    try:        
        return ', '.join(l)
    except:
        return None

@register.filter('toUserTz')    
def toUserTz(value):
    try:
        if value is None:
            return value
        utc_dt = parser().parse(str(value))
        user_dt = utz_util.to_usertz(utc_dt)
        return user_dt
    except (ValueError, TypeError):
        return value # Fail silently.

@register.filter('getMsg')      
def getMsg(value):
    try:
        index=value.rfind('http://')
        return value[:index]
    except (ValueError, TypeError):
        return value # Fail silently.

@register.filter('shortUrlLongDomain')    
def shortUrlLongDomain(urlhash):
    return url_serverutil.short_url_with_long_domain(urlhash)

@register.filter('addDomain')    
def addDomain(value,domain='http://twitter.com'):
    url = domain + value
    return url

@register.filter('normalize')    
def normalize(s):
    return s.replace(' ', '_')

@register.filter('more')    
def more(page):
    page = int(page)
    if page >= 1000:
        page = str(page) + '+'
    return page

@register.filter('encode')    
def encode(url):
    return urllib.quote(url)

@register.filter('numberDisplay')    
def numberDisplay(number):
    number_string=str(number)
    display_string=''
    while True:
        if len(number_string)>3:
            display_string=','+number_string[-3:]+display_string
            number_string=number_string[:-3]
        else:
            display_string=number_string+display_string
            break
    return display_string

@register.filter('htmlEscape')
def htmlEscape(s):
    s = s.replace('&', '&amp;')
    s = s.replace('<', '&lt;')
    s = s.replace('>', '&gt;')
    s = s.replace('\'', '&acute;')
    s = s.replace('\"', '&quot;')
    return s

@register.filter('monitorMsg')
def monitorMsg(monitor):
    if monitor.work:
        return 'Active'
    else:
        return 'Inactive'

@register.filter('monitorAction')
def monitorAction(monitor):
    if monitor.work:
        return 'Suspend'
    else:
        return 'Resume'
    
@register.filter('feedSources')
def feedSources(fsids):
    from sns.cont.feedsources import FeedSource
    views = []
    for fsid in fsids:
        views.append(FeedSource.get_name(fsid))
    return ','.join(views)

@register.filter('filterDisplay')
def filterDisplay(rule):
    if rule.filterType == mgmt_const.CMP_RULE_FILTER_TYPE_EXCLUDED_USER:
        return 'Excluded user tags: ' + rule.excludedTags
    elif rule.filterType == mgmt_const.CMP_RULE_FILTER_TYPE_INCLUDED_USER:
        return 'Included user tags: ' + rule.includedTags
    elif rule.filterType == mgmt_const.CMP_RULE_FILTER_TYPE_TOPIC:
        return 'Included topics:: ' + rule.filters