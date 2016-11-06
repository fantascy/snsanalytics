import unittest
import json

from client import conf, apiclient


class RefreshTest(unittest.TestCase):
    def testUserUpdate(self):
        offset = 0
        params = {'offset':offset,'type':type}
        go_on=True
        while go_on:
            rules_json = apiclient.call_api(apiclient.server_api_domain(), 'chan', 'queryall', params)
            result=json.loads(rules_json)
            if len(result) == 1:
                go_on =False
            elif len(result) == 2:
                go_on = True
                offset = result[1]
                params = {'offset':offset,'type':type}
        print 'over'


if __name__ == "__main__":
    apiclient.login(apiclient.server_domain(), conf.ADMIN_USER, conf.ADMIN_PASSWD, conf.APPLICATION_ID, conf.IS_DEV_SERVER, True)
    unittest.main()