# -*- coding: utf-8 -*-

import unittest

from common.utils import twitter as twitter_util


class TestTwitter(unittest.TestCase):
    def test_truncate_linked_tweet(self):
        original = "123456789012345678901234567890123456789012345678901234567890123456789012345678901234567890abcdefg http://www.snsanalytics.com/6z1Ey2"
        expected = "123456789012345678901234567890123456789012345678901234567890123456789012345678901234567... http://www.snsanalytics.com/6z1Ey2"
        actual = twitter_util.hack_tweet_with_media(original)
        self.assertTrue(len(actual) <= 140)
        self.assertEqual(actual, expected)

    
if __name__ == '__main__':
    unittest.main()
