import urllib
import json
import unittest

from sns.deal import consts as deal_const
from sns.deal.utils import DealUrlHandler, DealSurfUrlHandler


class DealTest(unittest.TestCase):
    def testGrouponDealApi(self):
        url = "https://api.groupon.com/v2/deals.json?division_id=athens-ga&client_id="+ deal_const.GROUPON_CLIENT_ID
        strData = urllib.urlopen(url).read()
        dictData = json.loads(strData)
        self.assertTrue(dictData.has_key('deals'))

    def testGrouponUrl(self):
        input1 = "http://www.groupon.com/deals/epione"
        output = "http://www.anrdoezrs.net/click-5517529-10804307?url=http%3A%2F%2Fwww.groupon.com%2Fdeals%2Fepione"
        self.assertEqual(output, DealUrlHandler(deal_const.DEAL_SOURCE_GROUPON).handle(input1))
    
    def testCj(self):
        self.testGrouponUrl()

    def testPlumDistrict(self):
        input1 = "http://gan.doubleclick.net/gan_click?lid=41000000032568685&pubid=21000000000291686&mid=4ed25258bda18368601625&redirect=http%3A%2F%2Fwww.plumdistrict.com%2Fmoms%2Fdiscount%2Feverywhere%2Fhome-and-garden-deals%2Fdiscount-mags-plum-steal-10-for-issues-of-better-homes-gardens-ladies-home-journa-ACjqDJ%3Fsub%3Dtrue"
        output1 = "http://www.plumdistrict.com/moms/discount/everywhere/home-and-garden-deals/discount-mags-plum-steal-10-for-issues-of-better-homes-gardens-ladies-home-journa-ACjqDJ?sub=true"
        self.assertEqual(output1, DealSurfUrlHandler(deal_const.DEAL_SOURCE_PLUMDISTRICT).handle(input1))

    def testTipprAffUrl(self):
        url1 = "https://tippr.com/offer/austin-zoo-15-for-30" 
        url2 = "https://tippr.com/offer/austin-zoo-15-for-30/?p1=v1"
        url3 = "http://jump.tippr.com/aff_c?offer_id=2&aff_id=xyz&params=%2526offer%253Daustin-zoo-15-for-30"
        affUrl = "http://jump.tippr.com/aff_c?offer_id=2&aff_id=1309&params=%2526offer%253Daustin-zoo-15-for-30"
        self.assertEqual(affUrl, DealSurfUrlHandler(deal_const.DEAL_SOURCE_TIPPR).handle(url1))
        self.assertEqual(affUrl, DealSurfUrlHandler(deal_const.DEAL_SOURCE_TIPPR).handle(url2))
        self.assertEqual(affUrl, DealSurfUrlHandler(deal_const.DEAL_SOURCE_TIPPR).handle(url3))


if __name__ == "__main__":
    unittest.main()
