import unittest

from common.utils import url as url_util
from common.content.trove import consts as trove_const
from common.content.trove import api as trove_api
from common.content.trove import urlnormalizer as trove_curl_normalizer


HOSTED_URLS = [
    "http://bleacherreport.com/articles/2387047-best-draft-day-contingency-plans-for-",
    "http://rmb.reuters.com/rmd/rss/item/tag:reuters.com,0000:newsml_L3N0WR03K:1378602566",
               ]

VISOR_PHONE_UNFRIENDLY_URLS = [
    "http://www.huffingtonpost.com/2015/02/23/white-house-fiduciary-rul_n_6732186.html",
                 ]

VISOR_IPHONE_UNFRIENDLY_URLS = [
    "http://latino.foxnews.com/latino/entertainment/2015/01/31/new-mana-album-with-single-featuring-shakira-due-out-this-year/",
    "http://experience.usatoday.com/food-and-wine/story/meet-the-chef/2015/02/19/chef-jose-andres-empire/23614511/",
                 ]

VISOR_FRIENDLY_URLS = [
    "http://www.foxnews.com/us/2015/02/23/tanker-truck-with-k-gallons-fuel-crashes-catches-fire-in-new-jersey/",
    "http://www.mercurynews.com/business/ci_27509186/cupertino-seeks-reap-benefits-from-apple-spaceship-campus",
    "http://techcrunch.com/2015/04/30/tesla-powerwall-home-battery/",
                 ]

VISOR_UNKNOWN_DOMAIN_URLS = [
    "http://tech.163.com/14/1117/23/AB9OMO4G000915BF.html",
                 ]

UNHOSTED_URLS = []
UNHOSTED_URLS.extend(VISOR_PHONE_UNFRIENDLY_URLS)
UNHOSTED_URLS.extend(VISOR_IPHONE_UNFRIENDLY_URLS)
UNHOSTED_URLS.extend(VISOR_FRIENDLY_URLS)

UNINGESTED_URLS = [
    "http://tech.163.com/14/1117/23/AB9OMO4G000915BF.html",
    "http://variety.com/2015/biz/news/brazil-preps-for-mass-sxsw-attendance-1201449605/",
    "http://www.independent.ie/entertainment/music/music-news/u2-tour-band-announces-dates-for-innocence-and-experience-tour-30795682.html",
                 ]

BLACKLISTED_URLS = [
    "http://espn.go.com/espn/story/_/page/instantawesome-leagueoflegends-141201/league-legends-championships-watched-more-people-average-nba-finals-world-series-games",
    "http://news.yahoo.com/missouri-governor-activates-national-guard-201522300.html",
    "http://www.forbes.com/sites/samsungbusiness/2015/01/29/turning-students-into-players-how-gamification-is-improving-education/",
    "http://www.si.com/nfl/2015/02/01/seattle-seahawks-marshawn-lynch-contract-extension-2015-super-bowl",
    "http://www.anrdoezrs.net/dummy",
                    ]

URL_SHORTENER_MAP = {
    "http://trove.com/me/content/jW1No?utm_campaign=hosted&utm_medium=twitter&utm_source=sns&chid=127904": "http://trov.es/1zxsW5v",
    "http://trove.com/me/content/jW1No?chid=127904&utm_campaign=hosted&utm_medium=twitter&utm_source=sns": "http://trov.es/1zxsW5v",
    "http://trove.com/me/content/qQ1XI?utm_campaign=unhosted&utm_medium=twitter&utm_source=sns": "http://trov.es/1KkDs1e",
    "http://trove.com/me/content/qQ1XI": None,
    "http://www.rollingstone.com/music/news/taylor-swift-abruptly-pulls-entire-catalog-from-spotify-20141103": None,
                     }

SEARCH_KEYWORDS_MAP = {
    'Washington, D.C.': "Washington%2CDC",
    'St  . Louis, MO ': "%22St+Louis%2CMO%22",
    'Chicago,   IL': "Chicago%2CIL",
    ' Aviation | Aero Space': "Aviation+%22Aero+Space%22",
    ' Soul | R&B': "Soul+R%26B",
    'Apple': "Apple",
    'Computer Gaming': "%22Computer+Gaming%22",
                       }

URL_NORMALIZATION_MAP = {
    "http://www.bbc.com/news/uk-england-south-yorkshire-31812280": 
    "http://www.bbc.co.uk/news/uk-england-south-yorkshire-31812280",
    "http://www.mercurynews.com/business/ci_27509186/cupertino-seeks-reap-benefits-from-apple-spaceship-campus":
    "http://www.mercurynews.com/business/ci_27509186/cupertino-seeks-reap-benefits-from-apple-spaceship-campus?source=rss",
    }

IMAGE_URL_MAP = {
    "http://www.people.com/article/bachelorette-kaitlyn-bristowe-blog-episode-3": "http://img2-1.timeinc.net/people/i/2015/news/150608/bachelorette-01-800.jpg",
    }

UNHOSTED_CURATOR_URL_MAP = {
    "http://boingboing.net/2015/06/21/the-girl-with-the-parrot-on-he.html": (190650, 'terryirving') ,
    }


class TestTrove(unittest.TestCase):
    def test_search(self):
        results = trove_api.search_by_unnormalized_keywords('Taylor Swift', limit=20)
        self.assertTrue(len(results)==20)
        for i in range(19):
            self.assertGreater(results[i], results[i+1])
            self.assertLess(results[i+1], results[i])
            self.assertEqual(results[i], results[i])
        filtered_results = trove_api.filter_search_results(results, contcutoffhours=1)
        self.assertTrue(len(filtered_results)<10)
        results = trove_api.search_and_filter('Columbia,SC', limit=20)
        self.assertTrue(len(results)<=20)
        filtered_results = trove_api.filter_search_results(results, contcutoffhours=5)
        self.assertTrue(len(filtered_results)<10)
        self.assertTrue(len(trove_api.search_by_unnormalized_keywords('LeBron James', limit=5))==5)
        self.assertTrue(len(trove_api.search_by_unnormalized_keywords('Dummydummynonexsitent', limit=20))==0)
        
    def test_search_entry_conversion(self):
        original = trove_api.search_by_unnormalized_keywords('Marshawn Lynch', limit=10)
        self.assertEqual(len(original), 10)
        text = trove_api.TroveItem.items_to_text(original)
        converted = trove_api.TroveItem.text_to_items(text)
        self.assertEqual(len(original), len(converted))
        for i in range(10):
            self.assertEqual(original[i], converted[i])

    def test_search_entry_merge(self):
        results = trove_api.search_by_unnormalized_keywords('Politics', limit=20)
        self.assertTrue(len(results)==20)
        list1 = results[5:15]
        list2 = results[10:20]
        merged = trove_api.TroveItem.merge_entries(list1, list2)
        self.assertEqual(len(merged), 15)
        hosted_items = trove_api.filter_search_results(merged, usage_rights_set=set([trove_const.USAGE_RIGHTS_FULL,]))
        unhosted_items = trove_api.filter_search_results(merged, usage_rights_set=set([trove_const.USAGE_RIGHTS_SNIPPET,]))
        if hosted_items and unhosted_items:
            self.assertGreater(hosted_items[0], unhosted_items[0])
            self.assertLess(unhosted_items[-1], hosted_items[-1])

    def test_search_keywords_mapping(self):
        for k, v in SEARCH_KEYWORDS_MAP.items():
            self.assertEqual(v, trove_api.normalize_search_keywords(k))
        
    def test_image(self):
        for url, full_image in IMAGE_URL_MAP.items():
            item = trove_api.TroveItem.get_by_url(url)
            self.assertEquals(item.full_image, full_image)
        
    def test_hosted(self):
        for url in HOSTED_URLS:
            trove_item = trove_api.TroveItem.get_by_url(url)
            self.assertTrue(trove_item is not None)
            self.assertTrue(trove_item.is_hosted)
            trove_url = trove_item.trove_url
            self.assertEquals(url_util.root_domain(trove_url), 'trove.com')
            trove_url = trove_api.get_trove_url_with_utm(url)
            self.assertEquals(url_util.root_domain(trove_url), 'trove.com')
            self.assertTrue(trove_api.is_trove_url_hosted(trove_url))
            params = url_util.get_params(trove_url)
            self.assertTrue(self.has_correct_utm_params(params, hosted=True))
                    
    def test_unhosted(self):
        for url in UNHOSTED_URLS:
            trove_item = trove_api.TroveItem.get_by_url(url)
            self.assertTrue(trove_item is not None)
            self.assertFalse(trove_item.is_hosted)
            trove_url = trove_item.trove_url
            self.assertEquals(url_util.root_domain(trove_url), 'trove.com')
            trove_url = trove_api.get_trove_url_with_utm(url)
            self.assertEquals(url_util.root_domain(trove_url), 'trove.com')
            self.assertFalse(trove_api.is_trove_url_hosted(trove_url))
            params = url_util.get_params(trove_url)
            self.assertTrue(self.has_correct_utm_params(params, hosted=False))

    def test_curator_info(self):
        for url, curator_info in UNHOSTED_CURATOR_URL_MAP.items():
            trove_item = trove_api.TroveItem.get_by_url(url)
            self.assertTrue(trove_item is not None)
            self.assertEqual(curator_info[0], trove_item.curator_id)
            self.assertEqual(curator_info[1], trove_item.curator_handle)

    def test_uningested(self):
        for url in UNINGESTED_URLS:
            trove_item = trove_api.TroveItem.get_by_url(url)
            self.assertFalse(trove_item is not None)

    def test_blacklisted(self):
        for url in BLACKLISTED_URLS:
            self.assertTrue(trove_api.is_url_in_unhosted_blacklist(url))
            trove_item = trove_api.TroveItem.get_by_url(url)
            self.assertFalse(trove_item is not None)
#         for url in UNHOSTED_URLS:
#             self.assertFalse(trove_api.is_url_in_unhosted_blacklist(url))
        for url in HOSTED_URLS:
            self.assertFalse(trove_api.is_url_in_unhosted_blacklist(url))

#     def test_visor_phone_unfriendly(self):
#         for url in VISOR_PHONE_UNFRIENDLY_URLS:
#             self.assertTrue(trove_api.is_url_in_collection(url, trove_const.VISOR_PHONE_UNFRIENDLY_BLACKSET))
#         for url in VISOR_FRIENDLY_URLS:
#             self.assertFalse(trove_api.is_url_in_collection(url, trove_const.VISOR_PHONE_UNFRIENDLY_BLACKSET))
# 
#     def test_visor_iphone_unfriendly(self):
#         for url in VISOR_IPHONE_UNFRIENDLY_URLS:
#             self.assertTrue(trove_api.is_url_in_collection(url, trove_const.VISOR_IPHONE_UNFRIENDLY_BLACKSET))
#         for url in VISOR_FRIENDLY_URLS:
#             self.assertFalse(trove_api.is_url_in_collection(url, trove_const.VISOR_IPHONE_UNFRIENDLY_BLACKSET))
# 
#     def test_visor_unknown_domains(self):
#         for url in VISOR_UNKNOWN_DOMAIN_URLS:
#             self.assertFalse(trove_api.is_url_in_collection(url, trove_const.VISOR_POSSIBLY_FRIENDLY_WHITESET))
#             self.assertFalse(trove_api.is_url_in_collection(url, trove_const.VISOR_UNFRIENDLY_BLACKSET))
# 
#     def test_visor_eligibility(self):
#         for url in BLACKLISTED_URLS:
#             self.assertFalse(trove_api.is_url_eligible_for_visor(url, is_iphone=True, is_phone=True))
#             self.assertFalse(trove_api.is_url_eligible_for_visor(url, is_iphone=False, is_phone=False))
#         for url in VISOR_IPHONE_UNFRIENDLY_URLS + VISOR_UNKNOWN_DOMAIN_URLS:
#             self.assertFalse(trove_api.is_url_eligible_for_visor(url, is_iphone=True, is_phone=True))
#             self.assertTrue(trove_api.is_url_eligible_for_visor(url, is_iphone=False, is_phone=True))
#             self.assertTrue(trove_api.is_url_eligible_for_visor(url, is_iphone=False, is_phone=False))
#         for url in VISOR_PHONE_UNFRIENDLY_URLS:
#             self.assertFalse(trove_api.is_url_eligible_for_visor(url, is_iphone=True, is_phone=True))
#             self.assertRaises(Exception, trove_api.is_url_eligible_for_visor(url, is_iphone=True, is_phone=False))
#             self.assertFalse(trove_api.is_url_eligible_for_visor(url, is_iphone=False, is_phone=True))
#             self.assertTrue(trove_api.is_url_eligible_for_visor(url, is_iphone=False, is_phone=False))
#         for url in VISOR_FRIENDLY_URLS:
#             self.assertTrue(trove_api.is_url_eligible_for_visor(url, is_iphone=True, is_phone=True))
#             self.assertRaises(Exception, trove_api.is_url_eligible_for_visor(url, is_iphone=True, is_phone=False))
#             self.assertTrue(trove_api.is_url_eligible_for_visor(url, is_iphone=False, is_phone=True))
#             self.assertTrue(trove_api.is_url_eligible_for_visor(url, is_iphone=False, is_phone=False))
#         
#     def test_visor_possibly_friendly_whitelist(self):
#         for url in VISOR_IPHONE_UNFRIENDLY_URLS + VISOR_PHONE_UNFRIENDLY_URLS + VISOR_FRIENDLY_URLS:
#             self.assertTrue(trove_api.is_url_in_visor_possibly_friendly_whitelist(url))
        
    def test_ingested_whitelist(self):
        for url in VISOR_IPHONE_UNFRIENDLY_URLS + VISOR_PHONE_UNFRIENDLY_URLS + VISOR_FRIENDLY_URLS + HOSTED_URLS:
            self.assertTrue(trove_api.is_url_in_ingested_whitelist(url))
        
#     def test_whitelist_blacklist(self):
#         mutual = trove_const.VISOR_POSSIBLY_FRIENDLY_WHITESET.intersection(trove_const.VISOR_UNFRIENDLY_BLACKSET)
#         self.assertTrue(len(mutual) == 0)
        
    def test_url_shortener(self):
        for url in URL_SHORTENER_MAP.keys():
            short_url = trove_api.get_trove_short_url(url)
            self.assertEqual(short_url, URL_SHORTENER_MAP.get(url))
            if short_url: self.assertNotEquals(short_url, trove_api.get_trove_short_url(url, add_timestamp=True))
    
    def test_url_normalization(self):
        for k, v in URL_NORMALIZATION_MAP.items():
            self.assertEqual(trove_curl_normalizer.normalize(k), v)
            
    def has_correct_utm_params(self, params, hosted=True):
        utm_campaign = trove_const.UTM_CAMPAIGN_HOSTED if hosted else trove_const.UTM_CAMPAIGN_UNHOSTED
        return params.has_key('utm_source') and params['utm_source'] == trove_const.UTM_SOURCE and \
            params.has_key('utm_medium') and params['utm_medium'] == trove_const.UTM_MEDIUM and \
            params.has_key('utm_campaign') and params['utm_campaign'] == utm_campaign
            

if __name__ == '__main__':
    unittest.main()
