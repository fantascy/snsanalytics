import unittest

import datetime


from sns.api import consts as api_const
from sns.api import errors as api_error
from client import conf, apiclient
from apitestbase import ApiTest, PostingCampaignApiTest, json


class DummyTest(unittest.TestCase):
    def _testDummy(self):
        self.assertEqual('dummy', 'dummy')

    def testStrDiff(self):
        key1= "agZzYS1kZXZySQsSB2RiX3VzZXIiInVzZXI6YnJ5YW4uc3ByaW5nZXIuc25zYUBnbWFpbC5jb20MCxITcG9zdGluZ19wb3N0aW5ncnVsZRiYJww"
        key2= "agZzYS1kZXZySQsSB2RiX3VzZXIiInVzZXI6YnJ5YW4uc3ByaW5nZXIuc25zYUBnbWFpbC5jb20MCxITcG9zdGluZ19wb3N0aW5ncnVsZRiZJww"
        self.assertNotEqual(key1, key2) 
        for i in range(0, len(key1)) :
            if key1[i] != key2[i] :
                print "key diff found at position %s. value is %s in key1, %s in key2" % (i, key1[i], key2[i])

class ChannelApiTest(ApiTest):
    def getModule(self):
        return api_const.API_M_CHANNEL

    def createWithUniqueNameSuffix(self):
        return False
    

class ArticleApiTest(ApiTest):
    API_MODULE = api_const.API_M_ARTICLE

    def testUpdate(self):
        if self.getModule() is None : return
        self.update({'id':self.testCreate()['id'], 'msg':'update_test', 'descr':'updated ' + str(datetime.datetime.utcnow())})



class FeedApiTest(ApiTest):
    def getModule(self):
        return api_const.API_M_FEED

    def createWithUniqueNameSuffix(self):
        return False
    

class MessageCampaignApiTest(PostingCampaignApiTest):
    def getModule(self):
        return api_const.API_M_POSTING_RULE_ARTICLE

    def getContentModule(self):
        return api_const.API_M_ARTICLE

    def testDeactivate(self, name=None):
        PostingCampaignApiTest.testDeactivate(self, 'Google App Engine Doc 15 min recurring')


class FeedCampaignApiTest(PostingCampaignApiTest):
    def getModule(self):
        return api_const.API_M_POSTING_RULE_FEED

    def getContentModule(self):
        return api_const.API_M_FEED


class CleanApiTest(unittest.TestCase):
    def getModule(self):
        return api_const.API_M_ADMIN
    
    def cleanAll(self):
#        total = 0
#        new_count = 1
#        while new_count>0 :
#            new_count = self._clean(None)
#            total += new_count
        total = self._clean(None)
        print "Total objects deleted: %s" % total

    def cleanChannel(self):
        self._clean('channel_channel')
        self._clean('channel_channelclickcounter')
        self._clean('channel_oauthaccesstoken')
        self._clean('channel_oauthrequesttoken')

    def cleanContent(self):
        self._clean('content_content')
        self._clean('content_feedclickcounter')
    
    def cleanPostingCampaign(self):
        self._clean('posting_postingrule')

    def cleanPosting(self):
        self._clean('posting_posting')

    def cleanPost(self):
        self._clean('posting_post')


    def cleanModels(self):
        """
        Manually change the model to clean all data inside the model.
        """
        modelList = (
#            "db_associatebasepolymodel",
#            "db_userhourlystats",
#            "db_userdailystats",
#            "db_userweeklystats",
#            "db_usermonthlystats",
#            "db_userlifetimestats",
#            "user_userhourlystats",
#            "user_userdailystats",
#            "user_userweeklystats",
#            "user_usermonthlystats",
#            "user_userlifetimestats",
                    )
        for model in modelList :
            self._clean(model)

    def _clean(self, modelName):
        total_count = 0
        count = self._cleanOnce(modelName)
        total_count += count
        while count > 10 :
            count = self._cleanOnce(modelName)
            total_count += count
        return total_count
        
    def _cleanOnce(self, modelName):
        return self._call('clean', dict(model=modelName))
        
    def _call(self, batch_op, params=None):
        module = self.getModule()
        resp_body = self._callApi(module, batch_op, params)
        if apiclient.IS_ADMIN :
            try :
                count = json.loads(resp_body)
                return count
            except :
                self.fail("Admin operation '%s' should return an integer" % batch_op)
        else :
            result = json.loads(resp_body)
            self.assertTrue(type(result)==dict and result.has_key('error_code') and result['error_code']==api_error.API_ERROR_ADMIN_OPERATION)


class CleanOneByOneApiTest(CleanApiTest):
    def _cleanOnce(self, modelName):
        return self._call('clean', dict(model=modelName,oneByOne=True))
        

class CleanUserApiTest(CleanApiTest):
    def getUsers(self):
        """
        Manually change the user email list to clean all data associated with specified users.
        """
        return (
                "chris.helleman.snsa@gmail.com",
                )

    def _cleanOnce(self, modelName):
        count = 0
        for user in self.getUsers() :
            count += self._call('clean', dict(model=modelName,user=user))
        return count


class SysCleanApiTest(unittest.TestCase):
    def getModule(self):
        return api_const.API_M_ADMIN
    
    def cleanQueue(self):
        self._clean('queue')

    def _clean(self, t):
        return self._call('sysclean', dict(type=t))
        
    def _call(self, batch_op, params=None):
        module = self.getModule()
        resp_body = self._callApi(module, batch_op, params)
        if apiclient.IS_ADMIN :
            try :
                count = json.loads(resp_body)
                return count
            except :
                self.fail("Admin operation '%s' should return an integer" % batch_op)
        else :
            result = json.loads(resp_body)
            self.assertTrue(type(result)==dict and result.has_key('error_code') and result['error_code']==api_error.API_ERROR_ADMIN_OPERATION)


if __name__ == "__main__":
    apiclient.login(apiclient.server_domain(), conf.USER_EMAIL, conf.USER_PASSWD, conf.APPLICATION_ID, conf.IS_DEV_SERVER, False)
    unittest.main()


