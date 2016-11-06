'''
Created on 2010-2-7

@author: sona
'''

from django import template 


register = template.Library()

@register.filter('executingState')
def executingState(value):
    if value==0:
        return 'Initial'
    elif value == 1:
        return 'Finished'
    elif value == 2:
        return 'Failed' 
    elif value == 3:
        return 'Executing'
    elif value == 4:
        return 'Suspend' 