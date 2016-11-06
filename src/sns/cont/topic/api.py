import logging
import csv
import copy
import datetime, time
import threading
from sets import ImmutableSet

from google.appengine.ext import db

from common.utils import string as str_util
import context, deploysns
from sns.serverutils import deferred, memcache
from sns.core.processcache import ProcessCache, PersistedProcessCache
from sns.api import consts as api_const
from sns.api.base import BaseProcessor
from sns.cont import consts as cont_const
from sns.cont.models import Topic, NoChannelTopic


class TopicProcessor(BaseProcessor):
    def getModel(self):
        return Topic
    
    @classmethod
    def supportedOperations(cls):
        """"
        Supported public API operations of this processor
        """
        return ImmutableSet([api_const.API_O_CRON_EXECUTE, api_const.API_O_CLEAN,]).union(BaseProcessor.supportedOperations())

    def getDefaultParent(self):
        return None
      
    def create(self, params):
        titleKey = str_util.name_2_key(params['name'])
        params['nameLower'] = params['name'].lower()
        if not params.has_key('key_name') :
            params['key_name'] = Topic.keyName(titleKey)
        topicModel =  BaseProcessor.create(self, params)
        for key in topicModel.relatedTopics :
            topic = Topic.get_by_key_name(Topic.keyName(key))
            if not titleKey in topic.relatedTopics:
                topic.relatedTopics.append(titleKey)
                topic.put()
        return topicModel
    
    def update(self,params):
        params['nameLower'] = params['name'].lower()
        topicModel =  BaseProcessor.update(self, params)
        titleKey = topicModel.keyNameStrip()
        memcache.delete(cont_const.TOPIC_MEM_KEY_PREFIX+titleKey)
        if params.has_key('relatedTopics'):
            m_related = set(topicModel.relatedTopics)
            relates = []
            for r in params['relatedTopics']:
                relates.append(r)
            p_ralated = set(relates)
            remove = m_related - p_ralated
            add = p_ralated - m_related
            for key in remove:
                topic = Topic.get_by_key_name(Topic.keyName(key))
                topic.relatedTopics.remove(titleKey)
                topic.put()
            for key in add:
                topic = Topic.get_by_key_name(Topic.keyName(key))
                topic.relatedTopics.append(titleKey)
                topic.put()
        return topicModel
    
    def delete(self,params):
        topic = self.get(params)
        titleKey = topic.keyNameStrip()
        noChannel = NoChannelTopic.get_by_key_name(titleKey)
        if noChannel is not None:
            db.delete(noChannel)
        for key in topic.relatedTopics :
            t = Topic.get_by_key_name(Topic.keyName(key))
            t.relatedTopics.remove(titleKey)
            t.put()
        topic.relatedTopics = []
        sons = Topic.all().filter('parentTopics', titleKey).fetch(limit=1000)
        for son in sons:
            son.parentTopics.remove(titleKey)
            son.put()
        topic.parentTopics = []
        topic.put()
        return topic

    def execute_admin(self, params):
        op = params.get('op', None)
        if op:
            if op=='get_hashtags_for_topic':
                return self.get_hashtags_for_topic(params.get('topic', None))
            elif op=='delete_all':
                return self._delete_all()
            
    def get_hashtags_for_topics(self, topic_keys):
        hashtags = []
        for topic_key in topic_keys:
            hashtags.extend(self.get_hashtags_for_topic(topic_key))
        return hashtags

    def get_hashtags_for_topic(self, topic_key):
        if not topic_key:
            return []
        topic = Topic.get_by_topic_key(topic_key)
        if topic and 'summerolympics' in topic.parentTopics:
            return ['Olympic']
        else:
            return []

    def _delete_all(self):
        count = 0
        while True:
            topics = Topic.all().fetch(limit=100)
            count += len(topics)
            if topics:
                db.delete(topics)
            else:
                break
        return count


class AllTopicNamesCache(PersistedProcessCache):
    KEY_NAME = 'pck_topic_name_list'


class AllDealCityTopicsCache(PersistedProcessCache):
    KEY_NAME = 'pck_topic_all_deal_cities'


class AllTopicsCache(ProcessCache):
    KEY_NAME = 'pck_topic_all'


class TopicCacheMgr:
    _cv = threading.Condition()

    @classmethod
    def is_cache_valid(cls):
        return AllTopicsCache.is_cache_valid()
    
    @classmethod
    def flush(cls):
        topic_map = AllTopicsCache.get(fallback={})
        for topic_key in topic_map.keys():
            memcache.delete(cont_const.TOPIC_MEM_KEY_PREFIX + topic_key)
        AllDealCityTopicsCache.flush()
        AllTopicNamesCache.flush()
        AllTopicsCache.flush()

    @classmethod
    def build_all_cache(cls, force=False):
        if not context.is_backend():
            raise Exception("Only backend server can build topic cache!")
        with cls._cv:
            if cls.is_cache_valid() and not force:
                return True  
            cls.flush()
            startTime = datetime.datetime.utcnow()
            logging.info("Topic cache: started re-building.")
            topics = TopicProcessor().execute_query_all()
            AllTopicNamesCache.set([topic.name.encode('utf-8') for topic in topics])
            for topic in topics:
                memcache.set(cont_const.TOPIC_MEM_KEY_PREFIX + topic.keyNameStrip(), topic)
    #        memcache.set(cont_const.TOPIC_MEM_KEY_TOPO_LIST, cls._topological_list(topics))
    #        memcache.set(cont_const.TOPIC_MEM_KEY_PARENT1_PREORDER, cls._parent1_preorder(topics))
            AllTopicsCache.set(dict([(topic.keyNameStrip(), topic) for topic in topics]))
            AllDealCityTopicsCache.set(cls._deal_cities(topics))
            endTime = datetime.datetime.utcnow() 
            logging.info("Topic cache: finished re-building in %s." % str(endTime-startTime))
            return True
    
    @classmethod
    def rebuild_if_cache_not_valid(cls):
        if not cls.is_cache_valid():
            cls.build_all_cache()

    @classmethod
    def deferred_build_all_cache(cls, force=False):
        deferred.defer(cls.build_all_cache, force=force)

    @classmethod
    def get_all_topic_names(cls):
        return AllTopicNamesCache.get(fallback=[])

    @classmethod
    def get_all_deal_city_topics(cls):
        return AllDealCityTopicsCache.get(fallback=[])

    @classmethod
    def get_or_build_all_topic_map(cls):
        cls.rebuild_if_cache_not_valid()
        return AllTopicsCache.get(fallback={})

    @classmethod
    def get_or_build_all_topics(cls):
        return cls.get_or_build_all_topic_map().values()

    @classmethod
    def get_topic_by_key(cls, topic_key):
        topic = cls.get_or_build_all_topic_map().get(topic_key, None)
        if not topic:
            logging.error("TopicCacheMgr: Topic not found for topic key '%s'!" % topic_key)
        return topic

    @classmethod
    def get_all_topic_keys(cls):
        return cls.get_or_build_all_topic_map().keys()

    @classmethod
    def get_all_topic_keys_parent1_preorder(cls):
        topicKeys = memcache.get(cont_const.TOPIC_MEM_KEY_PARENT1_PREORDER)
        if topicKeys is None :
            return None
        else :
            return topicKeys

    @classmethod
    def get_all_level_1_topic_keys(cls):
        level1TopicKeys = memcache.get(cont_const.TOPIC_MEM_KEY_LEVEL_1_LIST)
        if level1TopicKeys is None:
            query = db.Query(Topic, keys_only=True).filter('isLevel1', True)
            level1TopicKeys = [key.name().split(':')[1] for key in query.fetch(limit=1000)]
            if len(level1TopicKeys) > 0:  
                memcache.set(cont_const.TOPIC_MEM_KEY_LEVEL_1_LIST, level1TopicKeys, time=86400)
        if not level1TopicKeys:
            raise Exception("Failed to retrieve level 1 topic keys!")
        return level1TopicKeys

    @classmethod
    def get_all_level_1_topic_key_set(cls):
        return set(cls.get_all_level_1_topic_keys())

    @classmethod
    def get_all_us_topic_key_set(cls):
        all_us_topic_keys = memcache.get(cont_const.TOPIC_MEM_KEY_ALL_US_SET)
        if all_us_topic_keys is None:
            query = db.Query(Topic, keys_only=True).filter('ancestorTopics', 'us')
            all_us_topic_keys = [key.name().split(':')[1] for key in query.fetch(limit=1000)]
            if len(all_us_topic_keys)>0:
                all_us_topic_keys.append('us')
                all_us_topic_keys = set(all_us_topic_keys)  
                memcache.set(cont_const.TOPIC_MEM_KEY_ALL_US_SET, all_us_topic_keys, time=86400)
        if not all_us_topic_keys:
            raise Exception("Failed to retrieve all us topic keys!")
        return all_us_topic_keys

    @classmethod
    def _topological_list(cls, topics):
        """ Any child topic is always before any of its ancestor topics. """
        logging.info("Topic cache: started building topic topological list.")
        workSet = set([topic.keyNameStrip() for topic in topics])
        topicMap = {}
        for topic in topics :
            topicMap[topic.keyNameStrip()] = topic
        sortedSet = set([]) 
        sortedList = []
        while len(workSet)>0 :
            stack = [workSet.pop()]
            visitedMap = {}
            while len(stack)>0 :
                topicKey = stack.pop()
                topic = topicMap[topicKey]
                if topicKey in sortedSet :
                    continue
                if visitedMap.get(topicKey, False) :
                    sortedList.append(topicKey)
                    sortedSet.add(topicKey)
                else :
                    if topic.childTopics is None or len(topic.childTopics)==0 :
                        sortedList.append(topicKey)
                        sortedSet.add(topicKey)
                    else :
                        stack = stack + [topicKey] + topic.childTopics
                        visitedMap[topicKey] = True
            workSet = workSet - sortedSet
        logging.debug("Topic cache: topic topological list: %s " % str(sortedList))
        logging.info("Topic cache: finished building topic topological list.")
        return sortedList

    @classmethod
    def _parent1_preorder(cls, topics):
        """ Pre-order traverse all topics based on parent 1 relationship. """
        logging.info("Topic cache: started building parent 1 based pre-order topic traverse list.")
        roots = []
        childrenMap = {}
        topicMap = {}
        treeSizeMap = {}
        for topic in topics:
            topicKey = topic.keyNameStrip()
            topicMap[topicKey] = topic
            if len(topic.parentTopics)==0:
                roots.append(topicKey)
            else:
                children = childrenMap.get(topic.parentTopics[0], [])
                children.append(topicKey)
                childrenMap[topic.parentTopics[0]] = children
        sortedList = []
        cls._parent1_preorder_exec(roots, childrenMap, sortedList, treeSizeMap)
        updateList = []
        for topic in topics:
            newTreeSize = treeSizeMap[topic.keyNameStrip()]
            oldTreeSize = topic.treeSizeP1
            if newTreeSize!=oldTreeSize:
                topic.treeSizeP1 = newTreeSize
                updateList.append(topic)
        logging.info("Topic cache: updating parent1 tree size for %d topics." % len(updateList))
        index = 0
        while index<len(updateList):
            db.put(updateList[index:index+100])
            index += 100
        logging.debug("Topic cache: topic parent1 preorder: %s" % str(sortedList))
        logging.debug("Topic cache: topic parent1 tree sizes: %s" % str(treeSizeMap))
        logging.info("Topic cache: finished building parent1 preorder topic list.")
        return sortedList
        
    @classmethod
    def _parent1_preorder_exec(cls, roots, childrenMap, sortedList, treeSizeMap):
        forestSize = 0
        for root in roots:
            sortedList.append(root)
            treeSize = 1
            children = childrenMap.get(root, None)
            if children is not None and len(children)>0:
                treeSize += cls._parent1_preorder_exec(children, childrenMap, sortedList, treeSizeMap)
            treeSizeMap[root] = treeSize
            forestSize += treeSize
        return forestSize
        
    @classmethod
    def _deal_cities(cls, topics):
        """ All deal city topics."""
        deal_city_topics = []
        for topic in topics:
            if cont_const.TOPIC_TAG_DEAL_CITY in topic.tags:
                deal_city_topics.append(topic)
        return deal_city_topics

    
PSEUDO_LEVEL_1_TOPICS = ('music', 'movies', 'politics')            


class CsvRowBase:
    FORMAT = ()

    def __init__(self, row_data):
        self.row_data = row_data

    def column(self, index):
        if index >= len(self.row_data):
            return None
        else:
            return str_util.strip(self.row_data[index].decode('utf-8'))

    @classmethod
    def file_validate(cls, file_data):
        context.get_context().set_login_required(False)
        context.set_deferred_context(deploy=deploysns)
        return True
    
    @classmethod
    def file_import(cls, file_data):
        context.get_context().set_login_required(False)
        context.set_deferred_context(deploy=deploysns)
        return True
    

class CsvRowTopic(CsvRowBase):
    def name(self):
        return str_util.strip(self.column(0))


class CsvRowTopicCreate(CsvRowTopic):
    FORMAT = ('Name', 'Key', 'Parent 1', 'Parent 2', 'Parent 3', 'Parent 4',)
    
    def key(self):
        key = str_util.lower_strip(self.column(1))
        if str_util.empty(key) or key == 'default':
            return None
        else:
            return key 
    
    def parent1(self):
        return self.column(2)
    
    def parent2(self):
        return self.column(3)
    
    def parent3(self):
        return self.column(4)
    
    def parent4(self):
        return self.column(5)
    
    @classmethod
    def file_validate(cls, file_data):
        if not CsvRowTopic.file_validate(file_data):
            return False
        rows = csv.reader(file_data)
        parentKeys = {}
        topic_statuses = {}
        parentList = {}
        success = True
        number = 1
        while True:
            try:
                number += 1
                row = cls(rows.next())
                topic_name = row.name()
                if not str_util.is_ascii(topic_name):
                    logging.error("Topic file validation error: Non-ASCII topic name '%s' at line #%d." % (topic_name, number))
                    success = False
                topicKey = row.key()
                if topic_statuses.has_key(topic_name):
                    logging.error("Topic file validation error: duplicated topic name '%s' at line #%d." % (topic_name, number))
                    success = False
                if cls == CsvRowTopicCreate:
                    parentNames = []
                    for parentName in (row.parent1(), row.parent2(), row.parent3(), row.parent4()):
                        if not str_util.empty(parentName):
                            parentNames.append(parentName)
                    topic_statuses[topic_name] = "Normal"
                    parentKeys[row.parent1()] = "Needed"
                    parentKeys[row.parent2()] = "Needed"
                    parentKeys[row.parent3()] = "Needed"
                    parentKeys[row.parent4()] = "Needed"
                    parentList[topic_name] = parentNames
                elif cls == CsvRowTopicDelete:
                    topics = Topic.all().filter('name', topic_name).fetch(limit=1)
                    if len(topics) == 0:
                        logging.info("Topic file validation error: Deleting topic '%s' topic does not exist in line %d." % (topic_name, number))
                        success = False
                    topic_statuses[topic_name] = "Deleted"
                elif cls == CsvRowTopicRename:
                    if topicKey is None:
                        topics = Topic.all().filter('name', topic_name).fetch(limit=1)
                        if len(topics) == 0:
                            theTopic = None
                        else:
                            theTopic = topics[0]
                    else:
                        theTopic = Topic.get_by_key_name(Topic.keyName(topicKey))
                    if theTopic is None:
                        logging.info('Topic file validation error: Rename topic "%s" not found in line %d' % (topic_name, number))
                        success = False
                    else:
                        parentList[row.new_name()] = [Topic.key_2_name(key) for key in theTopic.parentTopics]
                    topic_statuses[topic_name] = "Deleted"
                    topic_statuses[row.new_name()] = "Normal"
                else:
                    logging.error("Topic file validation error: Unknown file format at line #%d!" % number)
                    success = False
            except StopIteration:
                break
            except Exception:
                logging.exception('Topic file validation error: at line #%d' % (number,))
                success = False
        
        #parent key check
        for parent in parentKeys:
            if str_util.empty(parent):
                continue
            if not topic_statuses.has_key(parent):
                logging.info('Topic file validation error: Unknown parent "%s"' % parent)
                success = False
                continue
            if topic_statuses[parent] == 'Deleted':
                logging.info('Topic file validation error: Parent "%s" needed but has been deleted.' % parent)
                success = False
                
        #parent loop check
        loopCheck = cls._topic_loop_check()
        for parent in parentList:
            if not loopCheck(parent, parentList, []):
                success = False
        
        if success:
            logging.info('Topic file validation succeeded.')
        return success

    @classmethod
    def _topic_loop_check(cls):
        _loopCheckCache = {}
        def _loopCheck(element, topicList, history):
            if _loopCheckCache.has_key(element):
                return _loopCheckCache[element]
            if element in history:
                logging.info('Topic file validation error: Parent loop. Loop circle: %s' % str(history))
                _loopCheckCache[element] = False
                return False
            for parent in topicList.get(element, []):
                result = _loopCheck(parent, topicList, history + [element])
                if not result:
                    _loopCheckCache[element] = False
                    return False
            _loopCheckCache[element] = True
            return True
        return _loopCheck

    @classmethod    
    def file_import(cls, file_data):
        if not CsvRowTopic.file_import(file_data):
            return False
        data_copy = copy.copy(file_data)
        if cls._file_import_phase_1(data_copy):
            return cls._file_import_phase_2(file_data)
        else:
            return False

    @classmethod    
    def _file_import_phase_1(cls, data):
        rows = csv.reader(data)
        success = True
        number = 1
        while True:
            try:
                number += 1
                row = cls(rows.next())
                params = {}
                if cls==CsvRowTopicRename:
                    params['name'] = row.new_name()
                else:
                    params['name'] = row.name()
                topicKey = row.key()
                if topicKey is None: topicKey = str_util.name_2_key(row.name())
                params['key_name'] = Topic.keyName(topicKey)
                theTopic = Topic.get_by_key_name(params['key_name'])
                if cls==CsvRowTopicCreate:
                    if theTopic is not None:
                        params['id'] = theTopic.id
                        TopicProcessor().update(params)
                    else:
                        TopicProcessor().create(params)
                elif cls==CsvRowTopicDelete:
                    pass
                elif cls==CsvRowTopicRename:
                    if theTopic is not None:
                        params['id'] = theTopic.id
                        TopicProcessor().update(params)
                    else:
                        logging.error('Topic file commit error: Rename topic "%s" not found in line %d' % (row.name(), number))
                        success = False
                else:
                    logging.error("Topic file commit error: Unknown file format at line #%d!" % (number, ))
                    success = False
            except StopIteration:
                break
            except Exception:
                logging.exception("Topic file commit error at line %d!" % (number, ))
                success = False
        if success:
            logging.info('Topic file commit phase 1 succeeded.')
        else:
            logging.error('Topic file commit phase 1 failed.')
        return success
    
    @classmethod    
    def _file_import_phase_2(cls, data):
        topicMapByName = {}
        topicMapByKey = {}
        offset = 0
        limit = 100
        logging.info("Wait some time for eventual consistency...")
        time.sleep(2)
        while True:
            topics = Topic.all().fetch(limit=limit, offset=offset)
            if len(topics) == 0:
                break
            offset += len(topics)
            for topic in topics:
                topicMapByName[topic.name] = topic
                topicMapByKey[topic.keyNameStrip()] = topic
        rows = csv.reader(data)
        success = True
        number = 1
        while True:
            try:
                number += 1
                row = cls(rows.next())
                topicName = row.name()
                if cls==CsvRowTopicDelete:
                    try:
                        if topicMapByName.has_key(topicName):
                            topic = topicMapByName[topicName]
                            TopicProcessor().delete({'id':topic.id})
                        else:
                            logging.error('Topic file commit error: Deleting topic "%s" not exist'%(topicName))
                            success = False
                    except Exception,ex:
                        logging.exception('Topic file commit error: Exception raised when delete topic %s: %s'%(topicName, str(ex)))
                        success = False
                elif cls==CsvRowTopicRename:
                    """ No need to do anything, because rename is done in the init() step. """
                    pass
                elif cls==CsvRowTopicCreate:
                    parentNames = []
                    for parentName in (row.parent1(), row.parent2(), row.parent3(), row.parent4()):
                        if not str_util.empty(parentName):
                            parentNames.append(parentName)
                    parents = []
                    for name in parentNames:
                        if str_util.empty(name):
                            pass
                        elif topicMapByName.has_key(name):
                            parents.append(name)
                        else:
                            logging.error("Topic file commit error: Unknown parent key %s at line #%d." % (name, number))
                            success = False
                    
                    topic = topicMapByName[topicName]
                    topic.parentTopics = [topicMapByName[name].keyNameStrip() for name in parents]
                    topic.isLevel1 = len(topic.parentTopics)==0 
                else:
                    logging.error("Topic file commit error: Wrong file format!")
                    success = False
            except StopIteration:
                break
            except Exception:
                logging.exception("Topic file commit error at line # %d!" % (number, ))
                success = False
                
        try:
            for topic in topicMapByKey.values():
                """ Clean up child and ancestor topics. """
                topic.childTopics = []
                topic.ancestorTopics = []
                
            for topicKey, topic in topicMapByKey.items():
                """ Build child topics """
                if topic.parentTopics is None:
                    continue
                for parentKey in topic.parentTopics:
                    parent = topicMapByKey[parentKey]
                    if parent.childTopics is None:
                        parent.childTopics = [topicKey]
                    else:
                        parent.childTopics.append(topicKey)
    
                """ Build ancestor topics """
                ancestors = set([])
                workset = set(topic.parentTopics)
                while len(workset)>0:
                    ancestor = workset.pop()
                    ancestors.add(ancestor)
                    topicModel = topicMapByKey[ancestor]
                    if topicModel is not None and topicModel.parentTopics is not None:
                        workset.update(topicModel.parentTopics)
                topic.ancestorTopics = list(ancestors)
            topicList = topicMapByKey.values()
            offset = 0
            while offset<len(topicList):
                db.put(topicList[offset:offset+100])
                offset += 100
        except:
            logging.exception("Topic file commit error: Exception raised when writing child topics info.")
            success = False
    
        if success:
            TopicCacheMgr.build_all_cache(force=True)
            logging.info('Topic file commit succeeded.')
        return success


class CsvRowTopicRename(CsvRowTopicCreate):
    FORMAT = ('Name', 'New Name')
    
    def new_name(self):
        return self.column(1)
    

class CsvRowTopicDelete(CsvRowTopicCreate):
    FORMAT = ('Name', )
    

class CsvRowTopicExt(CsvRowTopic):
    @classmethod
    def file_validate(cls, file_data):
        rows = csv.reader(file_data)
        success = True
        count = 0
        while True:
            try:
                count +=1
                row = cls(rows.next())
                name = row.name()
                topic = Topic.get_by_name(name)
                if topic is None:
                    success = False
                    logging.error("Topic file validation error: at line #%d. Topic %s not found." % (count, name))
                    continue
            except StopIteration:
                break
            except Exception:
                success = False
                logging.exception("Topic file validation error when setting topic attributes.")
        if success:
            logging.info("Topic file validation succeeded.")
        return success

    @classmethod
    def file_import(cls, file_data):
        rows = csv.reader(file_data)
        count = 0
        success = True
        while True:
            try:
                count +=1
                row = cls(rows.next())
                name = row.name()
                topic = Topic.get_by_name(name)
                if topic is None:
                    success = False
                    logging.error("Topic file error: topic %s not found." % name)
                    break
                row.update_topic(topic)
                topic.put()
            except StopIteration:
                break
            except Exception:
                success = False
                logging.exception("Topic file error when setting topic attributes.")
        if success:
            logging.info("Topic file commit succeeded for topic ext upload.")
            TopicCacheMgr.build_all_cache()
            return True
        else:
            logging.info("Topic file ended with errors.")
            return False

    def update_topic(self, topic):
        pass
        

class CsvRowTopicExtCity(CsvRowTopicExt):
    FORMAT = ('Name (City)', 'Groupon Code', 'Groupon Top Deal URL', )
    
    def groupon_code(self):
        return self.column(1)
    
    def groupon_top_deal_url(self):
        return self.column(2)
    
    def update_topic(self, topic):
        topic.ext_set_attr('groupon_code', self.groupon_code())
        topic.ext_set_attr('groupon_top_deal_url', self.groupon_top_deal_url())
        topic.add_tag(cont_const.TOPIC_TAG_DEAL_CITY)


ALL_CSV_ROW_CLASSES = (CsvRowTopicCreate, CsvRowTopicRename, CsvRowTopicDelete, CsvRowTopicExtCity, ) 
        

def get_csv_row_class(header):
    for clazz in ALL_CSV_ROW_CLASSES:
        if len(header) != len(clazz.FORMAT):
            continue
        matched = True
        for i in range(0, len(header)):
            if str_util.name_2_key(header[i]) != str_util.name_2_key(clazz.FORMAT[i]):
                matched = False
                break
        if matched:
            return clazz
    return None
   

def topic_validate(data):
    header = csv.reader(data).next()
    row_class = get_csv_row_class(header)
    if not row_class:
        return "invalid data format"
    else:
        deferred.defer(row_class.file_validate, data)
        return "succeeded"
    

def topic_import(data):
    header = csv.reader(data).next()
    row_class = get_csv_row_class(header)
    if not row_class:
        return "invalid data format"
    else:
        deferred.defer(row_class.file_import, data)
        return "succeeded"
    


