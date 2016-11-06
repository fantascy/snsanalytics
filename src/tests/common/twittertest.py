import unittest
import datetime

from common.utils import twitter as twitter_util


class TestTwitter(unittest.TestCase):

    def test_created_at(self):
        tstr = "Mon Feb 26 18:05:55 +0000 2007"
        fmt = "%a %b %d %H:%M:%S %Y"
        dt = twitter_util.t_strptime(tstr)
        self.assertEqual(datetime.datetime.strftime(dt, fmt), "Mon Feb 26 18:05:55 2007")
        

if __name__ == '__main__':
    unittest.main()
