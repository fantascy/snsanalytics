import unittest

from sns.usr import consts as user_const


OLD_NEW_USER_EMAIL_MAP = {
    'qa07.sa@gmail.com': 'cohort+0000@snsanalytics.com',
    'snsContent.0@gmail.com': 'cohort+0001@snsanalytics.com',
    'snsContent.1@gmail.com': 'cohort+0002@snsanalytics.com',
    'snsContent.10@gmail.com': 'cohort+0003@snsanalytics.com',
    'zhangwuchang@gmail.com': 'cohort+0302@snsanalytics.com',
                              }

class UserTest(unittest.TestCase):
    def test_old_new_user_email_mapping(self):
        for old_mail, new_mail in OLD_NEW_USER_EMAIL_MAP.items():
            self.assertEqual(user_const.OLD_USER_EMAIL_MAP.get(old_mail, None), new_mail)
        
        
if __name__ == "__main__":
    unittest.main()

