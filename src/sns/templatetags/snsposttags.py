from django import template    
from sns.camp import consts as camp_const

register = template.Library()    
   
@register.filter('state2str')    
def state2str(state):
    """
    Returns the string value of a rule state.
    """
    try:
        if state == camp_const.EXECUTION_STATE_INIT :
            return 'Pending'
        elif state == camp_const.EXECUTION_STATE_FINISH:
            return 'Successful' 
        elif state == camp_const.EXECUTION_STATE_FAILED:
            return 'Failed'      
        
    except (ValueError, TypeError):
        return 'Failed'