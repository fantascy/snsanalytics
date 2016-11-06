import sys
import datetime
import pickle
import threading
import logging

from google.appengine.ext import db

from sns.core.core import SystemStatusMonitor, KeyName


class DbCache(db.Model, KeyName):
    modifiedTime = db.DateTimeProperty(auto_now=True, required=True)
    cache = db.TextProperty()
    
    @classmethod
    def keyNamePrefix(cls):
        return "Cache:"

    def loads(self):
        return pickle.loads(str(self.cache)) if self.cache else None
    
    def dumps(self, obj):
        self.cache = pickle.dumps(obj)
        logging.info("%s size is %d." % (self.key().name(), len(self.cache)))
    
    @classmethod
    def get_or_insert_dbcache(cls, key_name):
        parent = SystemStatusMonitor.get_system_monitor(key_name)
        return cls.get_or_insert(cls.keyName(key_name), parent=parent)

    def size(self):
        return len(self.cache) if self.cache else 0 
        
    def put(self):
        db.Model.put(self)


class ProcessCache:
    KEY_NAME = None
    _cv = threading.Condition()
    _cache = None
    
    @classmethod
    def is_cache_valid(cls):
        return cls._cache and cls._cache[0] > SystemStatusMonitor.get_system_monitor(cls.KEY_NAME).modifiedTime

    @classmethod
    def get(cls, fallback=None, transformer=None):
        with cls._cv:
            if not cls.is_cache_valid():
                cls.handle_cache_missing()
        transformer = transformer if transformer else cls.transform_get
        return transformer(cls._cache[1]) if cls._cache and cls._cache[1] else fallback

    @classmethod
    def handle_cache_missing(cls):
        pass

    @classmethod
    def set(cls, value, transformer=None):
        transformer = transformer if transformer else cls.transform_set
        transformed = transformer(value)
        logging.info("Process cache: cache size is %d for key %s." % (sys.getsizeof(transformed), cls.KEY_NAME))
        with cls._cv:
            cls.handle_persistence(transformed)
            cls._update_monitor()
            cls._cache = (datetime.datetime.now(), transformed)

    @classmethod
    def handle_persistence(cls, transformed):
        pass

    @classmethod
    def flush(cls):
        """ Flush cache only, not persisted copy if there is any. """
        with cls._cv:
            cls._cache = None
        logging.info("Process cache: flushed cache for key %s." % cls.KEY_NAME)
    
    @classmethod
    def _update_monitor(cls):
        monitor = SystemStatusMonitor.get_system_monitor(cls.KEY_NAME)
        monitor.info = str(datetime.datetime.now())
        SystemStatusMonitor.set_system_monitor(monitor)
        
    @classmethod
    def transform_get(cls, obj):
        return obj
    
    @classmethod
    def transform_set(cls, obj):
        return obj


class PersistedProcessCache(ProcessCache):
    @classmethod
    def handle_cache_missing(cls):
        dbcache = DbCache.get_or_insert_dbcache(cls.KEY_NAME)
        obj = dbcache.loads() if dbcache else None
        cls._cache = (datetime.datetime.now(), obj)

    @classmethod
    def handle_persistence(cls, transformed):
        dbcache = DbCache.get_or_insert_dbcache(cls.KEY_NAME)
        dbcache.dumps(transformed)
        dbcache.put()


def get_persisted(key_name, fallback=None, transformer=None):
    return PersistedProcessCache.get(key_name, fallback=fallback, transformer=transformer)


def set_persisted(key_name, value, transformer=None):
    return PersistedProcessCache.set(key_name, value, transformer=None)


    