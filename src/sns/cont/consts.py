from common.content.trove import consts as trove_const


MONITOR_BING_FEED_SWITCH = 'bingfeed'
MONITOR_GOOGLE_FEED_SWITCH = 'googlefeed'
MONITOR_TOPIC_CAMPAIGN_EXECUTE = 'nocontentchannel'
MONITOR_SOUP_VIDEO_REDIRECT = 'soupvideoredirect'
MONITOR_SOUP_IMG_REDIRECT = 'soupimgredirect'
MONITOR_INSTAGRAM_FETCH = 'instagramfetch'
MONITOR_FEED_BUILDER_SWITCH = 'feedbuilderfetch'
MONITOR_FEED_BUILDER_EXECUTE = 'monitor_feed_builder_execute'
MONITOR_CHANNEL_STATUS_UPDATE = 'monitor_channel_status_update'
MONITOR_HOURLY_STATS_UPDATE = 'monitor_hourly_stats_update'
MONITOR_GLOBAL_STATS_UPDATE = 'monitor_global_stats_update'
MONITOR_GLOBAL_STATS_CMP_COUNTER_UPDATER = 'monitor_global_stats_cmp_counter_updater_%d'

INITIAL_TOPICS = \
    ['Tech','Business','Politics','Entertainment','Living','Sports', 'World', 'Local', ] + \
    ['Apple', 'iPhone','iPad','Basketball','Football', 'US', 'Europe', 'China', ]


TOPIC_TAG_COUNTRY = 'country'
TOPIC_TAG_CITY = 'city'
TOPIC_TAG_DEAL_CITY = 'deal_city'


""" Topic memcache keys """
TOPIC_MEM_KEY_PREFIX = 'topic_mem_key:'
TOPIC_MEM_KEY_TOPO_LIST = "topic_mem_key_topo_list"
TOPIC_MEM_KEY_PARENT1_PREORDER = "topic_mem_key_parent1_preorder"
TOPIC_MEM_KEY_LEVEL_1_LIST = "topic_mem_key_level_1_list"
TOPIC_MEM_KEY_ALL_US_SET = "topic_mem_key_all_us_set"
ALL_TOPIC_MEM_KEYS = (
    TOPIC_MEM_KEY_TOPO_LIST,
    TOPIC_MEM_KEY_PARENT1_PREORDER,
    TOPIC_MEM_KEY_LEVEL_1_LIST,
    TOPIC_MEM_KEY_ALL_US_SET,
    )


CS_ALL = 'cs_all'
CS_TROVE_HOSTED = 'cs_trove_hosted'
CS_TROVE_UNHOSTED = 'cs_trove_unhosted'
CS_HARK = 'hark.com'
CS_EXAMINER = 'examiner.com'
CS_DEALS = 'cs_deals'
CS_BLEACHERREPORT = 'bleacherreport.com'
CS_WETPAINT = 'wetpaint.com'
CS_JOLLY = 'jollychic.com'
CS_TRIBUNE_BROADCASTING = 'cs_tribune_broadcasting'
CS_SBNATION = 'cs_sbnation'
CS_WAPO = 'washingtonpost.com'
CS_INFO = {
           CS_TRIBUNE_BROADCASTING: dict(domains=set([
            'fox40.com', '39online.com', 'newsfixnow.com', 'fox5sandiego.com', 'ctnow.com',
            'fox17online.com', 'q13fox.com', 'abc26.com', 'wgno.com',
            'the33tv.com', 'nightcaptv.com', 'fox43.com', 'wpix.com', 'pix11.com', 'myphl17.com',
            'phl17.com', 'ktla.com', 'wgntv.com', 'cltv.com', 'wgnradio.com', 'fox59.com', 
            ]),),
           CS_SBNATION: dict(domains=set([
            'sbnation.com', 
            ]),),
           }
CS_PROMOTED = [CS_JOLLY, ]

def _domain_2_cs_map():
    _map = {}
    for cskey, cs_dict in CS_INFO.items():
        for domain in cs_dict.get('domains', set([])):
            _map[domain] = cskey
    return _map
DOMAIN_2_CS_MAP = _domain_2_cs_map()

CS_BLACKLIST = trove_const.VISOR_UNFRIENDLY_BLACKSET #set(trove_const.SNS_BLACKLIST)
TROVE_CS_KEYS = (CS_TROVE_HOSTED, CS_TROVE_UNHOSTED)

FEED_SOURCE_SEARCH_KEYWORD = 0
FEED_SOURCE_GOOGLE_NEWS = 1
FEED_SOURCE_BING_NEWS = 2
FEED_SOURCE_TROVE = 3
FEED_SOURCE_REDDIT = 4
FEED_SOURCE_YOUTUBE = 5
FEED_SOURCE_JOLLY = 6
FEED_SOURCE_INSTAGRAM = 7
FEED_SORCE_VIMEO = 8
FEED_SOURCE_DEAL = 9
FEED_SOURCE_CATEGORY_DEAL = 10

FEED_SOURCE_TRIBUNE_BROADCASTING = 1045
FEED_SOURCE_SBNATION = 1046

FEED_SOURCE_MAP = {
    FEED_SOURCE_SEARCH_KEYWORD:'Google Search Keywords',
    FEED_SOURCE_GOOGLE_NEWS:"Google News",
    FEED_SOURCE_BING_NEWS:"Bing News",
    FEED_SOURCE_TROVE: "Trove News",
    FEED_SOURCE_REDDIT:"Reddit",
    FEED_SOURCE_YOUTUBE:"Youtube",
    FEED_SOURCE_JOLLY:'Jolly',
    FEED_SOURCE_INSTAGRAM:'Instagram',
    FEED_SORCE_VIMEO:'Vimeo',
    FEED_SOURCE_DEAL:'Deal',
    FEED_SOURCE_CATEGORY_DEAL: 'Category Deal',
    FEED_SOURCE_TRIBUNE_BROADCASTING: 'Tribune Broadcasting',
    FEED_SOURCE_SBNATION: 'SB Nation',
    }

FEED_SOURCE_STANDARD_URL_PATTERN_MAP = {
#     FEED_SOURCE_GOOGLE_NEWS:"http://news.google.com/news/search?aq=f&pz=1&cf=all&ned=us&hl=en&q=%s&output=RSS",
    FEED_SOURCE_GOOGLE_NEWS:"https://news.google.com/news?num=15&ned=us&hl=en&q=%s&output=rss",
    FEED_SOURCE_BING_NEWS:"http://api.bing.com/rss.aspx?Source=News&Market=en-US&Version=2.0&Query=%s",
    FEED_SOURCE_TROVE:"http://mysocialboard.com/troverss/%s/",
    FEED_SOURCE_REDDIT:"http://feeds.feedburner.com/msb/4/%s",
    FEED_SOURCE_YOUTUBE:"http://gdata.youtube.com/feeds/api/videos?orderby=updated&vq=%s",
    FEED_SOURCE_JOLLY:'http://mysocialboard.com/jollyrss/%s/',
    FEED_SOURCE_INSTAGRAM:'http://pipes.yahoo.com/pipes/pipe.run?_id=31e9fdab5835ef3ebccf213e85a0e319&_render=rss&q=%s',
    FEED_SORCE_VIMEO:'http://vimeo.com/tag:%s/rss',
    FEED_SOURCE_DEAL:'http://www.snsanalytics.com/deal/rss/%s',
    FEED_SOURCE_CATEGORY_DEAL:'http://www.snsanalytics.com/deal/rss/%s/%s/',
    }

FEED_SOURCE_TOPIC_NUMBER_MAP = {
    FEED_SOURCE_CATEGORY_DEAL: 2,
    }

FEED_SOURCE_CHOICES = [(fsid, name) for fsid, name in FEED_SOURCE_MAP.items()]

def _primary_feed_source_map():
    _map = {}
    for fsid, name in FEED_SOURCE_MAP.items(): 
        if fsid > 0 and fsid < 1000:
            _map[fsid] = name
    return _map
PRIMARY_FEED_SOURCE_MAP = _primary_feed_source_map()

PRIMARY_FEED_SOURCE_CHOICES = [(fsid, name) for fsid, name in PRIMARY_FEED_SOURCE_MAP.items()]

 
FEED_CRAWLER_LIST = [
    (CS_EXAMINER, "http://www.examiner.com/rss_special/sns_celebrity", ['Celebrities',]),                     
                     ]

