import unittest
import datetime

from common.utils import datetimeparser


class TestDateTimeParser(unittest.TestCase):
    def test_int_day(self):
        i = datetimeparser.intDay(datetime.datetime.now())
        self.assertEqual(i, datetimeparser.intDay(datetimeparser.int_day_2_datetime(i)))

    def test_decrement_int_month(self):
        self.assertEqual(200902, datetimeparser.decrement_int_month(200903))
    
    def test_date_datetime_conversion(self):
        dt = datetime.datetime.now()
        d = datetimeparser.truncate_2_day(dt)
        self.assertEqual(d, datetimeparser.truncate_2_day(datetimeparser.date_2_datetime(d)))

    def test_week_of_month(self):
        d = datetime.date(2015, 4, 1)
        first_monday = datetimeparser.first_monday_of_month(d)
        self.assertEqual(first_monday, datetime.date(2015, 4, 6))
        self.assertFalse(datetimeparser.is_in_first_week_of_month(datetime.date(2015, 4, 5)))
        self.assertTrue(datetimeparser.is_in_first_week_of_month(datetime.date(2015, 4, 6)))
        self.assertTrue(datetimeparser.is_in_first_week_of_month(datetime.date(2015, 4, 12)))
        self.assertTrue(datetimeparser.is_in_second_week_of_month(datetime.date(2015, 4, 13)))
        self.assertTrue(datetimeparser.is_in_second_week_of_month(datetime.date(2015, 4, 19)))
        self.assertFalse(datetimeparser.is_in_second_week_of_month(datetime.date(2015, 4, 20)))

    
if __name__ == '__main__':
    unittest.main()

