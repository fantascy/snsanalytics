import datetime
import threading
from sets import ImmutableSet
import logging

from google.appengine.ext import db

import deploysns
import context
from sns.serverutils import deferred
from sns.core import core as db_core
from sns.core import base as db_base
from sns.api import consts as api_const
from sns.api.base import BaseProcessor
from sns.chan import consts as channel_const
from sns.log.models import CmpTwitterAcctFollowers 
from sns.femaster.models import Source, Target, TopicTarget, TopicTargetError, TgtflwrAllocationLog, TgtflwrFollowLog


ALL_FEMASTER_MODELS = (Source, Target, TopicTarget, TgtflwrAllocationLog, TgtflwrFollowLog)


def thread_name():
    return "FE Master thread %d" % threading.current_thread().ident 


class SourceProcessor(BaseProcessor):
    CHUNK_SIZE = 100 
    
    @classmethod
    def getModel(cls):
        return Source

    def update(self, params):
        chid = int(params.get('key_name'))
        obj = Source.get_by_chid(chid)
        state = params.get('state', None)
        if state is not None: obj.state = state
        tgtflwrs = params.get('tgtflwrs', None)
        if tgtflwrs is not None:
            if isinstance(tgtflwrs, basestring):
                tgtflwrs = eval(tgtflwrs)
            obj.reset(db_put=False)
            obj.add_tgtflwrs(tgtflwrs)
        db.put(obj)
        
    def execute_admin(self, params):
        op = params.get('op', None)
        if op == 'query_under_allocated':
            return self.query_under_allocated(params)
        elif op == 'get_follower_list':
            return self.get_follower_list(params)
        else:
            return BaseProcessor.execute_admin(self, params)
        
    def get_follower_list(self, params):
        source_chid = int(params.get('chid'))
        followers_store = CmpTwitterAcctFollowers.get_or_insert_by_chid(source_chid)
        return followers_store.getFollowers() if followers_store else []

    def query_under_allocated(self, params={}):
        now = datetime.datetime.now() 
        one_hour_ago = now - datetime.timedelta(hours=1)
        limit = int(params.get('limit', self.CHUNK_SIZE))
        query = Source.all().filter('state', channel_const.CHANNEL_STATE_NORMAL).filter('enough', False).filter('modifiedTime < ', one_hour_ago).order('modifiedTime')
        sources = query.fetch(limit=limit)
        for source in sources:
            source.modifiedTime = now
        db.put(sources) 
        logging.info("Retrieved %d sources." % (len(sources), ))
        return sources


class TargetProcessor(BaseProcessor):
    @classmethod
    def getModel(cls):
        return Target
         
    def update(self, params):
        user_id = int(params.get('key_name'))
        obj = Target.get_by_user_id(user_id)
        handle = params.get('handle', None)
        if handle is not None: obj.handle = handle
        cursor = params.get('cursor', None)
        if cursor is not None: obj.cursor = cursor
        completed = params.get('completed', None)
        if completed is not None: obj.completed = completed
        state = params.get('state', None)
        if state is not None: obj.state = state
        tgtflwrs = params.get('tgtflwrs', None)
        if tgtflwrs is not None: 
            if isinstance(tgtflwrs, basestring):
                tgtflwrs = eval(tgtflwrs)
            obj.tgtflwrs = '[]'
            obj.add_tgtflwrs(tgtflwrs)
        db.put(obj)
        
    def execute_admin(self, params):
        user_id = int(params.get('user_id', '0'))
        if not user_id:
            return "Missing required user_id!"
        op = params.get('op', None)
        if op == 'get_by_user_id':
            return Target.get_by_user_id(user_id)
        if op == 'get_or_insert_by_user_id':
            handle = params.get('handle', "Unknown")
            target = Target.get_or_insert_by_user_id(user_id, handle)
            return target
        else:
            return "Received an unsupported op request - %s" % op


class TopicTargetProcessor(BaseProcessor):
    @classmethod
    def getModel(cls):
        return TopicTarget
         
    def execute_admin(self, params):
        user_id = int(params.get('user_id', '0'))
        op = params.get('op', None)
        if op == 'get_by_topic_key':
            topic_key = params.get('topic_key')
            return TopicTarget.get_by_key_name_strip(topic_key)
        elif op == 'get_target_by_topic_key':
            topic_key = params.get('topic_key')
            return TopicTarget.get_target_by_topic_key(topic_key)
        elif op == 'get_or_insert_by_topic_key':
            topic_key = params.get('topic_key')
            user_id = int(params.get('user_id'))
            return TopicTarget.get_or_insert_by_topic_key(topic_key, user_id)
        else:
            return "Received an unsupported op request - %s" % op


class TopicTargetErrorProcessor(BaseProcessor):
    @classmethod
    def getModel(cls):
        return TopicTargetError
         
    def execute_admin(self, params):
        op = params.get('op', None)
        if op == 'get_or_insert_by_topic_key':
            topic_key = params.get('topic_key')
            error_msg = params.get('error_msg')
            return TopicTargetError.get_or_insert_by_topic_key(topic_key, error_msg)
        else:
            return "Received an unsupported op request - %s" % op


class TgtflwrAllocationLogProcessor(BaseProcessor):
    @classmethod
    def getModel(cls):
        return TgtflwrAllocationLog
         
    def create(self, params):
        chid = params.get('chid')
        tgtflwrs = params.get('tgtflwrs', [])
        return TgtflwrAllocationLog.create(chid, tgtflwrs)

    def delete(self, params):
        ids = []
        if params.has_key('ids'):
            ids = params.get('ids')
        else:
            ids.append(db_core.normalize_2_key(params))
        db.delete(ids)
    

class TgtflwrFollowLogProcessor(BaseProcessor):
    @classmethod
    def getModel(cls):
        return TgtflwrFollowLog
         

class FeMasterProcessor(BaseProcessor):
    @classmethod
    def supportedOperations(cls):
        return ImmutableSet([api_const.API_O_CRON_EXECUTE, 
                           ]).union(BaseProcessor.supportedOperations())

    def cron_execute(self, params):
        op = params.get('op', None)
        if op == 'sync_source':
            deferred.defer(self.__class__.deferred_sync_source)
        elif op == 'clean_all_deferred':
            deferred.defer(self.__class__.clean_all)
        else:
            return "Invalid operation - %s!" % op 
        return True

    def execute_admin(self, params):
        op = params.get('op', None)
        if op == 'show_target_followers':
            return self.show_target_followers(params)
        elif op == 'clean_all':
            return self.clean_all()
        else:
            return "Invalid operation - %s!" % op 
        return True

    @classmethod
    def show_target_followers(cls, params):
        chid = params.get('chid', None)
        source = Source.get_by_chid(chid) if chid else None
        return eval(source.tgtflwrs) if source else []

    @classmethod
    def deferred_sync_source(cls):
        context.set_deferred_context(deploysns)
        sources = SourceProcessor().execute_query_all()
        synced = []
        for source in sources:
            actual_count = source.actual_count()
            if actual_count == source.count:
                continue
            logging.info("%s: Source %d actual count is %d while count says %d." % (thread_name(), source.chid, actual_count, source.count))
            source.count = actual_count
            synced.append(source)
        db_base.put(synced)
        logging.info("%s: Corrected %d sources with incorrect count, out of total %d sources!" % (thread_name(), len(synced), len(sources)))
            
    @classmethod
    def clean_all(cls):
        return ' '.join([cls._clean_all(clazz) for clazz in ALL_FEMASTER_MODELS])

    @classmethod
    def _clean_all(cls, clazz):
        objs = clazz.all(keys_only=True)
        size = len(objs)
        db.delete(objs)
        return "%s: Deleted %d %s objs." % (thread_name(), size, clazz.__name__)

