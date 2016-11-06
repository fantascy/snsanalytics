from django import template    

from sns.camp import consts as camp_const
from sns.templatetags.snspostingruletags import state2str as sns_state2str

register = template.Library()    

@register.filter('state2str')    
def state2str(state):
    if state == camp_const.CAMPAIGN_STATE_ONHOLD:
        return 'Protected'
    else:
        return sns_state2str(state)
    

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

