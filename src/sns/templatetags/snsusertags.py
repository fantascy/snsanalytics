from django import template 
from sns.usr import consts as user_const
from sns.core.core import User

register = template.Library()   

@register.filter('userState') 
def userState(user):
    try:        
        if user.state==user_const.USER_STATE_NOT_APPROVED:
            return 'unapproved'
        elif user.state==user_const.USER_STATE_STANDARD:
            return 'standard'
        elif user.state==user_const.USER_STATE_UNLIMITED:
            return 'unlimited'
        elif user.state==user_const.USER_STATE_ADMIN:
            return 'admin'
        else:
            return 'unknown'
        
    except (ValueError, TypeError):
        return user.state # Fail silently.

@register.filter('userEmail') 
def userEmail(uid):
    try:
        user = User.get_by_id(int(uid))
        return user.mail
    except:
        return ''
