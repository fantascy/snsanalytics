import unittest
import urllib2
import json

from sns.api import consts as api_const
from client import conf, apiclient


class CounterTest(unittest.TestCase):
    def getModule(self):
        return api_const.API_M_URLSHORTENER
    
    def getUrlHash(self):
        urlHash_list=[]
        resp_body = apiclient.call_api(apiclient.server_api_domain(), self.getModule(), 'query')
        result = json.loads(resp_body)
        for item in result:
            urlHash=str(item['urlHash'])
            print urlHash
            urlHash_list.append(urlHash)
        return urlHash_list
        
    
    def getTotalCount(self,urlHash):
        totalcount=0
        url='http://%s/%s/%s/%s'%(apiclient.server_domain(),self.getModule(),'listCount',urlHash)
        req=urllib2.Request(url)
        resp=urllib2.urlopen(req)
        body=resp.read()
        lines=body.splitlines();
        for index in range(len(lines)):
            item=lines[index]
            sign=item.strip()
            if(sign=='<td> %s </td>'%urlHash):
                click=lines[index+3]
                num=int(click.replace('<td>','').replace('</td>','').strip())
                totalcount+=num
        print totalcount
        return totalcount
    
    def doClick(self,urlHash,times=1):
        for time in range(times):
            doclick_url='http://%s/%s'%(apiclient.server_domain(),urlHash)
            req=urllib2.Request(doclick_url)
            resp=urllib2.urlopen(req)
            
    def testCountIncrease(self):
        increase_time=1
        urlHashList=self.getUrlHash()
        for urlHash in urlHashList:
            formercount=self.getTotalCount(urlHash)
            self.doClick(urlHash,times=increase_time)
            currentcount=self.getTotalCount(urlHash)
            self.assertEqual((formercount+increase_time),currentcount)
            
                
    
if __name__ == "__main__":
    apiclient.login(apiclient.server_domain(), conf.USER_EMAIL, conf.USER_PASSWD, conf.APPLICATION_ID, conf.IS_DEV_SERVER, False)
    unittest.main()    
    