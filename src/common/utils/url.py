import re
import urllib
import urllib2
import urlparse
import base64
import logging
from StringIO import StringIO
import gzip

import deployappspot, context
from common.utils import string as str_util


MAX_URL_LENGTH = 512
ALLOWED_PROTOCOLS = ("http", "https", "ftp")
URL_REGEX = r"^(?#Protocol)(?:(?:ht|f)tp(?:s?)\:\/\/|~/|/)?(?#Username:Password)(?:\w+:\w+@)?(?#Subdomains)(?:(?:[-\w]+\.)+(?#TopLevel Domains)(?:com|org|net|gov|mil|biz|info|mobi|name|aero|jobs|museum|travel|[a-z]{2}))(?#Port)(?::[\d]{1,5})?(?#Directories)(?:(?:(?:/(?:[-\w~!$+|.,=]|%[a-f\d]{2})+)+|/)+|\?|#)?(?#Query)(?:(?:\?(?:[-\w~!$+|.,*:]|%[a-f\d{2}])+=(?:[-\w~!$+|.,*:=]|%[a-f\d]{2})*)(?:&(?:[-\w~!$+|.,*:]|%[a-f\d{2}])+=(?:[-\w~!$+|.,*:=]|%[a-f\d]{2})*)*)*(?#Anchor)(?:#(?:[-\w~!$+|.,*:=]|%[a-f\d]{2})*)?$"

GA_PARAMS = set(['utm_campaign', 'utm_source', 'utm_medium', 'utm_content', 'utm_term', ])
OMNITURE_PARAMS = set(['cid',])
ALL_WEB_ANALYTICS_PARAMS = set(list(GA_PARAMS) + list(OMNITURE_PARAMS)) 


def is_valid_domain(domain):
    return domain and len(domain.split('.')) > 1


def normalize_url(url):
    """
    This function needs to make sure all equivalent urls are treated as the same url.
    For instance, 'http://www.snsanalytics.com' should be equivalent to 'HTTP://www.SnsAnalytics.com/'.
    """
    url = str_util.encode_utf8_if_ok(url)
    import urlnorm  
    return urlnorm.normalize(url) if url else None


def is_valid_url(url, isNoneValid=False):
    if url is None:
        return isNoneValid
    (scheme,netloc) = urlparse.urlparse(url)[:2]
    if scheme in ALLOWED_PROTOCOLS and netloc.find(".")!=-1:
        return True
    else:
        return False


def sanitize_url(url):
    """
    sanitize a url by striping space and add http:// if necessary.
    return None if cannot sanitize the url
    """
    sanitized=url.strip()
    if sanitized.find(' ')!= -1:
        return None
    if not is_valid_url(sanitized):
        sanitized="http://"+sanitized
        
    if is_valid_url(sanitized):
        return sanitized
    else:
        return None
        
    
def scheme(url):
    normalized = normalize_url(url)
    parsed = urlparse.urlparse(normalized) if normalized else None
    if parsed and parsed.scheme:
        return parsed.scheme
    else:
        return 'http'


def full_domain(url):
    url = str_util.lower_strip(url)
    normalized = normalize_url(url)
    if not normalized:
        return None
    parsed = urlparse.urlparse(normalized)
    if parsed and parsed.scheme:
        return parsed.hostname
    else:
        """ e.g., 'localhost', 'localhost:8080' """
        return normalized.split(':')[0] 


def full_domain_excluding_www(url):
    domain = full_domain(url)
    if not domain: return None
    if domain.startswith('www.'):
        return domain[4:]
    else:
        return domain


def scheme_domain(url):
    return "%s://%s" % (scheme(url), full_domain(url)) if url else None
    

def root_domain(url):
    domain = full_domain(url)
    if domain and domain.startswith("www."):
        domain = domain[4:]
    if not domain:
        return None
    pieces = domain.split('.')
    if len(pieces) <= 2:
        return domain
    elif len(pieces[-1]) >= 3 or len(pieces[-2]) > 3:
        return '.'.join(pieces[-2:])
    else:
        return '.'.join(pieces[-3:])


def strip_url(url):
    from string import strip
    return strip(url)


def short_url(short_domain, url_id):
    url = strip_url(url_id)
    if url is None :
        return None
    return "http://%s/%s" %  (short_domain, url) 


def encode_base64(param):
    #return param
    return base64.urlsafe_b64encode(unicode(param).encode('utf-8'))
    

def decode_base64(param):
    #return param
    return unicode(base64.urlsafe_b64decode(param)).encode('utf-8')
    

def normalize_params(params):
    """
    This function makes sure all the param values are properly utf-8 encoded.
    This is needed before we invoke the standard Python fuction urllib.urlencode(params).
    """
    encodedParams = {}
    for k, v in params.items() :
        if v is not None :
            encodedParams[k] = unicode(v).encode("utf-8")
        else :
            encodedParams[k] = None
    return encodedParams


def params_2_query_string(params):
    return '&'.join(["%s=%s" % (key, value) for key, value in params.items()])
        

def get_params(url):
    if not url: return {}
    query = urlparse.urlparse(url)[4]
    if str_util.strip(query) is None :
        return {}
    split1 = query.split('&')
    params = {}
    for item in split1 :
        split2 = item.split('=', 1)
        if len(split2) != 2 :
            logging.warn("Invalid param '%s' in URL %s" % (item, url))
            continue
        params[split2[0]] = split2[1]
    return params
        

def get_param(url, param, decode=True):
    params = get_params(url)
    if len(params)==0 :
        return None
    else :
        return urldecode(params.get(param, None))
        

def merge_params(*paramss):
    result = {}
    for params in paramss :
        for key, value in params.items() :
            result[key] = value
    return result
        

def add_params_2_url(url, params):
    if params is None or len(params)==0 :
        return url
    query = params_2_query_string(merge_params(get_params(url), params))
    parsed = urlparse.urlparse(url)
    return urlparse.urlunparse((parsed[0], parsed[1], parsed[2], parsed[3], query, parsed[5]))
        

def remove_all_params(url):
    parsed = urlparse.urlparse(url)
    return urlparse.urlunparse((parsed[0], parsed[1], parsed[2], parsed[3], '', parsed[5]))
        

def remove_params(url, param_keys):
    if not url or not param_keys:
        return url
    params = get_params(url)
    url = remove_all_params(url)
    for key in param_keys:
        if params.has_key(key):
            params.pop(key)
    return add_params_2_url(url, params)
        

def remove_ga_params(url):
    return remove_params(url, GA_PARAMS)
        

def remove_omniture_params(url):
    return remove_params(url, OMNITURE_PARAMS)


def remove_analytics_params(url):
    return remove_params(url, ALL_WEB_ANALYTICS_PARAMS)


def htc(m):
    return chr(int(m.group(1),16))


def urldecode(url):
    rex=re.compile('%([0-9a-hA-H][0-9a-hA-H])', re.M)
    return rex.sub(htc, url.replace('+', ' '))


class UrlFetchResponse:
    def __init__(self, status_code, content, headers):
        self.status_code = status_code
        self.headers = headers
        self.content = content
        

def urlfetch(url, payload=None, headers={}, deadline=None):
    if context.is_client():
        req = urllib2.Request(url, data=payload, headers=headers)
        resp = urllib2.urlopen(req, timeout=deadline)
        """ TODOX handle bad status code """
        return UrlFetchResponse(status_code=resp.code, content=resp.read(), headers=headers)
    else:
        method = 'GET' if payload is None else 'POST'
        from google.appengine.api.urlfetch import fetch as gae_urlfetch
        resp = gae_urlfetch(url, payload=payload, method=method, headers=headers, deadline=deadline)
        return UrlFetchResponse(status_code=resp.status_code, content=resp.content, headers=resp.header_msg)

    
def fetch_url(url, agent=True):
    i = 0
    info = ''
    while i < 3:
        i += 1
        try:
            if agent:
                user = context.get_or_create_context(deploy=deployappspot).app_name()
            else:
                user = 'python'
            headers = {'User-Agent':user}
            req = urllib2.Request(url, headers=headers)
            usock = urllib2.urlopen(req)
            info = usock.read()
            break
        except Exception, e :
            e = str(e)
            if e.find("ApplicationError: 5")!=-1:
                continue
            elif e.find("ApplicationError")!=-1 or e.find("HTTP Error")!=-1 :
                pass
            else:
                logging.exception("Unexpected error in fetch_url() for %s:"  % url)
            break
    return info


class UrlIF(object):
    """
    A common interface for url handling.
    The default implementation assumes the url attribute name is 'url'.
    """
    def normalizedUrl(self):
        return normalize_url(self.url)
    
    def originalUrl(self):
        return self.url


def install_proxy(username, password, port=8008):
    proxyauth = "http://%s:%s@127.0.0.1:%s" % (username, password, port)
    proxy_handler = urllib2.ProxyHandler ( {'http' :proxyauth,} )
    opener= urllib2.build_opener(proxy_handler, urllib2.HTTPBasicAuthHandler(),
                             urllib2.HTTPHandler, urllib2.HTTPSHandler,
                             urllib2.FTPHandler)
    urllib2.install_opener(opener)
            

class SmartRedirectHandler(urllib2.HTTPRedirectHandler): 
    def http_error_301(self, req, fp, code, msg, headers):
        result = urllib2.HTTPRedirectHandler.http_error_301( 
            self, req, fp, code, msg, headers)              
        result.status = code                                 
        return result     
    
    def http_error_302(self, req, fp, code, msg, headers):   
        result = urllib2.HTTPRedirectHandler.http_error_302(
            self, req, fp, code, msg, headers)              
        result.status = code                                
        return result  
    

class RedirectUrlFetchResult():
    def __init__(self, url=None, redirectUrl=None, status=None, contentType=None, content=None, error=False):
        self.url = url
        self.redirectUrl = redirectUrl
        self.status = status  
        self.contentType = contentType
        self.content = content
        self.error = error

    def actualUrl(self, ignore_error=False):
        if self.error and not ignore_error:
            return None
        return self.redirectUrl if self.redirectUrl else self.url
        

def fetch_redirect_url(url, retry=3):
    redirectUrl = None
    status = None
    content = None
    contentType = None
    error = True
    i = 0
    while i < retry:
        i += 1
        try:
            headers = { 'User-Agent' : context.get_or_create_context(deploy=deployappspot).app_name()}
            request = urllib2.Request(url,headers=headers) 
            opener = urllib2.build_opener(SmartRedirectHandler()) 
            f = opener.open(request) 
            content = f.read()
            try:
                contentType = f.info().getheader("Content-Type")
            except:
                pass
            try :
                status = f.status
                if status ==301 or status ==302:
                    redirectUrl = f.url
                    logging.debug("Got redirect url %s for url %s" % (redirectUrl, url))
            except:
                pass
            error = False
            break
        except Exception, e :
            e = str(e)
            if e.find("ApplicationError: 5")!=-1 or e.find("ApplicationError: 2")!=-1:
                continue
            elif e.find("unknown url type")!= -1:
                logging.warning("Unknown URL type! %s" % url)
            elif e.find("Deadline exceeded")!=-1:
                logging.warning("Deadline exceeded when redirecting URL! %s" % url)
            elif e.find("ApplicationError")!=-1:
                pass
            else:
                logging.exception("Error when redirecting for url %s : %s" % (url, str(e)))
            break
    return RedirectUrlFetchResult(url=url,
                          redirectUrl=redirectUrl,
                          status=status,
                          contentType=contentType,
                          content=content,
                          error=error,
                          )


def remove_utm(url):
    index = url.find('?')
    if index==-1:
        return url
    else:
        query = url[index+1:]
        path = url[:index]
        values=query.split('&')
        params={}
        for value in values:
            key,item = urllib.splitvalue(value)
            if key not in GA_PARAMS:
                params[key] = item
        temp = []
        for k,v in params.items():
            if k is not None and v is not None:
                temp.append(k+'='+v)
        if len(temp) > 0:
            params = '&'.join(temp)
            url=path+'?'+params 
        else:
            url = path
        return url


def get_youtube_id(url):
    yid = None
    index = url.find('?')
    if index==-1:
        pass
    else:
        query = url[index+1:]
        values=query.split('&')
        for value in values:
            key,item=urllib.splitvalue(value)
            if key == 'v':
                yid = item
    if yid is None:
        logging.error("Failed to get YouTube id for url: %s" % url)
    return yid
    

def read_gzip(url, check_header=False):
    request = urllib2.Request(url)
    request.add_header('Accept-encoding', 'gzip')
    response = urllib2.urlopen(request)
    if response.info().get('Content-Encoding') == 'gzip' or not check_header:
        buf = StringIO( response.read())
        f = gzip.GzipFile(fileobj=buf)
        data = f.read()
        if response.info().get('Content-Type') == 'application/x-gzip':
            data = gzip.GzipFile(fileobj=StringIO(data)).read()
        return data
    else:
        return None
    

if __name__ == '__main__':
    test_urls = (
        'localhost',
        'localhost:8080',
        None,
        '',
        'abc.co.uk',
        'xyz.abc.co.uk',
        'news.google.com.hk',
        't.co',
        'www.google.com',
        'news.google.com',
        'http://1.news.google.com',
        'http://2.news.google.com:8088',
        ) 

    for url in test_urls:
        print url, scheme_domain(url), root_domain(url)

    test_gn_urls = [
        "http://news.google.com/news/url?sa=t&fd=R&usg=AFQjCNEAF__WWbdU0CCNrefUMEU2xsknxQ&url=http://blogs.fredericksburg.com/books/2012/10/01/desert-illusions/",
        "http://news.google.com/news/url?sa=t&fd=R&usg=AFQjCNGkhFqulOFtqZv26RzRHN5WtievuA&url=http://www.cbsnews.com/8301-202_162-57566042/massive-loss-of-life-in-brazil-nightclub-fire/",
        "http://news.google.com/news/url?sa=t&fd=R&usg=AFQjCNE3Q94nzLLAVMQtKOncw6hEm9rhgA&url=http://www.foxnews.com/world/2013/01/27/french-forces-advance-in-mali-against-radical-islamists-face-acts-harassment/",
        ]    

    for gn_url in test_gn_urls:    
        params = get_params(gn_url)
        if params.has_key('url'):
            print urllib.unquote(params['url'])
        
    
