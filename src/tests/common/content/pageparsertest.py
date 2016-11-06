import unittest
import urllib2

from common.content import pageparser


class TestPageParser(unittest.TestCase):

    def test_standard_parser(self):
        url = "http://variety.com/2015/biz/news/brazil-preps-for-mass-sxsw-attendance-1201449605/"
        usock = urllib2.urlopen(url)
        info = usock.read()
        parser = pageparser.SPageParser()
        parser.feed(info)
        self.assertEqual(parser.og_url, "http://variety.com/2015/digital/news/brazil-preps-for-mass-sxsw-attendance-1201449605/")
        self.assertEqual(parser.og_title, "Brazil Preps for Mass SXSW Attendance")
        self.assertEqual(parser.title, "Brazil Preps for Mass SXSW Attendance   | Variety")
        self.assertEqual(parser.get_title(), parser.og_title)
        

#     def test_reddit_parser(self):
#         url = "http://www.reddit.com/r/atheism/comments/22dedj/gods_plan/"
#         usock = urllib2.urlopen(url)
#         info = usock.read()
#         parser = pageparser.RedditPageParser(url)
#         parser.feed(info)
#         self.assertEqual(parser.reddit, "http://imgur.com/riNzZvW")
        

if __name__ == '__main__':
    unittest.main()
