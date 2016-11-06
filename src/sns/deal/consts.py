""" Deal distribution channel types """
CHANNEL_DEAL_TWITTER_ACCOUNTS = 0
CHANNEL_DEAL_MOBILE_APPS = 1


""" All API keys. """
GROUPON_CLIENT_ID = '4f75b47a49d93f43ae1bd1ee8feac101c5015584'
YIPIT_KEY = '6LTYCYzkYbhte8W7'
DEALSURF_KEY = '5fa9e41bfec0725742cc9d15ef594120'


""" All deal sources. """
DEAL_SOURCE_GROUPON = 'GROUPON'
DEAL_SOURCE_DEALON = 'DEALON'
DEAL_SOURCE_KGBDEALS = 'KGB'
DEAL_SOURCE_MAMAPEDIA = 'MAMAPEDIA'
DEAL_SOURCE_CROWDSAVINGS = 'CROWDSAVINGS'
DEAL_SOURCE_TIPPR = 'TIPPR'
DEAL_SOURCE_JUICEINTHECITY = 'JITC'
DEAL_SOURCE_MYDAILYDEALS = 'MYDAILYDEALS'
DEAL_SOURCE_LIVINGSOCIAL = 'LIVINGSOCIAL'
DEAL_SOURCE_PLUMDISTRICT = 'PLUMDISTRICT'
DEAL_SOURCE_SAVEOLOGY = 'SAVEOLOGY'
DEAL_SOURCE_DEALSTER = 'DEALSTER'
DEAL_SOURCE_ZOZI = 'ZOZI'
DEAL_SOURCE_YOURBESTDEALS = 'YOUBESTDEALS'


""" All affiliation networks. """
AFF_CJ = 'CJ'
AFF_LINKSHARE = 'LINKSHARE'


""" All affiliate IDs. """
AFF_ID_CJ_TWITTER = '5517529'
AFF_ID_CJ_MOBILE = '5755239'
AFF_ID_CJ = AFF_ID_CJ_TWITTER
AFF_ID_URL_PARAMS = {
    DEAL_SOURCE_CROWDSAVINGS: {'aff_id': 'allnewsoup'},
    DEAL_SOURCE_JUICEINTHECITY: {'referrer': 'l7ptpgnvm8'},
    DEAL_SOURCE_MYDAILYDEALS: {'affiliate_id': '183'},
    DEAL_SOURCE_PLUMDISTRICT: {'affiliate_url': 'http://gan.doubleclick.net/gan_click?lid=41000000032549767&pubid=21000000000508492'},
    DEAL_SOURCE_ZOZI: {'p': '265'},
    AFF_LINKSHARE: {'r': 'allnewsoup'},
                     }


""" Each tuple contains (Name, Affiliation Program, DealSurf supported) """
DEAL_SOURCE_MAP = {
    DEAL_SOURCE_GROUPON: ('Groupon', AFF_CJ, True),
    DEAL_SOURCE_LIVINGSOCIAL: ('Living Social', None, True),
    DEAL_SOURCE_DEALON: ('DealOn', AFF_CJ, True),
    DEAL_SOURCE_KGBDEALS: ('KGB Deals', AFF_CJ, True),
    DEAL_SOURCE_MAMAPEDIA: ('Mamapedia', AFF_CJ, True),
    DEAL_SOURCE_CROWDSAVINGS: ('Crowd Savings', DEAL_SOURCE_CROWDSAVINGS, True),
    DEAL_SOURCE_TIPPR: ('Tippr', DEAL_SOURCE_TIPPR, True),
    DEAL_SOURCE_JUICEINTHECITY: ('Juice in the City', DEAL_SOURCE_JUICEINTHECITY, True),
    DEAL_SOURCE_MYDAILYDEALS: ('My Daily Deals', DEAL_SOURCE_MYDAILYDEALS, False),
    DEAL_SOURCE_PLUMDISTRICT: ('Plum District', DEAL_SOURCE_PLUMDISTRICT, True),
    DEAL_SOURCE_SAVEOLOGY: ('Saveology', None, True),
    DEAL_SOURCE_DEALSTER: ('Dealster', None, True),
    DEAL_SOURCE_ZOZI: ('Zozi', DEAL_SOURCE_ZOZI, True),
    DEAL_SOURCE_YOURBESTDEALS: ('Your Best Deals', AFF_LINKSHARE, True),
                }


DEAL_SOURCE_BLACKLIST = set([
                         ])


DEAL_SOURCE_API_ENABLED = set([
    DEAL_SOURCE_GROUPON,                        
                         ])


DEAL_BUILDER_BUFFER_SIZE = 50
DEAL_BUILDER_BUFFER_SIZE_DEBUG = 5
DEAL_BUILDER_BUFFER_SIZE_NATIONAL = 500
DEAL_BUILDER_BUFFER_SIZE_NATIONAL_DEBUG = 20


CITY_2_GROUPON_DIVISION_MAP = {
    'losangelesca': 'los-angeles', 
    'miamifl': 'miami', 
    'fresnoca': 'fresno', 
    'charlottenc': 'charlotte', 
    'washingtondc': 'washington-dc', 
    'tampafl': 'tampa-bay-area', 
    'chicagoil': 'chicago', 
    'orlandofl': 'orlando', 
    'elpasotx': 'el-paso', 
    'kansascitymo': 'kansas-city', 
    'tucsonaz': 'tucson', 
    'detroitmi': 'detroit', 
    'stlouismo': 'stlouis', 
    'indianapolisin': 'indianapolis', 
    'oklahomacityok': 'oklahoma-city', 
    'columbusoh': 'columbus', 
    'portlandor': 'portland', 
    'dallastx': 'dallas', 
    'baltimoremd': 'baltimore', 
    'austintx': 'austin', 
    'seattlewa': 'seattle', 
    'houstontx': 'houston', 
    'memphistn': 'memphis', 
    'pittsburghpa': 'pittsburgh', 
    'sandiegoca': 'san-diego', 
    'sacramentoca': 'sacramento', 
    'albuquerquenm': 'albuquerque', 
    'phoenixaz': 'phoenix', 
    'philadelphiapa': 'philadelphia', 
    'sanjoseca': 'san-jose', 
    'jacksonvillefl': 'jacksonville', 
    'minneapolismn': 'minneapolis-stpaul', 
    'lasvegasnv': 'las-vegas', 
    'bostonma': 'boston', 
    'nashvilletn': 'nashville', 
    'sanfranciscoca': 'san-francisco', 
    'denverco': 'denver', 
    'milwaukeewi': 'milwaukee', 
    'atlantaga': 'atlanta', 
    'newyorkny': 'new-york', 
    'sanantoniotx': 'san-antonio', 
    'louisvilleky': 'louisville',
                     }

CITY_2_GROUPON_TOP_DEAL_MAP = {
    'losangelesca': "http://www.dpbolvw.net/click-5517529-10795773", 
    'miamifl': "http://www.kqzyfj.com/click-5517529-10795799", 
    'fresnoca': None, 
    'charlottenc': None, 
    'washingtondc': None, 
    'tampafl': None, 
    'chicagoil': "http://www.dpbolvw.net/click-5517529-10795770", 
    'orlandofl': None, 
    'elpasotx': None, 
    'kansascitymo': "http://www.anrdoezrs.net/click-5517529-10795797", 
    'tucsonaz': "http://www.jdoqocy.com/click-5517529-10796932", 
    'detroitmi': None, 
    'stlouismo': None, 
    'indianapolisin': None, 
    'oklahomacityok': None, 
    'columbusoh': None, 
    'portlandor': None, 
    'dallastx': "http://www.jdoqocy.com/click-5517529-10795776", 
    'baltimoremd': None, 
    'austintx': None, 
    'seattlewa': None, 
    'houstontx': None, 
    'memphistn': None, 
    'pittsburghpa': "http://www.jdoqocy.com/click-5517529-10795808", 
    'sandiegoca': None, 
    'sacramentoca': None, 
    'albuquerquenm': "http://www.tkqlhce.com/click-5517529-10796933", 
    'phoenixaz': None, 
    'philadelphiapa': "http://www.dpbolvw.net/click-5517529-10795789", 
    'sanjoseca': None, 
    'jacksonvillefl': None, 
    'minneapolismn': None, 
    'lasvegasnv': None, 
    'bostonma': None, 
    'nashvilletn': "http://www.jdoqocy.com/click-5517529-10795786", 
    'sanfranciscoca': "http://www.kqzyfj.com/click-5517529-10795774", 
    'denverco': None, 
    'milwaukeewi': "http://www.dpbolvw.net/click-5517529-10795800", 
    'atlantaga': None, 
    'newyorkny': None, 
    'sanantoniotx': "http://www.dpbolvw.net/click-5517529-10795793", 
    'louisvilleky': "http://www.anrdoezrs.net/click-5517529-10795801",
                     }

DEAL_TOPIC_SHOPPING = 'Shopping'
TOPIC_2_GROUPON_CATEGORY_MAP = {
    'Entertainment': ['Arts and Entertainment'],
    'Motors': ['Automotive'],
    'Beauty': ['Beauty & Spas'],
    'Education': ['Education'],
    'Personal Finance': ['Financial Services'],
    'Food': ['Food & Drink'],
    'Health': ['Health & Fitness'],
    'Home': ['Home Services', 'Services'],
    'Legal Services': ['Legal Services'],
    'Nightlife': ['Nightlife'],
    'Pets': ['Pets'],
    'Professional Services': ['Professional Services'],
    'Politics': ['Public Services & Government'],
    'Real Estate': ['Real Estate'],
    'Religion': ['Religious Organizations'],
    'Restaurants': ['Restaurants'],
    DEAL_TOPIC_SHOPPING: ['Shopping'],
    'Travel': ['Travel'],
    }

TOPIC_2_GROUPON_CHANNEL_MAP = {
    'Entertainment': None,
    'Motors': None,
    'Beauty': None,
    'Education': None,
    'Personal Finance': None,
    'Food': None,
    'Health': None,
    'Home': None,
    'Legal Services': None,
    'Nightlife': None,
    'Pets': None,
    'Professional Services': None,
    'Politics': None,
    'Real Estate': None,
    'Religion': None,
    'Restaurants': None,
    'Shopping': None,
    'Travel': 'getaways',
    }


DEALSURF_LOCATION_MAP = {
    'us': 'US', 
    'losangelesca': 'LAX', 
    'miamifl': 'MIA', 
    'fresnoca': 'FAT', 
    'charlottenc': 'CLT', 
    'washingtondc': 'DCA', 
    'tampafl': 'TPA', 
    'chicagoil': 'CHI', 
    'orlandofl': 'MCO', 
    'elpasotx': None, 
    'kansascitymo': 'MCI', 
    'tucsonaz': 'TUS', 
    'detroitmi': 'DET', 
    'stlouismo': 'STL', 
    'indianapolisin': 'IND', 
    'oklahomacityok': 'OKC', 
    'columbusoh': 'CMH', 
    'portlandor': 'PDX', 
    'dallastx': 'DAL', 
    'baltimoremd': 'BWI', 
    'austintx': 'AUS', 
    'seattlewa': 'SEA', 
    'houstontx': 'HOU', 
    'memphistn': 'MEM', 
    'pittsburghpa': 'PIT', 
    'sandiegoca': 'SAN', 
    'sacramentoca': 'SMF', 
    'albuquerquenm': 'ABQ', 
    'phoenixaz': 'PHX', 
    'philadelphiapa': 'PHL', 
    'sanjoseca': 'SJC', 
    'jacksonvillefl': 'JAX', 
    'minneapolismn': 'MSP', 
    'lasvegasnv': 'LAS', 
    'bostonma': 'BOS', 
    'nashvilletn': 'BNA', 
    'sanfranciscoca': 'SFO', 
    'denverco': 'DEN', 
    'milwaukeewi': 'MKE', 
    'atlantaga': 'ATL', 
    'newyorkny': 'NYC', 
    'sanantoniotx': 'SAT', 
    'louisvilleky': 'SDF',       
    }

TOPIC_2_DEALSURF_CATEGORY_MAP = {
    'Entertainment': ['ACTIV', 'EVENT', 'TICKS'],
    'Beauty': ['BEAU'],
    'Education': ['EDUC'],
    'Home': ['LABOR'],
    'Pets': ['PETS'],
    'Restaurants': ['REST'],
    'Shopping': ['CLOTH', 'ELEC', 'PROD'],
    'Travel': ['TRAV'],
    }


def _build_category_2_topic_map(topic2CategoryMap, category2TopicMap):
    from common.utils import string as str_util
    for topic , tags in topic2CategoryMap.items():
        topicKey = str_util.name_2_key(topic) 
        cats = [str_util.name_2_key(tag) for tag in tags]
        for cat in cats:
            topicKeys = category2TopicMap.get(cat, [])
            if topicKey not in topicKeys:
                topicKeys.append(topicKey)
            category2TopicMap[cat] = topicKeys

DEALSURF_CATEGORY_2_TOPIC_MAP = {}
if len(DEALSURF_CATEGORY_2_TOPIC_MAP)==0:
    _build_category_2_topic_map(TOPIC_2_DEALSURF_CATEGORY_MAP, DEALSURF_CATEGORY_2_TOPIC_MAP)

GROUPON_CATEGORY_2_TOPIC_MAP = {}
GROUPON_CATEGORY_TOPIC_KEYS = set([])
if len(GROUPON_CATEGORY_2_TOPIC_MAP)==0:
    _build_category_2_topic_map(TOPIC_2_GROUPON_CATEGORY_MAP, GROUPON_CATEGORY_2_TOPIC_MAP)
    for topicKeys in GROUPON_CATEGORY_2_TOPIC_MAP.values():
        GROUPON_CATEGORY_TOPIC_KEYS.update(topicKeys)


""" Deal locations """
DEAL_COUNTRIES = set(['us',])
LOCATION_KEY_TOTAL = 'total'
SPECIAL_LOCATIONS = [('all','All'), (LOCATION_KEY_TOTAL,'Total')] 


""" Deal categories """
CATEGORY_2_TOPIC_MAP = GROUPON_CATEGORY_2_TOPIC_MAP
CATEGORY_TOPIC_KEYS = GROUPON_CATEGORY_TOPIC_KEYS
CATEGORY_KEY_TOTAL = 'total'
CATEGORY_KEY_GENERAL = 'general'
SPECIAL_CATEGORIES = [('all','All'), (CATEGORY_KEY_TOTAL,'Total'), (CATEGORY_KEY_GENERAL,'General')]


LOCATION_CATEGORY_KEY_TOTAL = 'total_total'
LOCATION_CATEGORY_KEY_TOTAL_GENERAL = 'total_general'
SPECICAL_KEY_TOKENS = set(['total', 'general'])


DEAL_EXPIRE_CUTOFF_HOURS = 0
