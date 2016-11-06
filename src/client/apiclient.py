import time
import urllib
import urllib2
import cookielib
import logging
import json

import deploysns, deployglobal
from client import conf
from sns.api import consts as api_const


IS_LOGGED_IN = False
IS_ADMIN = False


def login_as_admin():
    login(server_domain(), conf.ADMIN_USER, conf.ADMIN_PASSWD, conf.APPLICATION_ID, conf.IS_DEV_SERVER, True)


def login_as_user():
    login(server_domain(), conf.USER_EMAIL, conf.USER_PASSWD, conf.APPLICATION_ID, conf.IS_DEV_SERVER, False)


def login(host, userEmail, user_passwd, app_name, is_dev_server, admin=False):
    global IS_ADMIN
    IS_ADMIN = admin

    global IS_LOGGED_IN
    if IS_LOGGED_IN:
        logging.debug("Already logged in!")
        return True
    
    hostUrl = "http://%s" % host

    #  we use a cookie to authenticate with Google App Engine
    #  by registering a cookie handler here, this will automatically store the 
    #  cookie returned when we use urllib2 to open http://hostname/_ah/login
    cookiejar = cookielib.LWPCookieJar()
    opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cookiejar))
    urllib2.install_opener(opener)
    
    #
    # get an AuthToken from Google accounts
    #
    auth_uri = 'https://www.google.com/accounts/ClientLogin'
    authreq_data = urllib.urlencode({ "Email":   userEmail,
                                      "Passwd":  user_passwd,
                                      "service": "ah",
                                      "source":  app_name,
                                      "accountType": "HOSTED_OR_GOOGLE" })
    auth_req = urllib2.Request(auth_uri, data=authreq_data)
    auth_resp = urllib2.urlopen(auth_req)
    auth_resp_body = auth_resp.read()
    # auth response includes several fields - we're interested in the bit after Auth= 
    auth_resp_dict = dict(x.split("=")
                          for x in auth_resp_body.split("\n") if x)
    authtoken = auth_resp_dict["Auth"]
    
    #
    # get a cookie
    # 
    #  the call to request a cookie will also automatically redirect us to the page
    #   that we want to go to
    #  the cookie jar will automatically provide the cookie when we reach the 
    #   redirected location
    
    serv_args = {}
    if is_dev_server :
        serv_args['email']     = userEmail
        serv_args['action']     = 'Login'
        serv_args['admin']     = admin
    else :
        serv_args['auth']     = authtoken
        serv_args['continue'] = hostUrl
    full_serv_uri = hostUrl + "/_ah/login?%s" % (urllib.urlencode(serv_args))
    
    serv_req = urllib2.Request(full_serv_uri)
    serv_resp = urllib2.urlopen(serv_req)
    IS_LOGGED_IN = True
    return serv_resp.read()


def call_api(hostname, moduleName, operation, params=None, fmt='json', http_method=None, log=True):
    apiurl = "http://%s/api/%s/%s" % (hostname, moduleName, operation)
    if not http_method:
        http_method = api_const.get_api_http_method(operation)
    postData = None
    getStr = ""
    if params is not None and len(params) > 0 :
        formatted_params = params.items()
        if fmt == 'json' :
            formatted_params = {'json' : json.dumps(params)}
        if http_method == api_const.API_HTTP_METHOD_POST:
            postData = urllib.urlencode(formatted_params)
        else :
            getStr = "?%s" % urllib.urlencode(formatted_params)
    retry = 3
    while retry:
        retry -= 1
        try:
            fullurl = "%s/%s" % (apiurl, getStr)
            serv_req = urllib2.Request(fullurl, data = postData)
            serv_resp = urllib2.urlopen(serv_req)
            serv_resp_body = serv_resp.read()
            if log :
                logging.debug("%s\n%s" % (fullurl, serv_resp_body))
            return json.loads(serv_resp_body)
        except urllib2.HTTPError, ex:
            error_msg = "API call failed with HTTPError %d %s. %s" % (ex.code, ex.reason, apiurl)
            if retry:
                logging.debug(error_msg)
            else:
                logging.error(error_msg)
                if ex.code == 503:
                    logging.info("Sleep for 60 seconds then try again. %s" % apiurl)
                    time.sleep(60)
                    retry = 3
        except Exception, ex:
            error_msg = "API call failed with general error. %s %s" % (str(ex), apiurl)
            if retry:
                logging.debug(error_msg)
            else:
                logging.error(error_msg)
    return {'error_code': -1, 'error_msg': "Failed sending API request from client."}


def is_error_response(resp):
    if resp is None :
        return False
    if type(resp)==list :
        resp = resp[0]
    return type(resp)==dict and resp.has_key('error_code')


def server_domain():
    """
    The convenient function to get the server domain based on server configuration.
    You should not need to modify this function to run your test cases, or any client side agent.  
    """
    if conf.SERVER_DOMAIN: return conf.SERVER_DOMAIN
    if conf.IS_DEV_SERVER: return 'localhost:8080'
    domain = deployglobal.APPSPOT_DOMAIN_MAP.get(conf.APPLICATION_ID, None)
    if domain is None : 
        domain = conf.APPLICATION_ID + '.appspot.com'
    if conf.BACKEND:
        domain = "%s.%s" % (conf.BACKEND, domain)
    return domain


def server_short_domain():
    """
    The convenient function to get the server short domain based on server configuration.
    You should not need to modify this function to run your test cases, or any client side agent.  
    """
    if conf.IS_DEV_SERVER :
        return 'localhost:8080'

    short_domain = deploysns.SHORT_DOMAIN_MAP.get(conf.APPLICATION_ID, None)
    if short_domain is None : 
        short_domain = conf.APPLICATION_ID + '.appspot.com'
    
    return short_domain


def server_api_domain():
    """
    The convenient function to get the server api domain based on server configuration.
    You should not need to modify this function to run your test cases, or any client side agent.  
    """
    return server_domain()


def server_port():
    if conf.IS_DEV_SERVER :
        return 8080
    else :
        return 80


if __name__ == '__main__':
    login_as_admin()
    print "API client logged in successfully!"

