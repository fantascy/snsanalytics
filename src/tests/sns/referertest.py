import unittest

from google.appengine.ext import db

    
class ReferrerCounterIF(db.Model):
    """
    HTTP referrer counter. If the referrer is twitter.com, we count it as twitter; otherwise we count it as direct
    """
    twitter = db.IntegerProperty(default=0,required=True)
    direct = db.IntegerProperty(default=0,required=True)
    
    def incrementReferer(self,referrer=None):
        if referrer and referrer.find("twitter.com")!=-1:
            self.twitter+=1
        else:
            self.direct+=1
            
class ReferrerTest(unittest.TestCase):
    def testIncrement(self):
        counter=ReferrerCounterIF()
        self.assertEquals(0,counter.twitter);
        self.assertEquals(0,counter.direct);
        counter.incrementReferer("http://www.twitter.com")
        self.assertEquals(1,counter.twitter)
        counter.incrementReferer("http://www.twitter.com")
        self.assertEquals(2,counter.twitter)
        counter.incrementReferer()
        self.assertEquals(2,counter.twitter)
        self.assertEquals(1,counter.direct)
        counter.incrementReferer("www.google.com")
        self.assertEquals(2,counter.direct)
        counter.incrementReferer("")
        self.assertEquals(3,counter.direct)
        counter.incrementReferer(None)
        self.assertEquals(4,counter.direct)


if __name__ == "__main__":
    unittest.main()
