# -*- coding: utf-8 -*-
"""
This module contains all API related constants that should be shared with any API client.
"""


"""
All API request methods supported.
"""
API_HTTP_METHOD_GET = 'GET'
API_HTTP_METHOD_POST = 'POST'


"""
All API request data formats supported.
"""
API_REQUEST_DATA_FORMATS = ('json', 'plain', 'xml') 


"""
All API modules.
"""
API_M_ADMIN                 = 'admin'
API_M_ADS                   = 'ads'
API_M_CHANNEL               = 'chan'
API_M_FCHANNEL              = 'chan/facebook'
API_M_FBPAGE                = 'chan/fbpage'
API_M_TWITTER_OAUTH_TOKEN   = 'chan/twitteroauth'
API_M_MAIL_LIST             = 'email/list'
API_M_MAIL_CONTACT          = 'email/contact'
API_M_MAIL_TEMPLATE         = 'email/template'
API_M_MAIL_CAMPAIGN         = 'email/campaign'
API_M_MAIL_EXECUTION        = 'email/execution'
API_M_CAMPAIGN              = 'camp'
API_M_CAMPAIGN_RECORD       = 'camp/record'
API_M_CONTENT               = 'cont'
API_M_ARTICLE               = 'message'
API_M_BASE_FEED             = 'basefeed'
API_M_FEED                  = 'rssfeed'
API_M_RAW_CONTENT           = 'cont/raw'
API_M_TOPIC_CS_CONTENT      = 'cont/topic_cs'
API_M_DEAL_BUILDER          = 'deal'
API_M_LINK                  = 'cust/linking'
API_M_CUSTOM_RULE           = 'cust/rule'
API_M_POSTING_RULE          = 'post/rule'
API_M_POSTING_RULE_ARTICLE  = 'post/rule/article'
API_M_POSTING_RULE_FEED     = 'post/rule/feed'
API_M_POSTING_RULE_QUICK    = 'post/rule/quick'
API_M_POSTING_POSTING       = 'post/posting'
API_M_POSTING_POST          = 'post/post'
API_M_POSTING_POST_ARTICLE  = 'post/post/article'
API_M_POSTING_POST_FEED     = 'post/post/feed'
API_M_FEED_BUILDER          = 'feedbuilder'
API_M_FEED_BUILDER_TOPIC_SCORE          = 'feedbuilder/topic_score'
API_M_FE_MASTER             = 'femaster'
API_M_FE_MASTER_SOURCE      = 'femaster/source'
API_M_FE_MASTER_TARGET      = 'femaster/target'
API_M_FE_MASTER_TOPIC_TARGET            = 'femaster/topic_target'
API_M_FE_MASTER_TOPIC_TARGET_ERROR      = 'femaster/topic_target_error'
API_M_FE_MASTER_ALLOC_LOG               = 'femaster/alloc_log'
API_M_FE_MASTER_FOLLOW_LOG              = 'femaster/follow_log'
API_M_URLSHORTENER          = 'urlshort'
API_M_USER                  = 'usr'
API_M_GLOBAL_URL            = 'url/globalurl'
API_M_URL_COUNTER           = 'urlcounter'
API_M_CHANNEL_COUNTER       = 'channelcounter'
API_M_FEED_COUNTER          = 'feedcounter'
API_M_LINK_COUNTER          = 'linkcounter'
API_M_SURL_COUNTER          = 'surlcounter'
API_M_USER_COUNTER          = 'usercounter'
API_M_GLOBAL_COUNTER        = 'globalcounter'
API_M_SITE_MAP              = 'sitemap'
API_M_TOPIC                 = 'topic'
API_M_WEBSITE               = 'website'
API_M_LOG_GLOBAL_STATS      = 'log/globalstats'
API_M_LOG_HOURLY_STATS      = 'log/hourlystats'
API_M_LOG_CMP_TWITTER_STATS = 'log/cmptwitterstats'
API_M_MGMT                  = 'mgmt'
API_M_MGMT_TOPIC            = 'mgmt/topic'
API_M_DM_RULE               = 'dm/rule'
API_M_ADVANCED_DM_RULE      = 'dm/rule/advanced'
API_M_ACCTMGMT_YAHOO        = 'acctmgmt/yahoo'
API_M_ACCTMGMT_CMP          = 'acctmgmt/cmp'


"""
All API operations.
Not all API modules support all API operations.
"""
API_O_ADMIN = 'admin'
API_O_CREATE = 'create'
API_O_GET = 'get'
API_O_UPDATE = 'update'
API_O_DELETE = 'delete'
API_O_QUERY = 'query'
API_O_QUERY_BY_CURSOR = 'query_by_cursor'
API_O_QUERY_ALL = 'queryall'
API_O_REMOVE = 'remove'
API_O_IMPORT = 'import_obj'
API_O_REFRESH = 'refresh'
API_O_REFRESH_ALL = 'refreshall'
API_O_ACTIVATE = 'activate'
API_O_DEACTIVATE = 'deactivate'
API_O_POST = 'post'
API_O_POST_DATA_TRANSLATE = 'postdatatranslate'
API_O_SCHEDULE = 'schedule'
API_O_EXECUTE = 'execute'
API_O_POST_JOB_COUNT = 'jobcount'
API_O_POST_EXPEDITE = 'expedite'
API_O_APPROVE = 'approve'
API_O_UPGRADE = 'upgrade'
API_O_DEGRADE = 'degrade'
API_O_GETALLSTATS = 'getallstats'
API_O_CLEAN = 'clean'
API_O_CLEAN_SYS = 'sysclean'
API_O_CHANGE_USER = 'changeuser'
API_O_CRON_EXECUTE = 'cron_execute'
API_O_ADD_TWITTER_ACC = 'addtwitteracct'
API_O_SEPERATE_CHANNELS = 'seperatechannels'
API_O_BATCH_FOLLOW = 'batchfollow'
API_O_CRON_PAYMENT_CHECK = 'cron_check'
API_O_CRON_FOLLOW_BATCH = 'cron_follow_batch'
API_O_ADD_SHORT_MESSAGE = 'addshortmessage'
API_O_ADD_CHANNEL_USER_EMAIL = 'addchannelemail'
API_O_CHANGE_CAMPAIGN_SNSANALYTICS_SOURCE = 'changeanalyticssource'
API_O_RATE = 'rate'


"""
The second value marks whether the OP is admin or not.
The third value marks whether the OP is cron or not. A cron job is an admin job that doesn't require a current login user.
"""
API_OPERATION_MAP = {
    API_O_ADMIN: ([API_HTTP_METHOD_GET, API_HTTP_METHOD_POST], True, False),
    API_O_CREATE: (API_HTTP_METHOD_POST, False, False),
    API_O_GET: (API_HTTP_METHOD_GET, False, False),
    API_O_UPDATE: (API_HTTP_METHOD_POST, False, False),
    API_O_DELETE: (API_HTTP_METHOD_POST, False, False),
    API_O_QUERY: (API_HTTP_METHOD_GET, False, False),
    API_O_QUERY_BY_CURSOR: (API_HTTP_METHOD_GET, False, False),
    API_O_QUERY_ALL: (API_HTTP_METHOD_GET, True, True),
    API_O_REMOVE: (API_HTTP_METHOD_GET, True, False),
    API_O_REFRESH: (API_HTTP_METHOD_GET, True, False),
    API_O_IMPORT: (API_HTTP_METHOD_POST, True, False),
    API_O_REFRESH_ALL: (API_HTTP_METHOD_GET, True, False),
    API_O_ACTIVATE: (API_HTTP_METHOD_POST, False, False),
    API_O_DEACTIVATE: (API_HTTP_METHOD_POST, False, False),
    API_O_CHANGE_USER: (API_HTTP_METHOD_POST, True, False),
    API_O_POST: (API_HTTP_METHOD_POST, False, False),
    API_O_SCHEDULE: (API_HTTP_METHOD_GET, True, False),
    API_O_EXECUTE: (API_HTTP_METHOD_GET, True, False),
    API_O_POST_JOB_COUNT: (API_HTTP_METHOD_GET, True, False),
    API_O_POST_EXPEDITE: (API_HTTP_METHOD_GET, True, False),
    API_O_APPROVE: (API_HTTP_METHOD_POST, True, False),
    API_O_UPGRADE: (API_HTTP_METHOD_POST, True, False),
    API_O_DEGRADE: (API_HTTP_METHOD_POST, True, False),
    API_O_GETALLSTATS: (API_HTTP_METHOD_GET, False, False),
    API_O_CLEAN: (API_HTTP_METHOD_POST, True, False),
    API_O_CLEAN_SYS: (API_HTTP_METHOD_POST, True, False),
    API_O_CRON_EXECUTE: (API_HTTP_METHOD_GET, True, True),
    API_O_ADD_TWITTER_ACC: (API_HTTP_METHOD_POST, False, False),
    API_O_SEPERATE_CHANNELS: (API_HTTP_METHOD_POST, False, False),
    API_O_BATCH_FOLLOW: (API_HTTP_METHOD_POST, False, False),
    API_O_ADD_SHORT_MESSAGE: (API_HTTP_METHOD_GET, False, False),
    API_O_CRON_PAYMENT_CHECK: (API_HTTP_METHOD_GET, True, True),
    API_O_CRON_FOLLOW_BATCH: (API_HTTP_METHOD_GET, True, True),
    API_O_POST_DATA_TRANSLATE: (API_HTTP_METHOD_GET, True, False),
    API_O_ADD_CHANNEL_USER_EMAIL: (API_HTTP_METHOD_GET, True, False),
    API_O_CHANGE_CAMPAIGN_SNSANALYTICS_SOURCE: (API_HTTP_METHOD_GET, True, False),
    API_O_RATE: (API_HTTP_METHOD_GET, False, False),
    }

def get_api_operation_perms(operation):
    http_methods, is_admin, is_cron = API_OPERATION_MAP.get(operation, ([], None, None))
    if isinstance(http_methods, basestring): http_methods = [http_methods]
    return http_methods, is_admin, is_cron

def get_api_http_methods(operation):
    return get_api_operation_perms(operation)[0]

def get_api_http_method(operation):
    http_methods = get_api_operation_perms(operation)[0]
    return http_methods[0] if http_methods else None

    
if __name__ == '__main__':
    pass
