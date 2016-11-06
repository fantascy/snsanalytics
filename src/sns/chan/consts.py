""" All constants for channel package go here. """

DEFAULT_TWITTER_AVATAR_URL = "http://s.twimg.com/images/default_profile_normal.png"
DEFAULT_FACEBOOK_AVATAR_URL = "http://static.ak.fbcdn.net/rsrc.php/z5HB7/hash/ecyu2wwn.gif"

TWITTER_CALLBACK_TWEET = "just started using SNS Analytics - your social media mgmt center. http://sns.mx #SNSanalytics thumbs up!"
FACEBOOK_CALLBACK_TWEET = "just started using SNS Analytics - your social media mgmt center, enabling effective personal and business online social. A best tool to feed RSS to Facebook and Twitter. http://sns.mx thumbs up!"

CHANNEL_STATE_NORMAL = 0
CHANNEL_STATE_SUSPENDED = 1
CHANNEL_STATES = (CHANNEL_STATE_NORMAL, CHANNEL_STATE_SUSPENDED)

CHANNEL_TYPE_TWITTER = 0
CHANNEL_TYPE_FACEBOOK_ACCOUNT = 1
CHANNEL_TYPE_FACEBOOK_PAGE = 2
CHANNEL_TYPE_FACEBOOK_APP = 3