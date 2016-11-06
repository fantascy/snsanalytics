import unittest

from common.utils.pageparser import PageFeedUrlParser


class PageFeedUrlParserTest(unittest.TestCase):
    def testWordpress(self):
        self.assertEquals("http://snsanalytics.wordpress.com/feed/", PageFeedUrlParser("http://snsanalytics.wordpress.com/").findFeedUrl())
        self.assertEquals("http://blog.snsanalytics.com/?feed=rss2", PageFeedUrlParser("http://blog.snsanalytics.com/").findFeedUrl())
        self.assertEquals("http://blog.snsanalytics.com/?feed=rss2", PageFeedUrlParser("http://everyonedeserves.me").findFeedUrl())
        self.assertEquals("http://blog.snsanalytics.com/?feed=rss2", PageFeedUrlParser("http://www.everyonedeserves.me").findFeedUrl())
    
    def testBlogger(self):
        self.assertEquals("http://lanl-the-rest-of-the-story.blogspot.com/feeds/posts/default", PageFeedUrlParser("http://lanl-the-rest-of-the-story.blogspot.com/").findFeedUrl())

    def testAlltop(self):
        self.assertEquals("http://npr.alltop.com/rss/", PageFeedUrlParser("http://npr.alltop.com/").findFeedUrl())
    
    def testYahoo(self):
        self.assertEquals("http://sports.yahoo.com/top/rss.xml", PageFeedUrlParser("http://sports.yahoo.com/").findFeedUrl())
        

if __name__ == "__main__":
    unittest.main()

        