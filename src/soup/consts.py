import datetime 

from common.consts import *
from common.utils.string import name_2_key
from common.utils import datetimeparser
from sns.url.models import GlobalUrlCounter

SITE_MAP_HEADER = '<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
SITE_MAP_INDEX_HEADER = '<?xml version="1.0" encoding="UTF-8"?><sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'

RANK_TYPE_HOT = 0
RANK_TYPE_NEW = 1
RANK_TYPE_TOP = 2
RANK_TYPES = (RANK_TYPE_HOT, RANK_TYPE_NEW, RANK_TYPE_TOP)
RANK_TYPE_MAP = {
    RANK_TYPE_HOT: "hot",
    RANK_TYPE_NEW: "new",
    RANK_TYPE_TOP: "top",
    }

TIME_RANGE_HOUR = 'hour'
TIME_RANGE_DAY = 'day'
TIME_RANGE_WEEK = 'week'
TIME_RANGE_MONTH = 'month'
TIME_RANGE_YEAR = 'year'
TIME_RANGES = (
    TIME_RANGE_HOUR,
    TIME_RANGE_DAY,
    TIME_RANGE_WEEK,
    TIME_RANGE_MONTH,
    TIME_RANGE_YEAR,
    )
TIME_RANGE_CHOICES = [
    (TIME_RANGE_HOUR, '1 hour'),
    (TIME_RANGE_DAY, '1 day'),
    (TIME_RANGE_WEEK, '1 week'),
    (TIME_RANGE_MONTH, "1 month"),
    (TIME_RANGE_YEAR, "1 year"),
    ] 

MEDIA_TYPE_ALL_STR      = 'all'
MEDIA_TYPE_NORMAL_STR   = 'normal'
MEDIA_TYPE_VIDEO_STR    = 'video'
MEDIA_TYPE_IMAGE_STR      = 'image'
MEDIA_TYPE_STRS = (MEDIA_TYPE_ALL_STR, MEDIA_TYPE_NORMAL_STR, MEDIA_TYPE_VIDEO_STR, MEDIA_TYPE_IMAGE_STR,)
MEDIA_TYPE_CHOICES = [(MEDIA_TYPE_ALL_STR,'All'),
                      (MEDIA_TYPE_VIDEO_STR,'Video Only'),
                     ]
MEDIA_TYPE_DISPLAY_NAME = { MEDIA_TYPE_ALL_STR: 'Soups',
                            MEDIA_TYPE_NORMAL_STR: 'News Soups',
                            MEDIA_TYPE_VIDEO_STR: 'Video Soups',
                            MEDIA_TYPE_IMAGE_STR: 'Image Soups',
                        }
def int_media_type(mediaType):
    if mediaType is None :
        return None
    if type(mediaType)==int :
        return mediaType
    return list(MEDIA_TYPE_STRS).index(mediaType)-1 

TIME_LENGTHS = {TIME_RANGES[0]:datetime.timedelta(seconds=3600),
                TIME_RANGES[1]:datetime.timedelta(days=1),
                TIME_RANGES[2]:datetime.timedelta(days=7),
                TIME_RANGES[3]:datetime.timedelta(days=30),
                TIME_RANGES[4]:datetime.timedelta(days=365),
                }

TIME_FILTERS = {TIME_RANGES[0]:'lastUpdateHour',
                TIME_RANGES[1]:'lastUpdateDay',
                TIME_RANGES[2]:'lastUpdateWeek',
                TIME_RANGES[3]:'lastUpdateMonth',
                TIME_RANGES[4]:'lastUpdateYear',
                }

TIME_RATINGS = {TIME_RANGES[0]:'c60m',
                TIME_RANGES[1]:'c24h',
                TIME_RANGES[2]:'c7d',
                TIME_RANGES[3]:'c30d',
                TIME_RANGES[4]:'c365d',
                }

TIME_PARSERS = {TIME_RANGES[0]:datetimeparser.intHour,
                TIME_RANGES[1]:datetimeparser.intDay,
                TIME_RANGES[2]:datetimeparser.intWeek,
                TIME_RANGES[3]:datetimeparser.intMonth,
                TIME_RANGES[4]:datetimeparser.intYear,
                }

TIME_SYNCS =   {TIME_RANGES[0]:GlobalUrlCounter.setHour,
                TIME_RANGES[1]:GlobalUrlCounter.setDay,
                TIME_RANGES[2]:GlobalUrlCounter.setWeek,
                TIME_RANGES[3]:GlobalUrlCounter.setMonth,
                TIME_RANGES[4]:GlobalUrlCounter.setYear,
                }

TIME_CACHE = {  TIME_RANGES[0]:(600,600),
                TIME_RANGES[1]:(3600,600),
                TIME_RANGES[2]:(3600,3600),
                TIME_RANGES[3]:(86400,86400),
                TIME_RANGES[4]:(86400,86400),
              }

USER_TYPE_TWITTER = 't'  
USER_TYPE_FACEBOOK = 'f'  
USER_TYPE_FACEBOOK_PAGE = 'fp'  
USER_TYPES = (USER_TYPE_FACEBOOK, USER_TYPE_TWITTER,USER_TYPE_FACEBOOK_PAGE)


NOTICE_TYPE_SHARE_ARTICLE = "share_article"
NOTICE_TYPE_SHARE_ARTICLE_DUP = "share_article_dup"
NOTICE_TYPE_TWITTER_CONNECT_DUP = "twitter_connect_dup"
NOTICE_USER_NOT_LOGIN = 'user_not_login'
NOTICE_UNKNOWN_ERROR = 'unknown_error'
NOTICE_GAE_MAINTENANCE = 'gae_maintenance'
NOTICE_MSG_MAP = {
  NOTICE_TYPE_SHARE_ARTICLE : "Waha. You've shared the soup. Wanna put some comments?",
  NOTICE_TYPE_SHARE_ARTICLE_DUP : "Oops. Somebody already shared the soup. Wanna put some comments?",
  NOTICE_TYPE_TWITTER_CONNECT_DUP : "Oops. The Twitter account is already connected with another user.",
  NOTICE_USER_NOT_LOGIN : "Oops. You have not signed in.",
  NOTICE_GAE_MAINTENANCE : 'Sorry! We are on scheduled maintenance. It should be finished within one hour.',
  NOTICE_UNKNOWN_ERROR : "Sorry. We just encountered some unexpected error.",
  }

ALL_NEW_SOUP_IMAGE = "http://media.allnewsoup.com/images/logo/soup_logo_256x256.png"

MAIN_MENU = ['Business','Politics','Entertainment','Gaming','Lifestyle','Health','Sports','Tech','Science','Arts','Books','Hobby','World','US'] 
MAIN_MENU_2_TOPIC_NAME_MAP = {
    'Tech': 'Technology',
    'World': 'International',                
    'Hobby': 'Hobbies',
    }
MAIN_MENU_2_TOPIC_KEY_MAP = [{'name':'All', 'keyNameStrip':'frontpage'}]
for name in MAIN_MENU:
    topicName = MAIN_MENU_2_TOPIC_NAME_MAP.get(name, name)
    MAIN_MENU_2_TOPIC_KEY_MAP.append({'name':name, 'keyNameStrip':name_2_key(topicName)})
MAIN_MENU_TOPIC_CHOICES = [(topic['keyNameStrip'], topic['name']) for topic in MAIN_MENU_2_TOPIC_KEY_MAP]
MAIN_TOPIC_NAMES = [MAIN_MENU_2_TOPIC_NAME_MAP.get(name, name) for name in MAIN_MENU]

LIST5 = [1,2,3,4,5]
ARTICLE_NUMBER_LOWER_LIMIT = 10

INVITE_FRIENDS_KEY = 'invite_friends:'
SOUP_FRIENDS_KEY = 'soup_friends:'

