import unittest

import json

from client import conf, apiclient


class CampaignTest(unittest.TestCase):
    def testScheduleStart(self):
        result = self._queryAll()
        brackets = {}
        for item in result :
            try :
                bracket = item.get("scheduleStart").split(':')[1]
            except :
                bracket = "--"
            count = brackets.get(bracket, 0)
            count += 1
            brackets[bracket] = count
        keys = brackets.keys()
        keys.sort()
        for key in keys :
            print "%s : %s" % (key, brackets[key])
            
    def _queryAll(self):
        module = 'post/rule/feed'
        method = 'query'
        result = []
        offset = 0
        while True :
            params = {'offset':offset, 'limit':1000, 'deleted':False}
            rules_json = apiclient.call_api(apiclient.server_api_domain(), module, method, params, log=False)
            resp = json.loads(rules_json)
            if apiclient.is_error_response(resp) :
                print resp
                break
            print "count=%s; offset=%s" % (len(resp), offset) 
            result = result + resp
            if len(resp)<1000 :
                break
            offset += 1000
        return result


if __name__ == "__main__":
    apiclient.login(apiclient.server_domain(), conf.ADMIN_USER, conf.ADMIN_PASSWD, conf.APPLICATION_ID, conf.IS_DEV_SERVER, True)
    unittest.main()