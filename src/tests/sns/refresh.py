import unittest
from sns.api import consts as api_const
import json

from client import conf, apiclient

MODULE_LIST = [api_const.API_M_CHANNEL, api_const.API_M_ARTICLE, api_const.API_M_FEED, api_const.API_M_POSTING_RULE, api_const.API_M_POSTING_POST, api_const.API_M_URLSHORTENER, api_const.API_M_URL_COUNTER]
COUNTER_LIST = [api_const.API_M_URL_COUNTER,api_const.API_M_CHANNEL_COUNTER,api_const.API_M_FEED_COUNTER,api_const.API_M_SURL_COUNTER,api_const.API_M_USER_COUNTER]


class RefreshTest(unittest.TestCase):
    def _testAllModelUpdate(self):
        users_json = apiclient.call_api(apiclient.server_api_domain(), 'user', 'queryall')
        users=json.loads(users_json)
        emails=[]
        for user in users:
            emails.append(user['user'])
        
        for email in emails:
            for module in COUNTER_LIST:
                moduleName = module
                operation = 'refresh'
                params = {'email':email}
                go_on=True
                while go_on:                
                    resp = apiclient.call_api(apiclient.server_api_domain(), moduleName, operation, params)
                    result=json.loads(resp)
                    if type(result)==list:
                        date=result[0]
                        params= {'email':email,'date':date}             
                    else:
                        go_on=False
                                
        print 'over'
    
    def _testUserUpdate(self):
        users_json = apiclient.call_api(apiclient.server_api_domain(), 'user', 'queryall')
        return
        users=json.loads(users_json)
        emails=[]
        for user in users:
            emails.append(user['user'])
            
        for email in emails:
            moduleName=api_const.API_M_USER
            operation = 'refresh'
            params = {'email':email}
            apiclient.call_api(apiclient.server_api_domain(), moduleName, operation, params)
            
        print 'over'


if __name__ == "__main__":
    apiclient.login(apiclient.server_domain(), conf.ADMIN_USER, conf.ADMIN_PASSWD, conf.APPLICATION_ID, conf.IS_DEV_SERVER, True)
    unittest.main()