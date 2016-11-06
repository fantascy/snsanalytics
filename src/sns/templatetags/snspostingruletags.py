from django import template    
from django.template.defaultfilters import date

from common import consts as common_const
from sns.usr import timezone as utz_util
from sns.camp import consts as camp_const


register = template.Library()    
   

@register.filter('state2str')    
def state2str(state):
    """
    Returns the string value of a rule state.
    """
    try:
        if state == camp_const.CAMPAIGN_STATE_INIT:
            return 'Inactive'
        if state == camp_const.CAMPAIGN_STATE_ACTIVATED:
            return 'Active'
        if state == camp_const.CAMPAIGN_STATE_EXPIRED:
            return 'Finished'
        if state == camp_const.CAMPAIGN_STATE_EXECUTING:
            return 'Executing'
        if state == camp_const.CAMPAIGN_STATE_ERROR:
            return 'Error'
        if state == camp_const.CAMPAIGN_STATE_ONHOLD:
            return 'Unapproved'
        if state == camp_const.CAMPAIGN_STATE_SUSPENDED:
            return 'Suspended'
        return 'Unknown'
    except (ValueError, TypeError):
        return 'Unknown'
    

@register.filter('scheduleType2str')    
def scheduleType2str(scheduleType):
    """
    Returns the string value of a rule state.
    """
    try:
        if scheduleType == camp_const.SCHEDULE_TYPE_NOW:
            return 'Immediate'
        if scheduleType == camp_const.SCHEDULE_TYPE_ONE_TIME:
            return 'One-time'
        if scheduleType == camp_const.SCHEDULE_TYPE_RECURRING:
            return 'Recurring'
        return 'Unknown'
    except (ValueError, TypeError):
        return 'Unknown'


@register.filter('scheduleInfo')     
def scheduleInfo(postingrule):
    """
    Returns the schedule info of a posting rule
    """
    
    try:
        schedule_type = postingrule.getScheduleType()
        if schedule_type == camp_const.SCHEDULE_TYPE_NOW:
            return 'Now'
        if schedule_type == camp_const.SCHEDULE_TYPE_ONE_TIME:
            return 'At %s' % date(utz_util.to_usertz(postingrule.scheduleNext), common_const.UI_DATETIME_FORMAT)
        if schedule_type == camp_const.SCHEDULE_TYPE_RECURRING:
            return 'Every %s' % camp_const.INTERVAL_MAP.get(postingrule.scheduleInterval, None)
    except (ValueError, TypeError):
        return 'Unknown'


@register.filter('gaCampaign') 
def gaCampaign(rule):
    if rule.gaUseCampaignName:
        return rule.name
    else:
        return rule.gaCampaign


@register.filter('followRuleInfo')   
def followRuleInfo(status):
    if status == 0:
        info = 'In white list,running.'
    elif status == 1:
        info = 'No follower count assigned.'
    elif status == 2:
        info = 'Running.'
    elif status == 3:
        info = 'Assigned follower count use up.'
    return info


@register.filter('displayAffix')   
def displayAffix(affixes):
    if affixes is None:
        return 'None'
    return ','.join(affixes.split('SubstituteSymbol'))


@register.filter('dealCount')   
def dealCount(rule):
    return len(rule.contents)

