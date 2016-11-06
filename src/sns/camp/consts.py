INTERVAL_MAP = {
    '0Min':'0 minutes',
    '5Min':'5 minutes',
    '10Min':'10 minutes',
    '15Min':'15 minutes',
    '30Min':'30 minutes', 
    '1Hr':'1 hour',
    '2Hr':'2 hours',
    '3Hr':'3 hours',
    '6Hr':'6 hours',
    '12Hr':'12 hours',
    '24Hr':'24 hours',  
    '48Hr':'48 hours',       
    '1Wk':'1 week',
    '1Mo':'1 month'            
                }

(SCHEDULE_TYPE_NOW, SCHEDULE_TYPE_ONE_TIME, SCHEDULE_TYPE_RECURRING) = range(3)
SCHEDULE_TYPES = tuple(range(3))


SCHEDULE_ARTICLE_POSTING_INTERVALS = ('30Min','1Hr', '2Hr', '3Hr', '6Hr', '12Hr', '24Hr', '48Hr', '1Wk','1Mo')
SCHEDULE_FEED_POSTING_INTERVALS = ('30Min', '1Hr', '2Hr', '3Hr', '6Hr', '12Hr', '24Hr', '48Hr', '1Wk','1Mo')

CAMPAIGN_PER_BATCH = 20
CAMPAIGN_ANALYTICS_SOURCE_DEFAULT = 'SNS.Analytics'

(CAMPAIGN_STATE_INIT, CAMPAIGN_STATE_ACTIVATED, CAMPAIGN_STATE_EXPIRED, CAMPAIGN_STATE_ERROR, CAMPAIGN_STATE_EXECUTING, CAMPAIGN_STATE_ONHOLD, CAMPAIGN_STATE_SUSPENDED) = range(7)
CAMPAIGN_STATES = tuple(range(7))

(EXECUTION_STATE_INIT, EXECUTION_STATE_EXECUTING, EXECUTION_STATE_FAILED, EXECUTION_STATE_FINISH, EXECUTION_STATE_SUSPEND) = range(5)
EXECUTION_STATES = tuple(range(5))


(RT_CAT_DUPLICATED_URL, RT_CAT_ADS_TOP_DEAL) = range(2)
RT_CATEGORIES = range(2)

