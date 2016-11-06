from google.appengine.ext import db

from sns.serverutils import memcache
from fe import consts as fe_const
from fe.api import errors as api_error


GLOBAL_KEY_NAME = "Global"
GLOBAL_BATCH_KEY_NAME =  "GlobalBatch"
class Global(db.Model):
    """ 
    The global object class.
    """
    
    @classmethod
    def get_global(cls):
        """
        Return the singleton global namespace object.
        """
        gobj = memcache.get(GLOBAL_KEY_NAME)
        if gobj is None :
            gobj = Global.get_or_insert(GLOBAL_KEY_NAME) 
            if gobj is None :
                raise api_error.ApiError(api_error.API_ERROR_UNKNOWN, "Global name space could not be established!")
            memcache.set(GLOBAL_KEY_NAME, gobj)
        return gobj
    
    @classmethod
    def get_batch_global(cls,batch_number):
        """
        Return the singleton global namespace object.
        """
        KEY_NAME=GLOBAL_BATCH_KEY_NAME+str(batch_number)
        gobj = memcache.get(KEY_NAME)
        if gobj is None :
            gobj = Global.get_or_insert(KEY_NAME) 
            if gobj is None :
                raise api_error.ApiError(api_error.API_ERROR_UNKNOWN, "Global name space could not be established!")
            memcache.set(KEY_NAME, gobj)
        return gobj
    
    @classmethod
    def get_mapping_global(cls, key):
        """
        Return the singleton global namespace object.
        """
        KEY_NAME=GLOBAL_BATCH_KEY_NAME+str(key)
        gobj = memcache.get(KEY_NAME)
        if gobj is None :
            gobj = Global.get_or_insert(KEY_NAME) 
            if gobj is None :
                raise api_error.ApiError(api_error.API_ERROR_UNKNOWN, "Global name space could not be established!")
            memcache.set(KEY_NAME, gobj)
        return gobj
    
    def className(self):
        return self.__class__.__name__    


