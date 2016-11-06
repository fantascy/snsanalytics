SETTING_MODE_DEBUG = 'DEBUG'
SETTING_MODE_BETA = 'BETA'
SETTING_MODE_PRODUCTION = 'PRODUCTION'
SETTING_MODES = (SETTING_MODE_DEBUG, 
                 SETTING_MODE_BETA, 
                 SETTING_MODE_PRODUCTION,
                 )

"""
Important! These parameters need to be manually checked, every time when deploying to production.
"""
SETTING_MODE = SETTING_MODE_PRODUCTION
MEDIA_VERSION = 330

"""
If SETTING_MODE is not SETTING_MODE_DEBUG, all DEBUG_XXX settings should be ignored. If not, there is a bug.
"""
DEBUG_DJANGO_EXCEPTION_DUMP_ON = True
DEBUG_SKIP_REAL_POST = False
DEBUG_SKIP_TIMEOUT = True

TROVE_EXPIRE_TIME_UTC = "2015-12-02 08:00:00"

EXTRA_FEATURES = False

MARK_IS_BACKEND_ON_DEV = True 

LOCALHOST_IP_IS_CN = True

REQUIRE_GOOGLE_LOGIN = False

CAKE_TOOLBAR_ENABLED = False

COUNT_ADMIN_USER_CLICKS = False

import logging
LOGGING_LEVEL = logging.DEBUG if SETTING_MODE == SETTING_MODE_DEBUG else logging.INFO
logging.getLogger().setLevel(LOGGING_LEVEL)

