import logging

from common.utils import datetimeparser
from client import apiclient


class ApiBase(object):
    API_MODULE = None
    QUERY_LIMIT = 500
    
    def __init__(self, obj=None):
        self.obj = obj
        
    def call(self, operation, params=None, fmt='json', http_method=None):
        return apiclient.call_api(apiclient.server_api_domain(), self.API_MODULE, operation, params, fmt, http_method=http_method)

    def create(self, params=None):
        obj = params if params else self.obj
        result = apiclient.call_api(apiclient.server_api_domain(), self.API_MODULE, "create", obj, "json", log=False)
        self.handle_error(result)
        result = self.transform_obj(result)
        return result
    
    def get(self, params=None, fmt='json'):
        result = self.call('get', params, fmt)
        self.handle_error(result)
        result = self.transform_obj(result)
        return result

    def update(self, params=None):
        obj = params if params else self.obj
        result = apiclient.call_api(apiclient.server_api_domain(), self.API_MODULE, "update", obj, "json", log=False)
        self.handle_error(result)
        result = self.transform_obj(result)
        return result
    
    def delete(self, params=None, fmt='json'):
        result = self.call('delete', params, fmt, http_method='POST')
        self.handle_error(result)
        return result

    def admin(self, params=None, fmt='json', http_method=None):
        result = self.call('admin', params, fmt, http_method=http_method)
        self.handle_error(result)
        return result

    def get_id_by_name (self, name):
        matched = self.query(self.API_MODULE, {'name = ':name, 'limit':1}, fmt='plain')
        return matched[0].get('id') if matched else None

    def query(self, params=None):
        return self.execute_query(params)
    
    def query_all(self, params=None):
        return self.execute_query_all(params)
    
    def execute_query(self, params):
        queryParams = params.copy() if params else {}
        curr_page = apiclient.call_api(apiclient.server_api_domain(), self.API_MODULE, 'query_by_cursor', queryParams, "json", log=False)
        self.handle_error(curr_page)
        cursor = curr_page.get('cursor', None)
        objs = curr_page.get('objs', [])
        if len(objs) > 0:
            objs = self.transform_obj_list(objs)
        logging.debug("Returned %d objects and cursor '%s' for query %s." % (len(objs), cursor, str(params)))
        return {'cursor': cursor, 'objs': objs}
    
    def execute_query_all(self, params):
        queryParams = params.copy() if params else {}
        queryParams['limit'] = self.QUERY_LIMIT
        queryParams['query_all']  = True
        results = []
        while True:
            curr_page = apiclient.call_api(apiclient.server_api_domain(), self.API_MODULE, 'query_by_cursor', queryParams, "json", log=False)
            self.handle_error(curr_page)
            cursor = curr_page.get('cursor', None)
            objs = curr_page.get('objs', [])
            if len(objs) > 0:
                self.transform_obj_list(objs)
                results.extend(objs)
                if len(objs)<self.QUERY_LIMIT:
                    break
                else:
                    queryParams['cursor'] = cursor
            else:
                break
        logging.debug("Returned %d results for %s query %s." % (len(results), self.API_MODULE, str(params)))
        return results
    
    def handle_error(self, results):
        if isinstance(results, dict) and results.has_key('error_code'):
            raise Exception("ApiError [error_code=%s] %s" % (results['error_code'], results['error_msg']))

    @classmethod
    def transform_obj(cls, obj):
        return obj
    
    @classmethod
    def transform_obj_list(cls, objs):
        ret_objs = []
        for obj in objs:
            ret_objs.append(cls.transform_obj(obj))
        return ret_objs
    
    @property        
    def key_name(self):
        return self.obj['key_name'].split(":")[-1]
    
    @property
    def key_id(self):
        return self.obj['key_id']

    @property
    def key(self):
        return self.obj['id']

    @property
    def createdTime(self):
        return self._parse_datetime('createdTime')

    @property
    def modifiedTime(self):
        return self._parse_datetime('modifiedTime')

    def _parse_datetime(self, attr):
        time_str = self.obj.get(attr, None) if self.obj else None
        return datetimeparser.parseDateTime(time_str) if time_str else None

    @property        
    def name(self):
        return self.obj['name']
    
    @property        
    def name_lower(self):
        return None if self.name is None else self.name.lower

    
