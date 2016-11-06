import unittest
import json

from sns.api import consts as api_const
from client import conf, apiclient
import testdata
from apitest import FeedCampaignApiTest, MessageCampaignApiTest


def setupUsers():
    """
    The purpose is to run this single test case to setup the two test users we have: one regular user bryan..., one admin user qa07.sa
    1. Log in once as the regular user bryan, so that the user object can be created into the db
    2. Log in as admin once as the admin user qa07.sa, so that the admin user object can be created into the db
    3. Update admin ser qa07.sa settings (First Name, Last Name, Timezone)
    4. Approve the regular user bryan
    5. Log in as user bryan again, and update user bryan's settings (First Name, Last Name, Timezone)
    """
    apiclient.login(apiclient.server_domain(), conf.USER_EMAIL, conf.USER_PASSWD, conf.APPLICATION_ID, conf.IS_DEV_SERVER, False)
    apiclient.login(apiclient.server_domain(), conf.ADMIN_USER, conf.ADMIN_PASSWD, conf.APPLICATION_ID, conf.IS_DEV_SERVER, True)
    params=testdata.USERS[1]
    params['id']=getUserId(conf.ADMIN_USER)
    apiclient.call_api(apiclient.server_api_domain(), api_const.API_M_USER, 'update', params)
    apiclient.call_api(apiclient.server_api_domain(), api_const.API_M_USER, 'approve', dict(email=conf.USER_EMAIL))
    apiclient.login(apiclient.server_domain(), conf.USER_EMAIL, conf.USER_PASSWD, conf.APPLICATION_ID, conf.IS_DEV_SERVER, False)
    params=testdata.USERS[0]
    params['id']=getUserId(conf.USER_EMAIL)
    apiclient.call_api(apiclient.server_api_domain(), api_const.API_M_USER, 'update', params)
    


        
def setupData():
    """
    Execute the following commands equivalent to populate the datastore with basic test data. 
    python sns/test/apitest.py FeedCampaignApiTest;
    python sns/test/adminapitest.py FeedCampaignApiTest.testBatchPost;
    python sns/test/apitest.py MessageCampaignApiTest;
    python sns/test/adminapitest.py MessageCampaignApiTest.testBatchPost
    """
    apiclient.login(apiclient.server_domain(), conf.USER_EMAIL, conf.USER_PASSWD, conf.APPLICATION_ID, conf.IS_DEV_SERVER, False)
    unittest.main()
    apiclient.login(apiclient.server_domain(), conf.ADMIN_USER, conf.ADMIN_PASSWD, conf.APPLICATION_ID, conf.IS_DEV_SERVER, True)
    #FeedCampaignApiTest().testBatchPost()
    #MessageCampaignApiTest().testBatchPost()
    apiclient.call_api(apiclient.server_api_domain(), api_const.API_M_POSTING_RULE_FEED, 'batch_post')
    apiclient.call_api(apiclient.server_api_domain(), api_const.API_M_POSTING_RULE_ARTICLE, 'batch_post')
    
def getUserId(email):
    resp=apiclient.call_api(apiclient.server_api_domain(), api_const.API_M_USER, 'query')
    users=json.loads(resp)
    for user in users:
        if user['user']==email:
            return user['id']
    return None


class FeedRuleTest(FeedCampaignApiTest):
    pass


class ArticleRuleTest(MessageCampaignApiTest):
    pass

   
        
if __name__ == "__main__":
    """
    Run setup, with command line options to run only setupUsers() or only setupData().
    """
    setupUsers()
    setupData()