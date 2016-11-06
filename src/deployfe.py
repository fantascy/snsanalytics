'''
Place for deployment data
'''

APP = 'fe'
APP_PATH = 'fe'

DOMAIN_MAP = {
    'localhost':'killersocialapps.com:8080',
    'prehistoricufo':'prehistoricufo.appspot.com',
    'findshowtime':'findshowtime.appspot.com',
    'twittergiants':'twittergiants.appspot.com',
    'hallowean':'hallowean.appspot.com',
    'sfbayunited':'sfbayunited.appspot.com',
    'quicksocial':'quicksocial.appspot.com',
    'actualizeryourself':'actualizeryourself.appspot.com',
    'b2realworld':'b2realworld.appspot.com',
    'bigdataworld':'bigdataworld.appspot.com',
    'postsocialworld':'postsocialworld.appspot.com',
             }

REDIRECT_MAP = {
               }

APPSPOT_DOMAIN_MAP = {
    'localhost':'killersocialapps.com:8080',
    'prehistoricufo':'prehistoricufo.appspot.com',
    'findshowtime':'findshowtime.appspot.com',
    'twittergiants':'twittergiants.appspot.com',
    'hallowean':'hallowean.appspot.com',
    'sfbayunited':'sfbayunited.appspot.com',
    'quicksocial':'quicksocial.appspot.com',
    'actualizeryourself':'actualizeryourself.appspot.com',
    'b2realworld':'b2realworld.appspot.com',
    'bigdataworld':'bigdataworld.appspot.com',
    'postsocialworld':'postsocialworld.appspot.com',
              }

SHORT_DOMAIN_MAP = {
    'localhost':'killersocialapps.com:8080',
    'prehistoricufo':'prehistoricufo.appspot.com',
    'findshowtime':'findshowtime.appspot.com',
    'twittergiants':'twittergiants.appspot.com',
    'hallowean':'hallowean.appspot.com',
    'sfbayunited':'sfbayunited.appspot.com',
    'quicksocial':'quicksocial.appspot.com',
    'actualizeryourself':'actualizeryourself.appspot.com',
    'b2realworld':'b2realworld.appspot.com',
    'bigdataworld':'bigdataworld.appspot.com',
    'postsocialworld':'postsocialworld.appspot.com',
                    }

API_DOMAIN_MAP = {
    'localhost':'killersocialapps.com:8080',
    'prehistoricufo':'prehistoricufo.appspot.com',
    'findshowtime':'findshowtime.appspot.com',
    'twittergiants':'twittergiants.appspot.com',
    'hallowean':'hallowean.appspot.com',
    'sfbayunited':'sfbayunited.appspot.com',
    'quicksocial':'quicksocial.appspot.com',
    'actualizeryourself':'actualizeryourself.appspot.com',
    'b2realworld':'b2realworld.appspot.com',
    'bigdataworld':'bigdataworld.appspot.com',
    'postsocialworld':'postsocialworld.appspot.com',
                 }

APP_NAME_MAP = {
    'localhost':'Localhost',
    'prehistoricufo':'Pre-historic UFO',
    'findshowtime':'Find Show Time',
    'twittergiants':'Twitter Giants',
    'hallowean':'Hallowean',
    'sfbayunited':'SF Bay United',
    'quicksocial':'Quick Social',
    'actualizeryourself':'Actualize Yourself',
    'b2realworld':'Back to Real World',
    'bigdataworld':'Big Data World',
    'postsocialworld':'Post Social World',
                 }
APP_DISPLAY_NAME = APP_NAME_MAP

FACEBOOK_ID_MAP = {
    'localhost':'196711817013363',
    'prehistoricufo':'NOT-Available',
    'findshowtime':'NOT-Available',
    'twittergiants':'NOT-Available',
    'hallowean':'NOT-Available',
    'sfbayunited':'NOT-Available',
    'quicksocial':'NOT-Available',
    'actualizeryourself':'NOT-Available',
    'b2realworld':'NOT-Available',
    'bigdataworld':'NOT-Available',
    'postsocialworld':'NOT-Available',
                   }

FACEBOOK_API_KEY_MAP = {
    'localhost':'a5b76d1500bda9a0c923ddc4d4d27932',
    'prehistoricufo':'NOT-Available',
    'findshowtime':'NOT-Available',
    'twittergiants':'NOT-Available',
    'hallowean':'NOT-Available',
    'sfbayunited':'NOT-Available',
    'quicksocial':'NOT-Available',
    'actualizeryourself':'NOT-Available',
    'b2realworld':'NOT-Available',
    'bigdataworld':'NOT-Available',
    'postsocialworld':'NOT-Available',
                   }

FACEBOOK_SECRET_MAP = {
    'localhost':'928f78cc7f1b91a2f482aa439442fd49',                
    'prehistoricufo':'NOT-Available',
    'findshowtime':'NOT-Available',
    'twittergiants':'NOT-Available',
    'hallowean':'NOT-Available',
    'sfbayunited':'NOT-Available',
    'quicksocial':'NOT-Available',
    'actualizeryourself':'NOT-Available',
    'b2realworld':'NOT-Available',
    'bigdataworld':'NOT-Available',
    'postsocialworld':'NOT-Available',
                       }

""" If callback_url is none, use the standard default callback url for each app. """
TWITTER_OAUTH_MAP={
    'localhost':{ 'consumer_key': 'mTYbrflfxSaQg4grd0F2A',
              'consumer_secret': 'T3PZ4D1q3hudTnjhqkSQYwHUtKTcYrMSFNPR4W9Lk',
            },
    'prehistoricufo':{ 'consumer_key': 'StAKK2up7LSkukhBnFhEUQ',
              'consumer_secret': 'C95yO9rzWcx7KLg0xBexYhcqxmvl8DwmwBC7rP8nQ8',
            },
    'findshowtime':{ 'consumer_key': 'vStZK2p3UxpAA04Ao2KAQ',
              'consumer_secret': 'KL3NX3tcB7bsQNb1tl3abXRxXPUQr4BKqhL7MFKGopQ',
            },
    'twittergiants':{ 'consumer_key': 'VJ0GOsHeC9Sg2P5nFJODA',
              'consumer_secret': 'Ap1s4d8xivjU8qeskly7qRISEIkzRoMuF7UpsBgI4C4',
            },
    'hallowean':{ 'consumer_key': 'AseYTQAvCl0JJHTAXUjQjA',
              'consumer_secret': '4fRBI8Nm74pFGyB8cCn4nRgzdNa4eq2fgaUrElZQo',
            },
    'sfbayunited':{ 'consumer_key': '71o4FyFXHgO5HKZ60KWmPg',
              'consumer_secret': 'hfzBLlpvrxsP9RWsUZK7O1nELO0hwnyYmClXoKtOG8',
            },
    'quicksocial':{ 'consumer_key': 'oZPZapNH80Thw5RkYYxksYxnk',
              'consumer_secret': 'c3ZWCnv5JXKVxDVzPJhfYuQQ6qaivzopXgkCLHRVqOGsVenRqJ',
            },
    'actualizeryourself':{ 'consumer_key': 'WeOUcXmemIbp3RM9w0Wfrw',
              'consumer_secret': 'REsiLp5yAYJNivWhcSSXlRN4oP97ilTmz0DU6uUMA',
            },
    'b2realworld':{ 'consumer_key': 'yLGhOYq3eBro6Gg0sARpvHfgi',
              'consumer_secret': 'SImKoGLRdPdZxqPO9RNtHeaROHOgfxnYP8tcvPUKnXHflv23B9',
            },
    'bigdataworld':{ 'consumer_key': 'fqrrZ6yjibviapAhu6Ltg',
              'consumer_secret': 'AmWMw8oIOdrv1Hw6Ykjbwu8d0SqdbdAtk5nAwik',
            },
    'postsocialworld':{ 'consumer_key': 'Gbm8pmjyJhOUNq6f0ge5xg',
              'consumer_secret': 'eNJ2ZtObNHJJoYc83BZQZZjeGLQ1X03OIkqOidQTk',
            },
    }


GA_TRACKING_CODE_MAP = {
    'localhost':'UA-8816477-21',
    'prehistoricufo':'NOT-Available',
    'findshowtime':'NOT-Available',
    'twittergiants':'NOT-Available',
    'hallowean':'NOT-Available',
    'sfbayunited':'NOT-Available',
    'quicksocial':'NOT-Available',
    'actualizeryourself':'NOT-Available',
    'b2realworld':'NOT-Available',
    'bigdataworld':'NOT-Available',
    'postsocialworld':'NOT-Available',
              }


SURL_GA_TRACKING_CODE_MAP = {
    'localhost':'UA-8816477-22',
    'prehistoricufo':'NOT-Available',
    'findshowtime':'NOT-Available',
    'twittergiants':'NOT-Available',
    'hallowean':'NOT-Available',
    'sfbayunited':'NOT-Available',
    'quicksocial':'NOT-Available',
    'actualizeryourself':'NOT-Available',
    'b2realworld':'NOT-Available',
    'bigdataworld':'NOT-Available',
    'postsocialworld':'NOT-Available',
              }


SHOW_ADS_FOOTER = {
        'localhost':False,
        'prehistoricufo':False,
        'findshowtime':False,
        'twittergiants':False,
        'hallowean':False,
        'sfbayunited':False,
        'quicksocial':False,
        'actualizeryourself':False,
        'b2realworld':False,
        'bigdataworld':False,
        'postsocialworld':False,
    }


DM_AVAILABLE = {
        'localhost':True,
        'prehistoricufo':False,
        'findshowtime':False,
        'twittergiants':False,
        'hallowean':False,
        'sfbayunited':False,
        'quicksocial':False,
        'actualizeryourself':False,
        'b2realworld':False,
        'bigdataworld':False,
        'postsocialworld':False,
    }


FOLLOW_AVAILABLE = {
        'localhost':True,
        'prehistoricufo':True,
        'findshowtime':True,
        'twittergiants':True,
        'hallowean':True,
        'sfbayunited':True,
        'quicksocial':True,
        'actualizeryourself':True,
        'b2realworld':True,
        'bigdataworld':True,
        'postsocialworld':True,
    }


LIKE_CAMPAIGN_AVAILABLE = {
        'localhost':True,
        'prehistoricufo':False,
        'findshowtime':False,
        'twittergiants':False,
        'hallowean':False,
        'sfbayunited':False,
        'quicksocial':False,
        'actualizeryourself':False,
        'b2realworld':False,
        'bigdataworld':False,
        'postsocialworld':False,
    }

CMP_MAP = {}