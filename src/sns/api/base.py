import datetime
import logging
from sets import ImmutableSet

from google.appengine.ext import db
from google.appengine.api import users

import json

from sns.core import core as db_core
from sns.core.base import parseValue, parseKeyOrModel, validateUniqueness
from sns.api import consts as api_const
from sns.api import errors as api_error
from sns.api.errors import ApiError


def getModelObject(param):
    """
    A convenient function to get the model object based on input param.
    This function always returns the data store state of the model.
    param - either a db.Key, or a dict with the key 'id', or a string as key id
    """
    return db.get(db_core.normalize_2_key(param))
    raise ApiError(api_error.API_ERROR_UNKNOWN, "Could not get model object because of bad input param type: %s !" % type(param))


def createModelObject(model, params):
    """
    A convenient function to create a model object IN MEMORY (Not put to data store).
    model - A subclass of db.Model
    params - A dict with attributes of the give model. The dict has to contain all required fields of the model. Key 'id' is skipped.
    """
    parsedValues = {}  
    properties = model.properties()
    excludeProperties = model.create_exclude_properties()
    if 'nameLower' in properties and 'nameLower' not in params:
        addLowerProperty(params)
        
    for k in properties.keys() :
        if k in excludeProperties or not params.has_key(k) :
            continue
        strValue = params[k]
        parsedValue = parseValue(strValue, properties.get(k))
        parsedValues[k] = parsedValue
    if params.has_key('parent') :
        parsedValues['parent'] = parseKeyOrModel(params.get('parent'))
    if params.has_key('key_name') :
        parsedValues['key_name'] = params['key_name']
    return model(**parsedValues)


def updateModelObject(obj, params):
    """
    A convenient function to create a model object IN MEMORY (Not put to data store).
    obj - An instance of subclass of db.Model
    params - A dict with some attributes of the give model. Key 'id' is skipped.
    """
    properties = obj.properties()
    if 'nameLower' in properties and 'nameLower' not in params:
        addLowerProperty(params)
    excludeProperties = type(obj).update_exclude_properties()
    for k in properties.keys() :
        if k in excludeProperties or not params.has_key(k) :
            continue
        strValue = params[k]
        parsedValue = parseValue(strValue, properties.get(k))
        setattr(obj, k, parsedValue)
    return obj


def deleteModelObject(param):
    """
    A convenient function to delete a model object based on input param.
    param - either a db.Key, or a db.Model, or a dict with the key 'id', or a string as key id
    """
    if isinstance(param, db.Key) :
        return db.delete(param)
    if isinstance(param, db.Model) :
        return db.delete(param)
    if isinstance(param, str) :
        return db.delete(db.Key(param))
    if isinstance(param, dict) :
        return db.delete(db.Key(param['id']))

def addLowerProperty(params, origProperty="name", lowerProperty="nameLower"):
    """
    Add a lower property for case insensitive sorting.
    """
    if params.has_key(origProperty) :
        origPropValue = params[origProperty]
        if origPropValue is None :
            params[lowerProperty] = None
        else :
            params[lowerProperty] = origPropValue.lower()

def smallModelAttributeMap(obj):
    smap = {}
    if hasattr(obj.__class__, 'smallModel') and obj.smallModel is not None :
        for attr in obj.smallModel.syncAttributes() :
            smap[attr] = getattr(obj, attr)
    return smap   
        
class BaseJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime.datetime):
            return str(obj)
        if isinstance(obj, db.Key):
            return self.encodeKey(obj)
        if isinstance(obj, users.User):
            return str(obj.email())
        if isinstance(obj, db.Model):
            return self.encodeModel(obj)
        return json.JSONEncoder.default(self, obj)

    def getExcludedProperties(self, obj):
        if isinstance(obj, db.Model):
            return type(obj).display_exclude_properties()
        else :
            return []
        
    def encodeKey(self, obj):
        return str(obj)

    def encodeModel(self, obj):
        key = obj.key()
        jsonDict = {'id':key, 'key_id': key.id(), 'key_name': key.name()}
        properties = obj.properties()
        for k in properties.keys() :
            if k in self.getExcludedProperties(obj) :
                continue
            jsonDict[k] = properties[k].get_value_for_datastore(obj)
        return jsonDict 
    

class BaseProcessor():
    QUERY_LIMIT = 25
    TIMEOUT_FRONTEND = 55
    TIMEOUT_BACKEND = 595
    TIMEOUT_MARGIN = 5

    def __init__(self, timeout=TIMEOUT_FRONTEND):
        self._request_expire = datetime.datetime.utcnow() + datetime.timedelta(seconds=timeout)

    def isTimeout(self, timeout=TIMEOUT_MARGIN):
        import context
        if context.get_context().skip_timeout() :
            return False
        is_timeout = datetime.datetime.utcnow() + datetime.timedelta(seconds=timeout) > self._request_expire
        if is_timeout :
            logging.info("Request timeout inside %s! Expire time is %s." % (self.__class__.__name__, self._request_expire))
        return is_timeout
      
    def logScheduleDelayStatus(self, oldestScheduleTime, now=datetime.datetime.utcnow()) :
        delta = now - oldestScheduleTime
        msg = "Max scheduled job delay is '%s' in %s." % (delta, self.__class__) 
        if delta > datetime.timedelta(minutes=10) :
            logging.error(msg)
        elif delta > datetime.timedelta(minutes=5) :
            logging.warn(msg)
        elif delta > datetime.timedelta(minutes=3) :
            logging.info(msg)
        else :
            logging.debug(msg)
    
    def create(self, params):
        return db.run_in_transaction(self._trans_create, params)

    def _trans_create(self, params):
        obj = createModelObject(self.getModel(), params)
        obj.put()
        return obj

    def get(self, params):
        key_name = params.get('key_name', None) if isinstance(params, dict) else None
        if key_name:
            parent = params.get('parent', None)
            if parent: parent = db_core.normalize_2_key(parent)
            obj = self.getModel().get_by_key_name(key_name, parent=parent)
        else:
            obj = getModelObject(params)
        if obj is not None and not isinstance(obj, self.getModel()) :
            raise ApiError(api_error.API_ERROR_INVALID_MODEL_TYPE, self.getModel().__name__, type(obj).__name__)
        return obj 

    def update(self, params):
        if not params.has_key('parent'):
            params['parent'] = self.getDefaultParent()
        validateUniqueness(params, self.getModel().uniqueness_properties(), self.getModel(), params['id'], parent=params.get('parent'))
        return db.run_in_transaction(self._trans_update, params)

    def _trans_update(self, params):
        obj = self.get(params)
        self._trans_update_massage_pre(obj, params)
        smallObjOld = smallModelAttributeMap(obj)
        updateModelObject(obj, params)
        self._trans_update_massage_post(obj, params)
        smallObjNew = smallModelAttributeMap(obj)
        objs = [obj]
        if len(smallObjOld)>0 :
            smallObj = obj.smallModel
            smallObjChanged = False
            for attr in smallObjOld.keys() :
                setattr(smallObj, attr, smallObjNew.get(attr, None))
                if smallObjOld.get(attr, None)!=smallObjNew.get(attr,None) :
                    smallObjChanged = True
            if smallObjChanged :
                objs.append(smallObj)
        db.put(objs)
        return obj

    def _trans_update_massage_pre(self, obj, params):
        pass

    def _trans_update_massage_post(self, obj, params):
        pass

    def delete(self, params):
        return db.run_in_transaction(self._trans_delete, params)
    
    def _trans_delete(self, params):
        obj = self.get(params)
        if obj is None :
            return None
        objs = [obj]
        if hasattr(obj.__class__, 'smallModel') and obj.smallModel is not None :
            objs.append(obj.smallModel)
        if hasattr(obj.__class__, 'deleted') :
            for obj in objs :
                obj.deleted = True
            return db.put(objs)
        else :
            return db.delete(objs)

    def query_base(self, keys_only=False, **kwargs):
        return self.getModel().all(keys_only=keys_only)
    
    def defaultOrderProperty(self):
        return None 
    
    def query(self, params):
        return self._query_by_offset(params)

    def queryall(self, params):
        if db_core.User.is_admin():
            return self.execute_query_all(params)
        raise ApiError(api_error.API_ERROR_ADMIN_OPERATION, "queryall", self.getModel().__name__)

    def default_query_limit(self):
        return 500 
    
    def execute_query_all(self, params={}):
        query = self._get_query_by_params(params, query_all=True)
        cursor = None
        limit = self.default_query_limit()
        try:
            results = []
            while True:
                if cursor:
                    query.with_cursor(cursor)
                objs = query.fetch(limit=limit)
                results.extend(objs)
                if len(objs)<limit:
                    break
                cursor = query.cursor()
            logging.info("Retrieved all %d %s objects successfully." % (len(results), self.getModel().__name__))
            return results
        except Exception:
            logging.exception("Unexpected error when querying all %s objects:" % self.getModel().__name__)
            return []
        
    def query_by_cursor(self, params={}):
        cursor = params.get('cursor', None)
        limit = int(params.get('limit', self.QUERY_LIMIT))
        query_all = bool(params.get('query_all', False))
        query = self._get_query_by_params(params, query_all=query_all)
        if cursor:
            query.with_cursor(cursor)
        objs = query.fetch(limit=limit)
        cursor = query.cursor()
        return {'cursor': cursor, 'objs': objs}

    def _query_by_offset(self, params={}):
        limit = int(params.get('limit', self.QUERY_LIMIT))
        offset = int(params.get('offset', 0))
        return self._get_query_by_params(params, query_all=False).fetch(limit, offset)

    def _get_query_by_params(self, params={}, query_all=False):
        order = params.get('order', None)
        if order is None and not query_all:
            order = self.defaultOrderProperty()
        queryParams = params.copy()
        for key in params:
            if key in ('limit', 'offset', 'cursor', 'order', 'parent', 'keys_only', 'query_all'):
                queryParams.pop(key)
                continue
            kstrip = key.strip()
            if kstrip.isalnum():
                value = queryParams.pop(key)
                parsedValue = parseValue(value, self.getModel().properties().get(kstrip))
                queryParams[kstrip + " = "] = parsedValue
        keys_only = bool(params.get('keys_only', False))
        query = self.getModel().all(keys_only=keys_only) if query_all else self.query_base(keys_only=keys_only)
        if params.has_key('parent'):
            query = query.ancestor(params.get('parent'))
        for key in queryParams:
            query = query.filter(key, queryParams.get(key))
        if order:
            query = query.order(order)
        return query

    def _refresh_turn(self, user,filter_date):
        return db.run_in_transaction(self._trans_refresh_turn,user,filter_date)
  
    def refresh(self,params):
        pass
              
    def _trans_refresh_turn(self,user,filter_date,limit_number=200):
        objects= self.getModel().all().filter('createdTime >=', filter_date).order('createdTime').ancestor(user).fetch(limit=limit_number)
        db.put(objects)
        num=len(objects)
        if len(objects)==limit_number:
            filter_date = objects[limit_number-1].createdTime
            return True,filter_date,num
        else:
            return False,filter_date,num

    @classmethod
    def supportedOperations(cls):
        """"
        Supported public API operations of this processor
        """
        return ImmutableSet([api_const.API_O_CREATE, api_const.API_O_GET, api_const.API_O_UPDATE, api_const.API_O_DELETE, 
                             api_const.API_O_QUERY, api_const.API_O_QUERY_BY_CURSOR, api_const.API_O_QUERY_ALL, api_const.API_O_REFRESH, api_const.API_O_ADMIN])
      
    def admin(self, params):
        if not users.is_current_user_admin():
            return "The opeartion requires admin privilege!"
        return self.execute_admin(params)

    def execute_admin(self, params):
        return "Noop!"

    def call(self, operation, inParams, outFormat='model'):
        """
        The entry point to call all api operations.
        Supported output format include: 
            'model' - the default output, return db.Model or a db.Key, or list of them
            'json' - return json
            'python' - return a python dict or list
        """
        oper = operation.lower()
        if oper not in self.supportedOperations():
            raise ApiError(api_error.API_ERROR_UNSUPPORTED_OPERATION, oper, self.getModel().__name__)
        obj = getattr(self, oper)(inParams)
        if outFormat=='model' :
            return obj
        if outFormat=='json' :
            return json.dumps(obj, cls=self.getJSONEncoder(), indent=4)
        if outFormat=='python' :
            return json.loads(json.dumps(obj, cls=self.getJSONEncoder(), indent=4))
    
    def convertFormat(self, obj, outFormat='model'):
        """
            The function converts the pass-in model to the specific out model
        """
        if outFormat=='model' :
            return obj
        if outFormat=='json' :
            return json.dumps(obj, cls=self.getJSONEncoder(), indent=4)
        if outFormat=='python' :
            return json.loads(json.dumps(obj, cls=self.getJSONEncoder(), indent=4))

    def getJSONEncoder(self):
        return BaseJSONEncoder

    def getModel(self):
        """
        Abstract function, please override
        """
        pass
    
    def getSmallModel(self):
        raise ApiError(api_error.API_ERROR_UNSUPPORTED_OPERATION, "getSmallModel", self.getModel().__name__)

    def getDefaultParent(self):
        return db_core.get_user()  
      
    @classmethod
    def api_module(cls):  
        pass

    def jsonEncodeKeyId(self, keyOrId):
        """
        Utility to encode an object key or key id into a json string like:
            {"id": "aglzbnNkamFuZ29yFwsSEGRiX2Jhc2Vwb2x5bW9kZWwYgAEM"} 
        """
        if keyOrId is None : return '{"id" : null}'
        
        return '{"id" : "' + str(keyOrId) + '"}'
        pass


class AssociateModelBaseProcessor(BaseProcessor):
    """
    A convenient base processor for associate models.
    Commonly, we don't support some public API operations for associate models.  
    """
    @classmethod
    def supportedOperations(cls):
        """"
        Supported public API operations of this processor
        """
        return ImmutableSet([api_const.API_O_QUERY,api_const.API_O_REFRESH])

