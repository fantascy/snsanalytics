import unittest


BEST_SELLERS = [
    {
        "prodid": "0FL2521077H",
        "url": "http://www.jollychic.com/p/solid-short-sleeves-shift-t-shirt-mini-dress-g157203.html",
        "desc": "Solid Short Sleeves Shift T-shirt Mini Dress",
        "now": "$5.99",
        "was": "$9.99"
    },
    {
        "prodid": "0FF253060V3",
        "url": "http://www.jollychic.com/p/geometric-print-long-sleeve-o-neckline-women-pullover-sweater-g159247.html",
        "desc": "Geometric Print Long Sleeve O Neckline Women Pullover Sweater",
        "now": "$7.99",
        "was": "$16.99"
    },
    {
        "prodid": "0FE2520323L",
        "url": "http://www.jollychic.com/p/solid-long-sleeves-chiffon-turn-down-collar-shirt-g153531.html",
        "desc": "Solid Long Sleeves Chiffon Turn-Down Collar Shirt",
        "now": "$7.99",
        "was": "$15.99"
    },
]


class TestJolly(unittest.TestCase):
    def test_noop(self):
        self.assertTrue(True)
           

if __name__ == '__main__':
    unittest.main()
