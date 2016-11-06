import unittest

from common.utils import url as url_util 


class UrlUtilTest(unittest.TestCase):
    def testGoodUrl(self):
        self.assertTrue(url_util.is_valid_url("http://www.google.com"))
        self.assertTrue(url_util.is_valid_url("ftp://blah.com"))
        self.assertTrue(url_util.is_valid_url("http://www.google.com/intl/en_ALL/images/logo.gif"))
        self.assertTrue(url_util.is_valid_url("http://us.rd.yahoo.com/sports/rss/top/SIG=12a2ctvs8/*http%3A//sports.yahoo.com/pga/news?slug=ap-britishopen&prov=ap&type=lgns"))
        self.assertTrue(url_util.is_valid_url("https://www.google.com"))
        self.assertTrue(url_util.is_valid_url("http://abc.com:8080/abc"))
        self.assertTrue(url_util.is_valid_url("https://free2.projectlocker.com/SnsAnalytics/SNS_Campaign_Manager/trac/ticket/78"))
        self.assertTrue(url_util.is_valid_url("http://64.233.161.104/"))
        self.assertTrue(url_util.is_valid_url("http://ABC.COM/"))
        self.assertTrue(url_util.is_valid_url("http://www.google.com?ie=7"))

    def testSanitzie(self):
        self.assertEquals("http://www.google.com",url_util.sanitize_url(" www.google.com  "))
        self.assertEquals("http://www.google.com",url_util.sanitize_url("www.google.com"))
        self.assertEquals("http://www.google.com",url_util.sanitize_url("http://www.google.com"))
        self.assertFalse(url_util.sanitize_url("google"))
        self.assertFalse(url_util.sanitize_url("ht://abc.com"))
        self.assertFalse(url_util.sanitize_url("http//abc"))
        
    def testBadUrl(self):
        self.assertFalse(url_util.is_valid_url("no"))
        self.assertFalse(url_util.is_valid_url("ht://abc.com"))
        self.assertFalse(url_util.is_valid_url("http//abc"))

    def testNormalization(self):
        self.assertEquals("http://www.abc.com/?id=7",url_util.normalize_url("HTTP://www.abc.com?id=7"))
        self.assertEquals("http://www.abc.com/",url_util.normalize_url("HTTP://www.abc.com"))
        self.assertEquals("http://www.abc.com/",url_util.normalize_url(u"HTTP://www.abc.com"))
        self.assertEquals("http://www.abc.com/",url_util.normalize_url("HTTP://WWW.ABC.COM"))
        self.assertEquals("http://zh.wikipedia.org/zh-cn/%E4%B8%83%E5%A4%95",url_util.normalize_url(u" http://zh.wikipedia.org/zh-cn/\u4E03\u5915"))
        self.assertEquals("http://zh.wikipedia.org/zh-cn/%E4%B8%83%E5%A4%95",url_util.normalize_url(u"http://zh.wikipedia.org/zh-cn/%E4%B8%83%E5%A4%95"))
        
    def testMixUpParam(self):
        self.assertEquals("MTEx",url_util.encode_base64(111))
        self.assertEquals("YWJj",url_util.encode_base64('abc'))
        self.assertEquals("YWJj",url_util.encode_base64(u'abc'))
        
    def testDeMixUpParam(self):
        self.assertEquals("111",url_util.decode_base64('MTEx'))
        self.assertEquals("abc",url_util.decode_base64('YWJj'))
        self.assertEquals(u"abc",url_util.decode_base64('YWJj'))
    
    def testAddParams(self):
        url0 = "http://www.domain1.com:80/path"
        self.assertEquals(url0, url_util.add_params_2_url(url0, {}))
        self.assertEquals(url0+"?p1=v1", url_util.add_params_2_url(url0, {'p1':'v1'}))
        url1 = "http://www.domain1.com:80/path?p1=v1"
        self.assertEquals(url1, url_util.add_params_2_url(url1, {}))
        self.assertEquals(url1, url_util.add_params_2_url(url1, {'p1':'v1'}))
        url2 = "http://www.domain1.com:80/path#frag&p3=v3"
        self.assertEquals(url2, url_util.add_params_2_url(url2, {}))
        self.assertTrue(url_util.is_valid_url(url_util.add_params_2_url(url2, {'p3':'v3'})))


if __name__ == "__main__":
    unittest.main()
