'''
Created on 2009-11-29

@author: alanxing
'''
from google.appengine.ext import deferred as gae_deferred

import context

def defer(func, *args, **kwargs) :
    if context.is_dev_mode() :
        if kwargs.has_key('queueName'):
            kwargs.pop('queueName')
        return func(*args, **kwargs)
    else :
        if kwargs.has_key('queueName'):
            queueName = kwargs['queueName']
            kwargs.pop('queueName')
        else:
            queueName = 'default'
        return gae_deferred.defer(func, _queue=queueName ,*args, **kwargs)


    
