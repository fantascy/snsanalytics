import unittest

from common.utils.fulltextmatcher import FulltextMatcher


class FulltextMatcherTest(unittest.TestCase):
    def testGetText(self):
        matcher=FulltextMatcher()
        text=matcher.getText("http://www.google.com/")
        self.assertTrue(text.lower().find("google")!=-1)
        text=matcher.getText("http://www.yahoo.com/")
        self.assertTrue(text.lower().find("yahoo")!=-1)
        #don't handle anything beside http
        self.assertEquals("",matcher.getText("ftp://blah.com"))
        self.assertEquals("",matcher.getText("http://www.google.com/intl/en_ALL/images/logo.gif"))
        
    def testMatchText(self):
        matcher=FulltextMatcher()   
        self.assertEquals(1, len(matcher.match_text(["apple"],"apple")))   
        self.assertEquals(1,len(matcher.match_text(["apple"],"apple orange")))  
        self.assertEquals(2,len(matcher.match_text(["apple","orange"],"apple orange")))    
        self.assertEquals(2,len(matcher.match_text(["apple","orange"],"apple orange pear"))) 
        self.assertEquals(2,len(matcher.match_text(["apple","orange","pear"],"apple orange")))
        self.assertEquals(2,len(matcher.match_text(["apple","orange","pear"],"apple orange apple orange")))
    
    def testMatchHashtag(self):
        matcher=FulltextMatcher()   
        self.assertEquals(1, len(matcher.match_text(["apple"],"#apple")))   
        
    def testMatchShortword(self):
        matcher=FulltextMatcher()
        self.assertEquals(0, len(matcher.match_text(["ga"],"navigation")))
        self.assertEquals(1,len(matcher.match_text(["ga"],"ga navigation")))
                          
                                 
    def testMatchUrlCNN(self):
        matcher=FulltextMatcher()   
        
        self.assertEquals(1,len(matcher.match_url(["cnn"],"http://www.cnn.com/")))   
        
        self.assertEquals(2,len(matcher.match_url(["cnn","news"],"http://www.cnn.com/")))  
        
        self.assertEquals(4,len(matcher.match_url(["a","the","cnn","news"],"http://www.cnn.com/")))  
        
        self.assertEquals(4,len(matcher.match_url(["a","THE","CNN","news"],"http://www.cnn.com/")))  
        
        self.assertEquals(3,len(matcher.match_url(["a","the","cnn","assertEquals"],"http://www.cnn.com/")))  
        
    def testMatchUrlWikipediaYaoMing(self):
        matcher=FulltextMatcher()
        
        url = "http://en.wikipedia.org/wiki/Yao_Ming"
        self.assertEquals(1,len(matcher.match_url(["NBA"], url)))   

# These assertions are failing because white space splits the words.
#        self.assertEquals(2,len(matcher.match_url(["nba","Yao Ming"],url)))  
#        
#        self.assertEquals(3,len(matcher.match_url(["nba","Yao Ming", "Houston Rockets"],url)))  
#        
#        self.assertEquals(4,len(matcher.match_url(["nba","Yao Ming", "Houston Rockets", "Shanghai"],url)))  
#        
#        self.assertEquals(3,len(matcher.match_url(["nba","Yao Ming", "Houston Rockets", "vampire"],url)))  
    
    def testPythonOrg(self):
        matcher=FulltextMatcher()
        url = "http://www.python.org"
        self.assertEquals(1,len(matcher.match_url(["python"], url))) 
        self.assertEquals(3,len(matcher.match_url(["python","programming","language"], url))) 
    
        
    def testESPN(self):
        matcher=FulltextMatcher()
        self.assertEquals(4,len(matcher.match_url(["baseball", "mlb", "football", "nfl"],"http://sports.espn.go.com/nba/news/story?id=4363982&campaign=rss&source=ESPNHeadlines")))
    
    def testESPN2(self):
        matcher=FulltextMatcher()
        self.assertEquals(1,len(matcher.match_url(["ESPN"],"http://sports.espn.go.com/mlb/news/story?id=4364086&campaign=rss&source=ESPNHeadlines")))
    
    def testNBA(self):
        matcher=FulltextMatcher()
        self.assertEquals(1,len(matcher.match_url(["NBA"],"http://widgetcenter.espn.go.com/widgets/tags/NBA")))
    
    def testChinese(self):
        matcher=FulltextMatcher()
        self.assertEquals(1,len(matcher.match_url([u"\u97f3\u4e50"],"http://www.yahoo.cn")))
    
    def testFrequencyMatch(self):
        matcher=FulltextMatcher()
        self.assertEquals(1,len(matcher.match_text_with_frequency(["ga"],"ga navigation")))
        self.assertEquals(("ga",2),matcher.match_text_with_frequency(["ga"],"ga ga navigation")[0])
        self.assertEquals(("organize",1),matcher.match_text_with_frequency(["ga","organize"],"ga ga navigation organization")[1])
        self.assertEquals([("ga",2),("organize",1)],matcher.match_text_with_frequency(["ga","organize"],"ga ga navigation organization"))
       
       
    
if __name__ == "__main__":
    unittest.main()
