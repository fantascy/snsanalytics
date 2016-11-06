import unittest
import urllib2
from datetime import datetime


class TwitterConnTest(unittest.TestCase):
    def testConn(self):
        for url in ("http://www.twiiter.com","http://twitter.com/bryanspringer","http://twitter.com/oauth/request_token?oauth_nonce=2385316106298316508&oauth_timestamp=1251686009&oauth_consumer_key=arn9d2HSISvFD6sXYbWFQ&oauth_signature_method=HMAC-SHA1&oauth_version=1.0&oauth_signature=%2FuugShzwjws8HWKRxIqmZ4L8Ebs%3D","https://twitter.com/oauth/request_token?oauth_nonce=2385316106298316508&oauth_timestamp=1251686009&oauth_consumer_key=arn9d2HSISvFD6sXYbWFQ&oauth_signature_method=HMAC-SHA1&oauth_version=1.0&oauth_signature=%2FuugShzwjws8HWKRxIqmZ4L8Ebs%3D"):
            print "%s: start request %s"%(datetime.now().isoformat(),url)           
            try:
                content=urllib2.urlopen(url).read()
                print "return", " ".join(content[:500].split())
            except Exception,ex:
                print "get error %s"%(ex,)
            print "%s: finish request %s"%(datetime.now().isoformat(),url) 
                        

if __name__ == "__main__":
    unittest.main()