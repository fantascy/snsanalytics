import unittest
import json
import urllib2

from sns.core.core import get_user
from sns.api import consts as api_const
from sns.api import errors as api_error
from client import conf, apiclient


class URLShortenerTest(unittest.TestCase):
    def getModule(self):
        return api_const.API_M_URLSHORTENER
    
    def getId(self):
        query_resp_body=apiclient.call_api(apiclient.server_api_domain(), self.getModule(), 'query',dict(limit=1))
        result = json.loads(query_resp_body)[0]
        return result['id'] 
        
    def testQuery(self):
        resp_body=apiclient.call_api(apiclient.server_api_domain(), self.getModule(), 'query',dict(limit=5))
        result = json.loads(resp_body)      
        for item in result:
            original_url=str(item['url'])
            urlHash=str(item['urlHash'])
            shorturlquery='http://%s/api/%s/%s?urlHash=%s'%(apiclient.server_domain(),self.getModule(),'query',urlHash)
            req_shorturl = urllib2.Request(shorturlquery)
            resp_shorturl = urllib2.urlopen(req_shorturl)
            resp_shorturl_body= resp_shorturl.read()
            redirect_result=json.loads(resp_shorturl_body)
            redirect_url=str(redirect_result[0]['url'])
            self.assertEqual(original_url,redirect_url)
            
       
    def testCreate(self):
        obj = {'url':'www.163.com','parent':get_user()}
        serv_resp_body=apiclient.call_api(apiclient.server_api_domain(), self.getModule(), 'create', obj, 'json')  
        result = json.loads(serv_resp_body)
        self.assertTrue(type(result)==dict and result.has_key('id')) 
   
    def testDelete(self):        
        id=self.getId()
        resp_body=apiclient.call_api(apiclient.server_api_domain(), self.getModule(), 'delete',{'id':id})
        result=json.loads(resp_body)
        self.assertTrue(type(result)==dict and result.has_key('error_code') and result['error_code']==api_error.API_ERROR_UNSUPPORTED_OPERATION)
        
    def testGet(self):
        id=self.getId()
        resp_body=apiclient.call_api(apiclient.server_api_domain(), self.getModule(), 'get',{'id':id})
        result=json.loads(resp_body)
        self.assertTrue(type(result)==dict)
        
    def testUpdate(self):
        id=self.getId()
        resp_body=apiclient.call_api(apiclient.server_api_domain(), self.getModule(), 'update',{'id':id})
        result=json.loads(resp_body)
        self.assertTrue(type(result)==dict and result.has_key('error_code') and result['error_code']==api_error.API_ERROR_UNSUPPORTED_OPERATION)
 
                                        
if __name__ == "__main__":
    
  # apiclient.login(apiclient.server_domain(), conf.ADMIN_USER, conf.ADMIN_PASSWD, conf.APPLICATION_ID, conf.IS_DEV_SERVER, True)    
    apiclient.login(apiclient.server_domain(), conf.USER_EMAIL, conf.USER_PASSWD, conf.APPLICATION_ID, conf.IS_DEV_SERVER, False)
    unittest.main()