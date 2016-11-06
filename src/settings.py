# -*- coding: utf-8 -*-
from common.appenginepatch.ragendja.settings_pre import *

import conf
DEBUG = conf.SETTING_MODE==conf.SETTING_MODE_DEBUG

    
# Increase this when you update your media on the production site, so users
# don't have to refresh their cache. By setting this your MEDIA_URL
# automatically becomes /media/MEDIA_VERSION/
MEDIA_VERSION = conf.MEDIA_VERSION


# By hosting media on a different domain we can get a speedup (more parallel
# browser connections).
#if on_production_server or not have_appserver:
#    MEDIA_URL = 'http://media.mydomain.com/media/%d/'
if DEBUG:
    MEDIA_URL="/"


COMMON_JS = [
        # See documentation why site_data can be useful:
        # http://code.google.com/p/app-engine-patch/wiki/MediaGenerator
        '.site_data.js',  #used by mediageneator to add image path in javascript
        'common/js/jquery-latest.min.js',
        'common/js/jquery-ui-latest.custom.min.js',
        'common/js/jquery-plugins.js',
        'common/js/jquery.history.js',
        'common/js/json2.js',
        'common/js/ajaxupload.js',
        'common/js/common.js',
    ]


COMMON_CSS = [
        'common/css/yahoo-grids-min.css',
    ]


def _combined_js(js_list):
    combined = []
    combined.extend(COMMON_JS)
    combined.extend(js_list)
    return tuple(combined)


def _combined_css(css_list):
    combined = []
    combined.extend(COMMON_CSS)
    combined.extend(css_list)
    return tuple(combined)


COMBINE_MEDIA = {
    'sns-combined-%(LANGUAGE_CODE)s.js': _combined_js([
        'common/js/facebox.js',
        'common/js/swfobject.js',
        'common/js/rgraph/RGraph.common.core.js',
        'common/js/rgraph/RGraph.line.js',
        'common/js/rgraph/RGraph.pie.js',
        'common/js/rgraph/RGraph.bar.js',
        'common/js/rgraph/RGraph.common.tooltips.js',
        'sns/js/sns.js',
    ]),
    'sns-combined-%(LANGUAGE_DIR)s.css': _combined_css([
        'common/css/facebox.css',
        'common/css/jquery-ui-latest.custom.css',
        'sns/css/sns.css',
    ]),
    'fe-combined-%(LANGUAGE_CODE)s.js': _combined_js([
        'common/js/facebox.js',
        'common/js/swfobject.js',
        'sns/js/sns.js',
        'fe/js/fe.js',
    ]),
    'fe-combined-%(LANGUAGE_DIR)s.css': _combined_css([
        'common/css/facebox.css',
        'common/css/jquery-ui-latest.custom.css',
        'sns/css/sns.css',
        'fe/css/fe.css',
    ]),
    'soup-combined-%(LANGUAGE_CODE)s.js': _combined_js([
        'soup/js/soup.js',
    ]),
    'soup-combined-%(LANGUAGE_DIR)s.css': _combined_css([
        'common/css/jquery-ui-latest.custom.css',
        'soup/css/soup.css',
    ]),
    'cake-combined-%(LANGUAGE_CODE)s.js': _combined_js([
        'cake/js/cake.js',
    ]),
    'cake-combined-%(LANGUAGE_DIR)s.css': _combined_css([
        'common/css/jquery-ui-latest.revisionary19.css',                                      
        'cake/css/cake.css',
    ]),
}

# Change your email settings
if on_production_server:
    DEFAULT_FROM_EMAIL = 'support@snsanalytics.com'
    SERVER_EMAIL = DEFAULT_FROM_EMAIL

# Make this unique, and don't share it with anybody.
SECRET_KEY = '998756545'

#ENABLE_PROFILER = True
#ONLY_FORCED_PROFILE = True
#PROFILE_PERCENTAGE = 25
#SORT_PROFILE_RESULTS_BY = 'cumulative' # default is 'time'
# Profile only datastore calls
#PROFILE_PATTERN = 'ext.db..+\((?:get|get_by_key_name|fetch|count|put)\)'

# Enable I18N and set default language to 'en'
USE_I18N = True
LANGUAGE_CODE = 'en'

# Restrict supported languages (and JS media generation)
LANGUAGES = (
    ('de', 'German'),
    ('en', 'English'),
)

TEMPLATE_CONTEXT_PROCESSORS = (
    'django.core.context_processors.auth',
    'django.core.context_processors.media',
    'django.core.context_processors.request',
    'django.core.context_processors.i18n',
    'ragendja.auth.context_processors.google_user',
)


if DEBUG and conf.DEBUG_DJANGO_EXCEPTION_DUMP_ON :
    MIDDLEWARE_CLASSES = (
        'ragendja.middleware.ErrorMiddleware',
        #'django.contrib.sessions.middleware.SessionMiddleware',
        # Django authentication
        #'django.contrib.auth.middleware.AuthenticationMiddleware',
        # Google authentication
        #'ragendja.auth.middleware.GoogleAuthenticationMiddleware',
        # Hybrid Django/Google authentication
        #'ragendja.auth.middleware.HybridAuthenticationMiddleware',
        'django.middleware.common.CommonMiddleware',
        'django.middleware.locale.LocaleMiddleware',
        'ragendja.sites.dynamicsite.DynamicSiteIDMiddleware',
        #'django.contrib.flatpages.middleware.FlatpageFallbackMiddleware',
        'django.contrib.redirects.middleware.RedirectFallbackMiddleware',
        'middleware.RequestHandler',
    )
else :
    MIDDLEWARE_CLASSES = (
        'ragendja.middleware.ErrorMiddleware',
        #'django.contrib.sessions.middleware.SessionMiddleware',
        # Django authentication
        #'django.contrib.auth.middleware.AuthenticationMiddleware',
        # Google authentication
        #'ragendja.auth.middleware.GoogleAuthenticationMiddleware',
        # Hybrid Django/Google authentication
        #'ragendja.auth.middleware.HybridAuthenticationMiddleware',
        'django.middleware.common.CommonMiddleware',
        'django.middleware.locale.LocaleMiddleware',
        'ragendja.sites.dynamicsite.DynamicSiteIDMiddleware',
        #'django.contrib.flatpages.middleware.FlatpageFallbackMiddleware',
        'django.contrib.redirects.middleware.RedirectFallbackMiddleware',
        'middleware.RequestHandler',
        'middleware.ExceptionHandler',
    )


# Google authentication
#AUTH_USER_MODULE = 'ragendja.auth.google_models'
#AUTH_ADMIN_MODULE = 'ragendja.auth.google_admin'
# Hybrid Django/Google authentication
#AUTH_USER_MODULE = 'ragendja.auth.hybrid_models'


#LOGIN_URL = '/guestbook/login'
#LOGOUT_URL = '/guestbook/logout/'
#LOGIN_REDIRECT_URL = '/'

INSTALLED_APPS = [
    # Add jquery support (app is in "common" folder). This automatically
    # adds jquery to your COMBINE_MEDIA['combined-%(LANGUAGE_CODE)s.js']
    # Note: the order of your INSTALLED_APPS specifies the order in which
    # your app-specific media files get combined, so jquery should normally
    # come first.
    #'django.contrib.auth',
    #'django.contrib.sessions',
    'django.contrib.admin',
    'django.contrib.webdesign',
    #'django.contrib.flatpages',
    'django.contrib.redirects',
    #'django.contrib.sites',
    'appenginepatcher',
    'ragendja',
    'common',
    'sns',
    'soup',
    'cake',
    'msb',
    'fe',
    'search',
]

if not DEBUG:
    INSTALLED_APPS.append('mediautils')


# List apps which should be left out from app settings and urlsauto loading
#IGNORE_APP_SETTINGS = IGNORE_APP_URLSAUTO = (
    # Example:
    # 'django.contrib.admin',
    # 'django.contrib.auth',
    # 'yetanotherapp',
#)

# Remote access to production server (e.g., via manage.py shell --remote)
#DATABASE_OPTIONS = {
    # Override remoteapi handler's path (default: '/remote_api').
    # This is a good idea, so you make it not too easy for hackers. ;)
    # Don't forget to also update your app.yaml!
    #'remote_url': '/remote-secret-url',

    # !!!Normally, the following settings should not be used!!!

    # Always use remoteapi (no need to add manage.py --remote option)
    #'use_remote': True,

    # Change appid for remote connection (by default it's the same as in
    # your app.yaml)
    #'remote_id': 'otherappid',

    # Change domain (default: <remoteid>.appspot.com)
    #'remote_host': 'bla.com',
#}


from common.appenginepatch.ragendja.settings_post import *
