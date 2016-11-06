import logging
import datetime
from sets import ImmutableSet

from google.appengine.ext import db

import context
from common.utils import string as str_util
from sns.serverutils import memcache, deferred
from sns.core.core import User
from sns.core import base as db_base
from sns.api import consts as api_const
from sns.api import base as api_base


CLEAN_MODEL_LIST = [
    "channel_channel", 
    "channel_channelclickcounter",
    "channel_oauthaccesstoken",
    "channel_oauthrequesttoken",
    "content_content",
    "content_feedclickcounter",
    "posting_post",
    "posting_posting",
    "posting_postingrule",
    "user_userclickcounter",
    "user_usercounters",
    "user_userfailurecounter",
    "user_userpostcounter",
    "user_userpostingcounter",
    "user_userurlcounter",
                    ]


SYSTEM_MODEL_LIST = [
    "db_user",
    "db_global",
    "posting_postingruleexecutor",
    "posting_postingrulequeue",
    "posting_postingscheduler",
                    ]


class AdminProcessor(api_base.BaseProcessor):
    @classmethod
    def supportedOperations(cls):
        """"
        Supported public API operations of this processor
        """
        return ImmutableSet([api_const.API_O_CLEAN, api_const.API_O_CLEAN_SYS]).union(api_base.BaseProcessor.supportedOperations())
    
    def execute_admin(self, params):
        from tests.sns.threadtest import TestThread
        from tests.sns.backgroundthreadtest import TestBackgroundThread
        from tests.common.s3 import s3test
        logging.info("Admin operation submitted.")
        op = params.get('op', None)
        if op:
            if op=='flush_memcache':
                return self._flush_memcache(params)
            elif op=='print_request':
                return self._print_request(params)
            elif op=='send_print_request':
                return self._send_print_request(params)
            elif op == 'test_threads':
                deferred.defer(TestThread.test)
            elif op == 'test_thread_limit':
                deferred.defer(TestThread.test_limit)
            elif op == 'test_thread_pool':
                from tests.sns import threadtest
                deferred.defer(threadtest.test_thread_pool)
            elif op == 'test_background_threads':
                deferred.defer(TestBackgroundThread.test)
            elif op == 'test_background_thread_limit':
                deferred.defer(TestBackgroundThread.test_limit)
            elif op == 'test_task_daemon':
                from sns.core.taskdaemon import DemoBackendTaskDaemon
                deferred.defer(DemoBackendTaskDaemon.deferred_execute)
            elif op == 'test_s3_multipart_upload':
                return s3test.TestBotoUpload.multipart_upload()
            elif op == 'test_s3_simple_upload':
                return s3test.TestBotoUpload.simple_upload()
            elif op == 'test_memory_size':
                size = int(params.get('size', 100000))
                from tests.sns import memorytest
                return memorytest.ChannelIdMemoryTest.set_chid_set(size)
            return "Submitted op %s." % op
        return "Noop!"

    def _print_request(self, params):
        request = context.get_context().request()
        return str(request)

    def _send_print_request(self, params):
        domain = params.get('domain', None)
        if domain is None:
            return "Please specify target domain!"
        import urllib2
        headers = { "User-Agent": "Admin Agent", "Host": "admin.sns.mx"}
        req = urllib2.Request("http://%s/api/admin/admin?op=print_request" % domain, data={}, headers=headers)
        return urllib2.urlopen(req).read()

    def _flush_memcache(self, params):
        cacheKey = params.get('key', None)
        if cacheKey is None:
            return "Please specify memcache key!"
        elif cacheKey=='all':
            memcache.flush_all()
            return "Flushed all memcache!"
        else:
            memcache.delete(cacheKey) 
            return "Flushed memcache by key '%s'!" % cacheKey

    @classmethod
    def clean_models(cls):
        now = datetime.datetime.utcnow()
        count = 0
        while True:
            then = datetime.datetime.utcnow()
            if then > now + datetime.timedelta(seconds=50):
                logging.info('Delete %d for model %s'%(count,str(cls)))
                break
            models = db.Query(cls,keys_only=True).fetch(limit=100)
            if len(models) == 0:
                logging.info('Finish delete for model %s'%str(cls))
                break
            db.delete(models)
            count += 100
    
    @classmethod
    def clean_small_models(cls, offset):
        from sns.cont.models import ContentPolySmall
        try :
            query = ContentPolySmall.all()
            updateCount = 0
            deleteCount = 0
            total = 0
            while True :
                objs = query.fetch(limit=100, offset=offset)
                total += len(objs)
                offset += len(objs)
                if len(objs)==0 :
                    logging.info('Finished cleaning up %d small models.' % (total,))
                    break
                try :
                    updateObjs = []
                    deleteObjs = []
                    for obj in objs :
                        if obj.model is None :
                            model = db.get(obj.modelId)
                            if model is None :
                                deleteObjs.append(obj)
                            else :
                                obj.model = model
                                updateObjs.append(obj)
                    db.put(updateObjs)
                    db.delete(deleteObjs)
                    updateCount += len(updateObjs)
                    deleteCount += len(deleteObjs)
                    offset -= len(deleteObjs)
                    logging.info('Updated %d, deleted %d, out of total %d small models.' % (updateCount, deleteCount, total))
                except :
                    logging.exception('Error updating small models:')
        except :
            logging.exception("Error updating small models, most likely timed out.")
        
    def clean(self, params=None):
        """
        Three params are checked: user, model, oneByOne.
        If 'user' param is present, we clean only for the user. Otherwise, clean for all user.
        If 'model' param is present, we clean only for the model. Otherwise, clean for all models in clean model list.
        If 'oneByOne' param is present, we delete one model instance at a time. Otherwise, we will delete by a batch of up to 500. 
        The 'oneByOne' param is ignored if the 'user' param is specified.
        The 'oneByOne' param is useful to delete objects whose parent entity may have been removed for various reasons.
        However, we should always try to run without the 'oneByOne' flag first, then run with this 'oneByOne' flag on a second pass if needed.
        Be super super careful to call this function!
        """
        if params is None :
            cleanModel = None
            user = None
            oneByOne = False
        else :
            cleanModel = str_util.strip(params.get('model', None))
            user = params.get('user', None)
            oneByOne = db_base.parseBool(params.get('oneByOne', None))
      
        delete_count = 0
        if user is not None :
            modelUser = User.get_by_key_name(User.keyNameByEmail(user))
            if modelUser is None :
                logging.error("User %s doesn't exist!" % user)
                return 0
            if cleanModel is None :
                delete_count += self._cleanAllModels(parent=modelUser)
            else :
                delete_count += self._cleanModel(cleanModel, parent=modelUser)  
            return delete_count
    
        if oneByOne:
            if cleanModel is None :
                delete_count += self._cleanAllModelsOneByOne()
            else :
                delete_count += self._cleanModelOneByOne(cleanModel)  
            return delete_count
            
        userList = User.all().fetch(1000)
        for modelUser in userList :
            if cleanModel is None :
                delete_count += self._cleanAllModels(parent=modelUser)
            else :
                delete_count += self._cleanModel(cleanModel, parent=modelUser)  
        return delete_count
        
    def _cleanModel(self, model, parent):
        delete_count = 0
        try :
            queryStr = "SELECT __key__ FROM %s WHERE ANCESTOR IS :1 " % model
            query = db.GqlQuery(queryStr, parent)
            count = 1
            while count>0 :
                delete_list = query.fetch(500)
                new_count = len(delete_list)
                if new_count>0 :
                    db.delete(delete_list)
                    delete_count += new_count
                    if self.isTimeout(timeout=5) : return delete_count
                count = query.count(500)
        except Exception, e:
            logging.error("AdminProcessor._cleanModel() error: %s" % e.message)
        logging.debug("AdminProcessor._cleanModel() cleaned %s entries for model %s of parent %s" % (delete_count, model, parent.key().name()))
        return delete_count
    
    def _cleanAllModels(self, parent):
        delete_count = 0
        for model in CLEAN_MODEL_LIST :
            delete_count += self._cleanModel(model, parent)
        logging.debug("AdminProcessor._cleanAllModels() cleaned totally %s entries of parent %s." % (delete_count, parent.key().name()))
        return delete_count
    
    def _cleanModelOneByOne(self, model):
        """
        If we clean one by one, we don't need the parent filter.
        """
        delete_count = 0
        try :
            queryStr = "SELECT __key__ FROM %s " % model
            query = db.GqlQuery(queryStr)
            count = 1
            while count>0 :
                delete_list = query.fetch(500)
                for obj in delete_list :
                    db.delete(obj)
                    delete_count += 1
                    if self.isTimeout(timeout=0) : return delete_count
                count = query.count(500)
        except Exception, e:
            logging.error("AdminProcessor._cleanModel() error: %s" % e.message)
        logging.debug("AdminProcessor._cleanModelOneByOne() cleaned %s entries for model %s." % (delete_count, model))
        return delete_count
        
    def _cleanAllModelsOneByOne(self):
        delete_count = 0
        for model in CLEAN_MODEL_LIST :
            delete_count += self._cleanModelOneByOne(model)
        logging.debug("AdminProcessor._cleanAllModelsOneByOne() cleaned totally %s entries." % delete_count)
        return delete_count
    
    def sysclean(self, params=None):
        """
        Clean all entities of certain db models.
        For now, this method is empty.
        """
        return 1  
    

def main():
    pass    


if __name__ == "__main__":
    main()
