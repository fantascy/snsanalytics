import unittest
import json

from sns.api import consts as api_const
from sns.api import errors as api_error
from client import conf, apiclient


class UserApiTest(unittest.TestCase):
    def getModule(self):
        return api_const.API_M_USER
    
    def testApprove(self, userEmail=None):
        if userEmail is None :
            userEmail = conf.USER_EMAIL
        resp_body=apiclient.call_api(apiclient.server_api_domain(), self.getModule(), 'approve', dict(email=userEmail))
        if apiclient.IS_ADMIN:
            try:
                bool(resp_body)
            except:
                self.fail("A boolean should be returned")
        else :
            result = json.loads(resp_body)
            self.assertTrue(type(result)==dict and result.has_key('error_code') and result['error_code']==api_error.API_ERROR_ADMIN_OPERATION)
        
        

    def testUpgrade(self, userEmail=None):
        if userEmail is None :
            userEmail = conf.USER_EMAIL
        resp_body=apiclient.call_api(apiclient.server_api_domain(), self.getModule(), 'upgrade', dict(email=userEmail))
        if apiclient.IS_ADMIN :
            try:
                bool(resp_body)
            except:
                self.fail("A boolean should be returned")
        else :
            result = json.loads(resp_body)
            self.assertTrue(type(result)==dict and result.has_key('error_code') and result['error_code']==api_error.API_ERROR_ADMIN_OPERATION)
        
if __name__ == "__main__":
    apiclient.login(apiclient.server_domain(), conf.ADMIN_USER, conf.ADMIN_PASSWD, conf.APPLICATION_ID, conf.IS_DEV_SERVER, True)
    unittest.main()
