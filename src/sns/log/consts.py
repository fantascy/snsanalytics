import conf


PATTERN_KEY_WORD = 'keyword'
PATTERN_FULL_NAME = 'fullname'
PATTERN_IP_LIST = 'iplist'
PATTERN_USER_LIST = 'user'
PATTERN_DEMO_LIST = 'demo'
PATTERN_GA_LIST = 'ga'
PATTERN_DOS_LIST = 'dos'
PATTERN_AD_SITE = 'adsite'
PATTERN_FRAME_SITE = 'framesite'
PATTERN_REDIRECT_USER = 'redirectuser'


FACEBOOK_REAL_TIME_VERIFY_TOKEN = 'allnewsoup'


FOLLOW_ENGINES = (
                  'actualizeryourself',
                  'b2realworld',
                  'bigdataworld',
                  'findshowtime', 
                  'hallowean', 
                  'postsocialworld',
                  'prehistoricufo', 
                  'quicksocial',
                  'sfbayunited',
                  'twittergiants',
                  )
FOLLOW_ENGINES_DAGGERED = ()
FOLLOW_ENGINES_DOUBLE_DAGGERED = ()
def _fe_display(fe):
    return fe + ' **' if fe in FOLLOW_ENGINES_DOUBLE_DAGGERED else (fe + ' *' if fe in FOLLOW_ENGINES_DAGGERED else fe) 
FOLLOW_ENGINE_CHOICES = [("all", "All")] + [(fe, _fe_display(fe)) for fe in FOLLOW_ENGINES]


EMAIL_SERVER_2_FE_MAP = {
    }
EMAIL_SERVERS = EMAIL_SERVER_2_FE_MAP.keys()


KNOWN_NON_CMP_TWITTER_ACCOUNTS = (
    'bryanspringer', 'chrishelleman', 'darren_barefoot', 'frank_parker', 'grocerysalmon_', 'heather_adams09', 'irenesermer', 'jamescracker', 'kimberly_marcus', 'lesliepenninge', 'marcustulane', 'nancywilliamssa', 
    'oliviawalter', 'walter017', 'perrychecker', 'checker112', 'quinncarnegie', 'quinn_sar', 'rosiebrokaw', 'smithryan01', 'timmacarthy', 'tracylee_', 'zacharyalberso', 
    'alanxing', 'travelingdad',
)

CHANNEL_STATS_CHART_POSTS = 0
CHANNEL_STATS_CHART_CLICKS = 1
CHANNEL_STATS_CHART_FOLLOWERS = 2
CHANNEL_STATS_CHART_KLOUT_SCORES = 3
CHANNEL_STATS_CHART_SEARCH_RANKS = 4
CHANNEL_STATS_CHART_RETWEETS = 5
CHANNEL_STATS_CHART_MENTIONS = 6
CHANNEL_STATS_CHART_HASHTAGS = 7
CHANNEL_STATS_CHART_COMPARISON = 8
CHANNEL_STATS_CHART_TYPES_NO_COMPARISION = (
    CHANNEL_STATS_CHART_POSTS, 
    CHANNEL_STATS_CHART_CLICKS,
    CHANNEL_STATS_CHART_FOLLOWERS,
    CHANNEL_STATS_CHART_KLOUT_SCORES,
    CHANNEL_STATS_CHART_SEARCH_RANKS,
    CHANNEL_STATS_CHART_RETWEETS,
    CHANNEL_STATS_CHART_MENTIONS,
    CHANNEL_STATS_CHART_HASHTAGS,
    )
CHANNEL_STATS_CHART_ATTR_MAP = {
    CHANNEL_STATS_CHART_POSTS: "postCounts", 
    CHANNEL_STATS_CHART_CLICKS: "clickCounts",
    CHANNEL_STATS_CHART_FOLLOWERS: "followerCounts",
    CHANNEL_STATS_CHART_KLOUT_SCORES: "kloutScores",
    CHANNEL_STATS_CHART_SEARCH_RANKS: "searchRanks",
    CHANNEL_STATS_CHART_RETWEETS: "retweetCounts",
    CHANNEL_STATS_CHART_MENTIONS: "mentionCounts",
    CHANNEL_STATS_CHART_HASHTAGS: "hashtagCounts",
    CHANNEL_STATS_CHART_COMPARISON: "comparison",
    }
CHANNEL_STATS_CHART_CHOICES = [
    (CHANNEL_STATS_CHART_POSTS,"Posts"), 
    (CHANNEL_STATS_CHART_CLICKS,"Clicks"),
    (CHANNEL_STATS_CHART_FOLLOWERS,"Followers"),
    (CHANNEL_STATS_CHART_KLOUT_SCORES,"Klout Scores"),
    (CHANNEL_STATS_CHART_SEARCH_RANKS, "Search Ranks"),
    (CHANNEL_STATS_CHART_RETWEETS,"Retweets"),
    (CHANNEL_STATS_CHART_MENTIONS,"Mentions"),
    (CHANNEL_STATS_CHART_HASHTAGS,"Hashtags"),
    (CHANNEL_STATS_CHART_COMPARISON,"Comparison"),
    ]


CS_STATS_CHART_COMPARISON = -1
CS_STATS_CHART_POSTS = 0
CS_STATS_CHART_CLICKS = 1
CS_STATS_CHART_TYPES_NO_COMPARISION = (
    CS_STATS_CHART_POSTS, 
    CS_STATS_CHART_CLICKS,
    )
CS_STATS_CHART_ATTR_MAP = {
    CS_STATS_CHART_POSTS: "postCounts", 
    CS_STATS_CHART_CLICKS: "clickCounts",
    CS_STATS_CHART_COMPARISON: "comparison",
    }
CS_STATS_CHART_CHOICES = [
    (CS_STATS_CHART_POSTS,"Posts"), 
    (CS_STATS_CHART_CLICKS,"Clicks"),
    (CS_STATS_CHART_COMPARISON,"Comparison"),
    ]


LOG_TIMEZONE = 'US/Pacific'  


HOURLY_STATS_CONTENT_SOURCE = 10070


GLOBAL_STATS_COMPARISON = -1
GLOBAL_STATS_TOTAL_CLICKS = 5
GLOBAL_STATS_TOTAL_POSTS = 2
GLOBAL_STATS_TOTAL_UNIQUE_URLS = 3
GLOBAL_STATS_CMP_CLICKS = 0
GLOBAL_STATS_CMP_POSTS = 1
GLOBAL_STATS_CMP_CLICKED_URLS = 4
GLOBAL_STATS_CMP_FOLLOWERS = 7
GLOBAL_STATS_CMP_ACTIVE_FE_CAMPAIGNS = 9
GLOBAL_STATS_CMP_TWITTER_ACCTS = 8
GLOBAL_STATS_CMP_TWITTER_ACCT_NO_TOPICS = 12
GLOBAL_STATS_TWITTER_SEARCH_RANK_TOP_3 = 10
GLOBAL_STATS_TWITTER_SEARCH_RANK_TOP_20 = 11
GLOBAL_STATS_KLOUT_SCORE_100TH = 13
GLOBAL_STATS_KLOUT_SCORE_1000TH = 14
GLOBAL_STATS_RETWEETS_ALL = 30
GLOBAL_STATS_RETWEETS_NONORGANIC = 31
GLOBAL_STATS_RETWEETS_ORGANIC = 32
GLOBAL_STATS_RETWEETS_DUP_ARTICLES = 33
GLOBAL_STATS_RETWEETS_TOP_DEALS = 34
GLOBAL_STATS_MENTIONS_ALL = 50
GLOBAL_STATS_HASHTAGS = 60
GLOBAL_STATS_CONTENT_SOURCE = 70
GLOBAL_STATS_CMP_TWITTER_ACCT_BASIC_INFO = 80
GLOBAL_STATS_ONCE_SUSPENDED_CHIDS = 81
GLOBAL_STATS_CMP_COUNTER_UPDATER_0 = 90
GLOBAL_STATS_CMP_COUNTER_UPDATER_1 = 91
GLOBAL_STATS_CMP_COUNTER_UPDATER_2 = 92
GLOBAL_STATS_CMP_COUNTER_UPDATER_3 = 93
GLOBAL_STATS_CMP_COUNTER_UPDATER_4 = 94
GLOBAL_STATS_CMP_COUNTER_UPDATER_5 = 95
GLOBAL_STATS_CMP_COUNTER_UPDATER_6 = 96
GLOBAL_STATS_CMP_COUNTER_UPDATER_7 = 97
GLOBAL_STATS_CMP_COUNTER_UPDATER_8 = 98
GLOBAL_STATS_CMP_COUNTER_UPDATER_9 = 99
GLOBAL_STATS_DEAL_STATS = 2001

GLOBAL_STATS_DISPLAY_NAME_TUPLE = [
#    (GLOBAL_STATS_TOTAL_CLICKS, "Total Clicks"),
#    (GLOBAL_STATS_TOTAL_POSTS, "Total Posts"),
    (GLOBAL_STATS_CMP_CLICKS, "Clicks"),
    (GLOBAL_STATS_CMP_POSTS, "Posts"),
    (GLOBAL_STATS_TOTAL_UNIQUE_URLS, "Unique URLs"),
#    (GLOBAL_STATS_CMP_CLICKED_URLS, "Clicked URLs"),
    (GLOBAL_STATS_CMP_FOLLOWERS, "Followers"),
    (GLOBAL_STATS_CMP_TWITTER_ACCTS, "Accounts"),
    (GLOBAL_STATS_COMPARISON, "Comparison"),
    ] 

if conf.EXTRA_FEATURES: GLOBAL_STATS_DISPLAY_NAME_TUPLE.extend([
    (GLOBAL_STATS_CMP_ACTIVE_FE_CAMPAIGNS, "Active FE Campaigns"),
    (GLOBAL_STATS_TWITTER_SEARCH_RANK_TOP_3, "Search Ranked Top 3"),
    (GLOBAL_STATS_TWITTER_SEARCH_RANK_TOP_20, "Search Ranked Top 20"),
    (GLOBAL_STATS_KLOUT_SCORE_100TH, "100th Klout Score"),
    (GLOBAL_STATS_KLOUT_SCORE_1000TH, "1000th Klout Score"),
    (GLOBAL_STATS_RETWEETS_DUP_ARTICLES, "Retweets - Dup Articles"),
    (GLOBAL_STATS_RETWEETS_TOP_DEALS, "Retweets - Top Deals"),
    (GLOBAL_STATS_MENTIONS_ALL, "Mentions - All"),
    (GLOBAL_STATS_HASHTAGS, "Hashtags"),
    ])

GLOBAL_STATS_DISPLAY_NAME_MAP = dict(GLOBAL_STATS_DISPLAY_NAME_TUPLE)

GLOBAL_STATS_DISPLAY_LIST = tuple([item[0] for item in GLOBAL_STATS_DISPLAY_NAME_TUPLE])
