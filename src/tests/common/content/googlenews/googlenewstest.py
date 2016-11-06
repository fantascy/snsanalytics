import unittest

from common.content.googlenews import api as googlenews_api


SEARCH_KEYWORDS_MAP = {
    "Apple": "Apple",
    "Washington, D.C.": '"Washington, D.C."',
    "Lost (TV Series)": 'Lost "TV Series"',
    "Arizona Wildcats (Football)": '"Arizona Wildcats" Football',
                       }


class TestGoogleNews(unittest.TestCase):
    def test_search_keywords(self):
        for topic_name, keywords in SEARCH_KEYWORDS_MAP.items():
            self.assertEqual(keywords, googlenews_api.SearchKeywordsHandler(topic_name).keywords)
        self.assertEqual("Custom", googlenews_api.SearchKeywordsHandler("Taylor Swift", custom_keywords="Custom").keywords)
        self.assertRaises(Exception, googlenews_api.SearchKeywordsHandler, "Apple (Watch) (TV)")

if __name__ == '__main__':
    unittest.main()
