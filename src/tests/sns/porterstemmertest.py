import unittest

from common.utils.porter import PorterStemmer


class ReferrerTest(unittest.TestCase):
    def testStemmer(self):
        stemmer=PorterStemmer()
        self.assertEquals("appl",stemmer.stem("apples",0,len("apples")-1))
        self.assertEquals("appl",stemmer.stem("appl",0,len("appl")-1))
        self.assertEquals("organ",stemmer.stem("organization",0,len("organization")-1))
        self.assertEquals("nba",stemmer.stem("nba",0,len("nba")-1))
        self.assertEquals("yao m",stemmer.stem("yao ming",0,len("yao ming")-1))
        
    def testError(self):
        stemmer=PorterStemmer()
        self.assertEquals("",stemmer.stem("",0,len("")-1))