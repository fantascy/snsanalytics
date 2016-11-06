from google.appengine.api import memcache

def get(key, namespace=None):
    return memcache.get(key,namespace=namespace)

def set(key, value, time=86400*7, min_compress_len=0, namespace=None):
    return memcache.set(key,value,time=time,min_compress_len=min_compress_len,namespace=namespace)

def delete(key, seconds=0, namespace=None):
    return memcache.delete(key,seconds=seconds,namespace=namespace)

def flush_all():
    return memcache.flush_all()
