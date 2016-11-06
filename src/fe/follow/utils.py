import json
import urllib
import logging

from common import consts as common_const
from fe import consts as fe_const


def always_rated_limited(handle):
    return handle.lower() in fe_const.ALWAYS_RATE_LIMITED


def fe_master_backend_endpoint():
    return "http://prod.ripple1app.appspot.com" 


def fe_master_endpoint():
    return "http://www.snsanalytics.com" 


def fe_master_backend_req_url(path):
    return "%s/%s" % (fe_master_backend_endpoint(), path)


def fe_master_req_url(path):
    return "%s/%s" % (fe_master_endpoint(), path)


def fe_master_urlopen(url):
    """ Return a tuple of two. """
    retry = 3
    while retry:
        try:
            resp = urllib.urlopen(url).read()
            if resp:
                logging.debug("url %s response: %s" % (url, resp))
                resp = json.loads(resp)
                return resp[common_const.JSON_HTTP_RESPONSE_ATTR_STATE], resp[common_const.JSON_HTTP_RESPONSE_ATTR_DATA]
        except Exception:
            if not retry:
                logging.exception("Failed making FE master request: %s" % url)
        retry -= 1
    return False, None


