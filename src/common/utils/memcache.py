from datetime import datetime, timedelta
import threading


class ProcessMemCache:
    _cv = threading.Condition()
    _map = {}
    
    @classmethod    
    def get(cls, mem_key):
        with cls._cv:
            obj, cached_time = cls._map.get(mem_key, (None, None))
            if obj is None:
                return None
            if cached_time < datetime.utcnow():
                cls._map.pop(mem_key)
                return None
            else:
                return obj
        
    @classmethod
    def set(cls, mem_key, obj, time=86400):
        with cls._cv:
            cached_time = datetime.utcnow() + timedelta(seconds=time)
            cls._map[mem_key] = (obj, cached_time)
    
    @classmethod    
    def delete(cls, mem_key):
        with cls._cv:
            if cls._map.has_key(mem_key):
                cls._map.pop(mem_key)
    
    
import context
if context.is_client():
    memcache = ProcessMemCache
else:
    from sns.serverutils import memcache as server_memcache
    memcache = server_memcache



