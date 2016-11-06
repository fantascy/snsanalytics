import logging

from google.appengine.api import users
from django.http import HttpResponse
import json
import context


class ApiFacade(object):
    def __init__(self, api_const, api_error, api_processor_map):
        self.api_const = api_const
        self.api_error = api_error
        self.api_processor_map = api_processor_map
        
    def iapi(self, moduleName, login_required=True):
        """
        Returns the internal API processor for given module.
        """
        try :
            return self.api_processor_map[moduleName]()
        except self.api_error.ApiError, a_e:
            raise a_e

    def route(self, request, url):
        """
        This is the single function that routes all external API requests.
        """
        error = None
        try :
            return self._route(request, url)
        except self.api_error.ApiError, a_e:
            error = a_e
            logging.exception("API error!")
        except Exception, e:
            error = self.api_error.ApiError(self.api_error.API_ERROR_UNKNOWN, "Root error is type '%s' with original message: '%s'." % (e.__class__, e.message))
            logging.exception("Unknown API error!")
        
        ret_msg = json.dumps(dict(error_code=error.error_code,error_msg=str(error)), indent=4)
        return HttpResponse(ret_msg, mimetype='application/json')    
        
    def _route(self, request, url):
        """
        This is the routing function without exception handling.
        """
        operationIndex = url[:-1].rfind('/')
        processorPath = url[:operationIndex]
        processor = self.api_processor_map.get(processorPath.lower()) 
        operation = url[operationIndex+1:].rstrip('/').lower()
    
        http_methods, is_admin, is_cron = self.api_const.get_api_operation_perms(operation)
    
        if is_cron and users.get_current_user() is not None and not users.is_current_user_admin() :
            raise self.api_error.ApiError(self.api_error.API_ERROR_ADMIN_OPERATION, operation)
    
        if is_admin and not is_cron and not users.is_current_user_admin():
            raise self.api_error.ApiError(self.api_error.API_ERROR_ADMIN_OPERATION, operation)
                
        if request.method not in http_methods:
            raise self.api_error.ApiError(self.api_error.API_ERROR_INVALID_HTTP_METHOD, request.method, operation)
    
        if is_cron :
            context.get_context().set_login_required(False)
            
        return self._process(request, processor(), operation)
    
    @classmethod
    def _convertMergeDict(cls, mergeDict):
        newDict = {}
        for key in dict(mergeDict.items()).keys() :
            l = mergeDict.getlist(key)
            if len(l)>1 :
                newDict[key] = l
            else :
                try :
                    el = eval(l[0])
                    if type(el)==list :
                        newDict[key] = el
                    else :
                        newDict[key] = l[0]
                except :
                    newDict[key] = l[0]
        return newDict
        
    def _process(self, request, processor, operation):
        """
        This is the single function that processes all external API requests.
        For now, we support request formats of 'json' and 'plain'. 
        For 'plain' format, we don't support multiple values for the same param key.  
        For now, we only support response format of 'json'. Other response formats like 'xml' will be supported in the future.  
        """
        
        params = request.REQUEST.get('json', None)
        if params is None :
            params = ApiFacade._convertMergeDict(request.REQUEST)
        else :
            params=params
            params = json.loads(params)
    
        resp_body = processor.call(operation, params, 'json')
        return HttpResponse(resp_body, mimetype='application/json')    


if __name__ == '__main__':
    pass