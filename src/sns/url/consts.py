SHORT_URL_GENERATOR_CURSOR_START = 2383280
HASH_MAPPING = [        '0', '1', '2', '3', '4', '5', '6', '7', '8', '9',
                        'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 
                        'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 
                        'U', 'V', 'W', 'X', 'Y', 'Z', 'a', 'b', 'c', 'd', 
                        'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 
                        'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x',
                        'y', 'z'    ]
"""
The whole purpose is to make url hash result in a unique but less detectable pattern.
"""
HASH_INDEX_DELTA=(0,11, 29, 37, 59, 7)
URLHASH_TYPE_POST = 0
URLHASH_TYPE_MAIL = 1
URLHASH_TYPE_DM = 2
URLHASH_TYPE_CUSTOM = 3
URLHASH_TYPES = (URLHASH_TYPE_POST, URLHASH_TYPE_MAIL, URLHASH_TYPE_DM, URLHASH_TYPE_CUSTOM)


SUPER_LONG_URL_GLOBAL_PARENT = "superlongurl"


USER_URL_CLICK_COUNTER_HASH_SIZE = 100
GLOBAL_URL_FIRST_LEVEL_SIZE = 1000
GLOBAL_URL_SECOND_LEVEL_SIZE = 1000
GLOBAL_URL_SIZE_LIMIT = 10000
GLOBAL_URL_THUMBNAIL_URL = "http://%s.s3-website-us-west-1.amazonaws.com/%s.png"


RAW_CLICK_PARENT_NUMBER = 10
RAW_CLICK_HASH_SIZE = 10
RAW_CLICK_CACHE_MINUTES = 180


SITE_MAP_HASH_SIZE = 10


BLACKLISTED_URL_HASHS = set([
    "3Oo3y9",
    "Omfty2",
    "O8ipy7",
    "OFh9y0",
    "OfhJy2",
    "6qA4y6",
    "7Rssy4",
    "OAmky3",
    "OOmmy4",
    "ObnYy7",
    "YJkky4",
    "19jyy1",
    "Fmkey2",
    "blZry9",
    "bvWUy5",
    "kFmry2",
    "knmhy4",
    "OOmVy8",
    "pWzWy4",
    ])

