
""" Give some random interval before processing another account. In seconds. """
YAHOO_LOGIN_TIME_INTERVAL = 5
YAHOO_PASSWD_CHANGE_TIME_INTERVAL = 5
TWITTER_LOGIN_TIME_INTERVAL = 5
TWITTER_PASSWD_CHANGE_TIME_INTERVAL = 5

SELENIUM_IMPLICITLY_WAIT = 10

""" Map model attributes to CSV column headers. """ 
ATTR_2_HEADER_MAP = {
    "num": "ID", 
    "name": "Yahoo Login", 
    "password": "Yahoo Password", 
    "oldPassword": "Yahoo Old Password", 
    "newPassword": "Yahoo New Password", 
    "passwordClue": "Yahoo Sec Q/A", 
    "state": "Yahoo State", 
    "lastLoginTime": "Yahoo LLT", 
    "lastPasswdChangeTime": "Yahoo LPCT", 
    "tHandle": "Twitter Handle", 
    "tPassword": "Twitter Password", 
    "tOldPassword": "Twitter Old Password", 
    "tNewPassword": "Twitter New Password", 
    "tState": "Twitter State", 
    "tLastLoginTime": "Twitter LLT", 
    "tLastPasswdChangeTime": "Twitter LPCT", 
    "isCmp": "Is CMP", 
                  }
HEADER_2_ATTR_MAP = dict([(v, k) for k, v in ATTR_2_HEADER_MAP.items()])

DEFAULT_ATTRS = [
    "num",
    "name", 
    "password", 
    "passwordClue", 
    "state", 
    "lastLoginTime", 
    "lastPasswdChangeTime", 
    "tHandle", 
    "tPassword",
    "tState", 
    "tLastLoginTime", 
    "tLastPasswdChangeTime", 
    "isCmp", 
    ]
DEFAULT_HEADERS = [ATTR_2_HEADER_MAP[attr] for attr in DEFAULT_ATTRS]
