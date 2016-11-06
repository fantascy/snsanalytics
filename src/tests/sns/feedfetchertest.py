#from datetime import datetime
import unittest

from common.content import feedfetcher


class FeedFetcherTest(unittest.TestCase):
#    def testStatic(self):   
#        fetcher = FeedFetcher("http://feedparser.org/docs/examples/atom10.xml")
#        #this sample feed should never change, so we use it to compare contents
#        entries = fetcher.fetch(datetime(2000, 1, 1))
#        self.assertEquals(1, len(entries))
#        self.assertEquals("http://example.org/entry/3",entries[0].url)
#        self.assertEquals("First entry title",entries[0].title)
##        self.assertEquals("Watch out for nasty tricks",entries[0].keywords)
#        entries = fetcher.fetch(datetime(2009, 1, 1))
#        self.assertEquals(0, len(entries))
#    
#    def testDyanmic(self):
#        #test some real feed
#        #it's an educated guess that these sites won't do something crazy
#        for feedurl in ('http://sports.yahoo.com/top/rss.xml', 'http://rss.cnn.com/rss/cnn_topstories.rss', 
#                        'http://news.google.com/news?pz=1&ned=us&hl=en&topic=h&num=3&output=rss'):
#            fetcher = FeedFetcher(feedurl)
#            #it shouldn't publish in the future
#            self.assertTrue(len(fetcher.fetch(datetime.utcnow())) == 0)
#        
#            entries = fetcher.fetch(datetime(2009, 6, 1))
#            #there must be more something after 2009-06-01
#            self.assertTrue(len(entries) > 1)
#
#    def testKeywords(self):
#        entries = FeedFetcher("http://www.feedparser.org/tests/wellformed/rss/item_category.xml").fetch(datetime(1990,1,1))
#        self.assertEquals(['Example', 'category'], entries[0].keywords)
#        
#        entries = FeedFetcher("http://www.feedparser.org/tests/wellformed/atom10/entry_category_term.xml").fetch()
#        self.assertEquals(['atom10'], entries[0].keywords)
        
#    def testNull(self):
#        entries = FeedFetcher("http://www.feedparser.org/tests/wellformed/rss/item_category.xml").fetch()
#        self.assertEquals(1, len(entries))
    
    def testTitle(self):
        self.assertTrue(FeedFetcher("http://www.bizjournals.com/rss/feed/daily/sanfrancisco").title is not None)
    
    def testInvalid(self):
        self._isNotValid("http://example.com/a.xml")
        self._isNotValid("abc")
        
#    def testMisesBlog(self):
#        self._isValid("http://blog.mises.org/blog/atom.xml")
    
#    def testSpaceInUrl(self):
#        self._isValid("http://blog.mises.org/blog/atom.xml ")
    
    def testSanFrancisco(self):
        self._isValid("http://www.bizjournals.com/rss/feed/daily/sanfrancisco")
    
    def testAlltop(self):
        self._isValid("http://sports.alltop.com/rss/")
        self._isValid("http://nba.alltop.com/rss")
        
#    def testSummary(self):
#        """feed keywords should include summary now"""
#        entries = FeedFetcher("http://www.feedparser.org/tests/wellformed/atom/entry_summary.xml").fetch()
#        self.assertTrue(entries[0].keywords.index("Example")!=-1)
        
    def testDelicious(self):
        """test delicious http://feeds.delicious.com/v2/rss/barryhoggard/cptweet?count=15"""
        entries= FeedFetcher("http://feeds.delicious.com/v2/rss/barryhoggard/cptweet?count=15").fetch()
        self.assertTrue(len(entries)>0)
        self.assertNotEquals(None, FeedFetcher("http://feeds.delicious.com/v2/rss/barryhoggard/cptweet?count=15").title)
    
    def testGlif(self):
        fetcher=FeedFetcher("http://feed.glif.cn/")
        self.assertNotEquals(None, fetcher.title)
        entries= fetcher.fetch()
        self.assertTrue(len(entries)>0)

    def testTwitterTimeline(self):
        self._isValid("http://twitter.com/statuses/user_timeline/23243741.rss")
    
    def _isValid(self, url):
        self.assertTrue(FeedFetcher(url).isValid)
        
    def _isNotValid(self, url):
        self.assertFalse(FeedFetcher(url).isValid)
        
    
if __name__ == "__main__":
    unittest.main()

