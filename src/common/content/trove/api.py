import urllib
import urllib2
import logging
import json
import datetime
import time

from common import consts as common_const
from common.utils import url as url_util
from common.utils import string as str_util
from common.content import pageparser
from common.content.trove import consts as trove_const
from common.content.trove import urlnormalizer as trove_curl_normalizer


V1_API_ROOT = "https://api.trove.com/v1"
V1_API_SEARCH_PATTERN = "%s/search?subscription-key=%s&limit=%d&q=%s"
V1_API_SEARCH_LIMIT = 15
V1_API_URL_PATTERN = "%s/items?subscription-key=%s&url=%s"
#V1_API_URL_PATTERN = "%s/items?key=%s&trim_content=1&trim_user=1&trim_stream=1&url=%s"
V1_API_URL_SHORTENER_ROOT = "http://shorten.trove.com/trove.com/me/content"
V1_API_URL_SHORTENER_PATTERN_WITHOUT_CHID = "http://shorten.trove.com/trove.com/me/content/%s?utm_campaign=%s%%26utm_medium=twitter%%26utm_source=sns"
TROVE_CONTENT_ROOT = "http://trove.com/me/content/"


class TroveItem:
    def __init__(self, trove_id, title, link, updated, published, usage_rights, 
                 description=None, thumbnail=None, full_image=None, curator_id=None, curator_handle=None):
        self.trove_id = trove_id
        self.title = title
        self.link = trove_curl_normalizer.normalize(link)
        self.updated = updated
        self.published = published
        self.usage_rights = usage_rights
        self.description = description
        self.thumbnail = thumbnail
        self.full_image = full_image
        self.curator_id = curator_id
        self.curator_handle = curator_handle
#         self.validate()

    def validate(self):
        if self.updated_time < self.published_time:
            raise Exception("Trove article time stamps are disordered!")
        if self.trove_id and self.title and self.link and self.updated and self.published and self.usage_rights: return
        raise Exception("Missing required attributes for a Trove article!")
        
    def __eq__(self, other):
        if not isinstance(other, self.__class__): return False
        curator_id_v_self = 1 if self.curator_id else 0
        curator_id_v_other = 1 if other.curator_id else 0
        return self.trove_id == other.trove_id \
            and self.title == other.title \
            and self.link == other.link \
            and curator_id_v_self == curator_id_v_other \
            and self.updated == other.updated \
            and self.usage_rights == other.usage_rights
        
    def __hash__(self):
        return hash(self.trove_id)
    
    def __ne__(self, other):
        return not self.__eq__(other)
    
    def __lt__(self, other):
        if other is None: return False
        cmp_usage_rights = cmp(self.usage_rights_weight(), other.usage_rights_weight())
        if cmp_usage_rights != 0: return True if cmp_usage_rights < 0 else False
        cmp_updated = cmp(self.updated, other.updated)
        if cmp_updated != 0: return True if cmp_updated < 0 else False
        curator_id_v_self = 1 if self.curator_id else 0
        curator_id_v_other = 1 if other.curator_id else 0
        if curator_id_v_self != curator_id_v_other: return curator_id_v_self < curator_id_v_other
        cmp_url = cmp(self.link, other.link)
        if cmp_url != 0: return True if cmp_url < 0 else False
        cmp_title = cmp(self.title, other.title)
        if cmp_title != 0: return True if cmp_title < 0 else False
        cmp_trove_id = cmp(self.trove_id, other.trove_id)
        if cmp_trove_id != 0: return True if cmp_trove_id < 0 else False
        return False
    
    def __le__(self, other):
        return self.__eq__(other) or self.__lt__(other)
    
    def __gt__(self, other):
        return not self.__le__(other)
    
    def __ge__(self, other):
        return not self.__lt__(other)
    
    def __unicode__(self):
        return unicode(self.__dict__)
        
    def usage_rights_weight(self):
        return trove_const.USAGE_RIGHTS_MAP.get(self.usage_rights, 0)
        
    @property
    def trove_url(self):
        trove_url = "%s%s" % (TROVE_CONTENT_ROOT, self.trove_id)
        if self.curator_id:
            trove_url = "%s?chid=%s" % (trove_url, self.curator_id)
        return trove_url

    @property
    def is_hosted(self):
        return self.usage_rights == trove_const.USAGE_RIGHTS_FULL

    @property
    def updated_time(self):
        return datetime.datetime.strptime(self.updated, trove_const.DATETIME_FORMAT)

    @property
    def published_time(self):
        return datetime.datetime.strptime(self.published, trove_const.DATETIME_FORMAT)

    @classmethod    
    def text_to_items(cls, text):
        entries = json.loads(text) if text else []
        return [cls(**entry) for entry in entries]
        
    @classmethod    
    def items_to_text(cls, entries):
        json_obj = [entry.__dict__ for entry in entries]
        return json.dumps(json_obj)

    @classmethod    
    def merge_entries(cls, list1, list2):
        diff = set(list1).difference(list2)
        diff.update(list2)
        entries = list(diff)
        entries.sort(reverse=True)
        return entries
    
    @classmethod
    def get_by_item_info(cls, item):
        full_image, thumbnail = cls.get_image_urls(item)
        curator_id, curator_handle = cls.get_curator_info(item)
        return cls(
                trove_id = item.get('id'),
                title = item.get('displayName'),
                link = item.get('url'),
                updated = item.get('updated'),
                published = item.get('published'),
                usage_rights = item.get('usageRights'),
                description = item.get('summary', None),
                thumbnail = thumbnail,
                full_image = full_image,
                curator_id = curator_id,
                curator_handle = curator_handle,
                )

    @classmethod
    def get_by_url(cls, url):
        if not url or is_url_in_unhosted_blacklist(url): return None
        if is_url_in_hosted_whitelist(url) or is_url_in_collection(url, trove_const.VISOR_FRIENDLY_WHITESET):
            retry = 3 
        else:
            retry = 2
        url_info = _fetch_url_mapping_info(url, retry=retry)
        if not url_info: return None
        items = url_info.get('items', None)
        if not items: return None
        return cls.get_by_item_info(items[0])
    
    @classmethod
    def get_image_urls(cls, item):
        try:
            full_image = None
            thumbnail = None
            image_info = item.get('image', None)
            if not image_info: return None, None
            thumbnails = image_info.get('thumbnails', [])
            if thumbnails:
                thumbnail = thumbnails[0].get('url', None)
            full_image_info = image_info.get('fullImage', None)
            if full_image_info:
                full_image = full_image_info.get('url', None)
            if full_image and thumbnail:
                width = full_image_info.get('width')
                height = full_image_info.get('height')
                for thumbnail in thumbnails:
                    if width==thumbnail['width'] and height==thumbnail['height']:
                        full_image = thumbnail['url']
                        break
            return full_image, thumbnail 
        except:
            logging.exception("Unexpected error when resolving images for a Trove item!")
            return None, None
    
    @classmethod
    def get_curator_info(cls, item):
        "Return curator id and Twitter handle"
        try:
            if item and 'picks' in item:
                for pick in item['picks']['picks']:
                    # Skip twitter handle logic
                    curator_handle = None
#                     origin = pick.get('origin', None)
#                     if not origin: continue
#                     provider = origin.get('provider', None)
#                     if provider != 'twitter': continue
#                     actor = pick.get('actor', None)
#                     if not actor: continue
#                     curator_handle = actor.get('twitterHandle', None)
#                     if not curator_handle: continue
                    trove_context = pick.get('context', {})
                    curator_id = trove_context.get('id', None) if trove_context else None
                    return curator_id, curator_handle
#             else:
#                 for stream in item.get('relatedStreams', []):
#                     if stream.has_key('owner'): return stream.get('id', None)
        except:
            logging.exception("Error resolving trove curator info! %s" % item)
        return None, None


def search_by_unnormalized_keywords(unormalized_keywords, limit=V1_API_SEARCH_LIMIT):
    normalized_keywords = normalize_search_keywords(unormalized_keywords)
    return search_by_normalized_keywords(normalized_keywords, limit=limit)


def search_by_normalized_keywords(keywords, limit=V1_API_SEARCH_LIMIT):
    search_url = get_search_url_by_keywords(keywords, limit=limit)
    data = _fetch_api_url(search_url, retry=2)
    if not data or not data.has_key('itemCollection'): return []
    collection = data.get('itemCollection')
    items = collection.get('items', [])
    if len(items) > limit:
        logging.error("Wrong count %s for search %s with limit %d!" % (len(items), keywords, limit))
    entries = []
    for item in items:
        entry = TroveItem.get_by_item_info(item)
        entries.append(entry)
    entries.sort(reverse=True)
    return entries


def search_and_filter(normalized_keywords, contcutoffhours=common_const.CONTENT_CUTOFF_HOURS, limit=V1_API_SEARCH_LIMIT):
    return filter_search_results(search_by_normalized_keywords(normalized_keywords, limit=limit), contcutoffhours=contcutoffhours)

    
def filter_search_results(entries, contcutoffhours=common_const.CONTENT_CUTOFF_HOURS, usage_rights_set=None, skip_blacklist=False):
    filtered = []
    time_cutoff = datetime.datetime.utcnow() - datetime.timedelta(hours=contcutoffhours)
    for entry in entries:
        if entry.updated_time < time_cutoff: continue
        if not skip_blacklist and is_url_in_unhosted_blacklist(entry.link): continue
        if usage_rights_set and not entry.usage_rights in usage_rights_set: continue
        filtered.append(entry)
    return filtered


def get_search_url_by_keywords(keywords, limit=V1_API_SEARCH_LIMIT):
    return V1_API_SEARCH_PATTERN % (V1_API_ROOT, trove_const.API_KEY, limit, keywords)


TROVE_SEARCH_IGNORED_CHARSET = set(['.', ])
def normalize_search_keywords(keywords):
    keywords = str_util.encode_utf8_if_ok(str_util.strip(keywords))
    if not keywords: return None
    chars = []
    leading_comma = False
    for c in keywords:
        if c in TROVE_SEARCH_IGNORED_CHARSET: continue
        if leading_comma and c == ' ': continue
        leading_comma = True if c == ',' else False
        if c == '/': c = '|'
        chars.append(c)
    normalized = ''.join(chars)
    while normalized.find('  ') != -1:
        normalized = normalized.replace('  ', ' ')
    return urllib.quote_plus(_handle_search_keywords_operator_or(normalized)) 


def _handle_search_keywords_operator_or(keywords):
    return ' '.join([_double_quote_search_keywords(k) for k in keywords.split('|')])
 

def _double_quote_search_keywords(keywords):
    keywords = str_util.strip(keywords)
    words = keywords.split(' ')
    if len(words) == 1:
        return words[0]
    else:
        return '"%s"' % keywords
    
 
def get_v1_api_item(url):
    url = trove_curl_normalizer.normalize(url)
    return V1_API_URL_PATTERN % (V1_API_ROOT, trove_const.API_KEY, url)


def get_mention_str(mention_type, mention_handle):
    if not mention_handle or not mention_type: return None
    if mention_type == trove_const.MENTION_PICKER:
        return "via @%s" % mention_handle
    elif mention_type == trove_const.MENTION_TROVE:
        return "via @trove"
    else:
        return "via @%s @trove" % mention_handle


def get_utm_content(mention_type=trove_const.MENTION_NONE):
    return trove_const.MENTION_TYPE_MAP.get(mention_type, None)


def get_utm_params(hosted, mention_type=trove_const.MENTION_NONE):
    camp = trove_const.UTM_CAMPAIGN_HOSTED if hosted else trove_const.UTM_CAMPAIGN_UNHOSTED
    params = dict(utm_source=trove_const.UTM_SOURCE, utm_medium=trove_const.UTM_MEDIUM, utm_campaign=camp)
    utm_content = get_utm_content(mention_type)
    if utm_content:
        params['utm_content'] = utm_content
    return params


def get_trove_url_with_utm(url, mention_type=trove_const.MENTION_NONE):
    trove_item = TroveItem.get_by_url(url)
    if not trove_item: return url
    utm_params = get_utm_params(trove_item.is_hosted, mention_type)
    return url_util.add_params_2_url(trove_item.trove_url, utm_params)
    
    
def get_trove_short_url(trove_url, add_timestamp=False):
    if not trove_url.startswith(TROVE_CONTENT_ROOT):
        logging.error("Trying to shorten a non Trove URL! %s" % trove_url)
        return None
    no_param_url = url_util.remove_all_params(trove_url)
    trove_url_hash = no_param_url[len(TROVE_CONTENT_ROOT):]
    params = url_util.get_params(trove_url)
    if not params.has_key('utm_campaign') or not params.has_key('utm_source') or not params.has_key('utm_medium'):
        logging.error("Trying to shorten a Trove URL without UTM params! %s" % trove_url)
        return None
    shortener_url = V1_API_URL_SHORTENER_PATTERN_WITHOUT_CHID % (trove_url_hash, params.get('utm_campaign'))
    if params.has_key('chid'):
        shortener_url = shortener_url + '%26chid=' + params.get('chid')
    if add_timestamp:
        shortener_url = shortener_url + '%26ts=' + str(int(time.time()))
    short_url_info = fetch_short_url_info(shortener_url)
    short_url = None
    if short_url_info:
        data = short_url_info.get('data', None)
        if data:
            short_url = data.get('url', None)
    if not short_url:
        logging.error("Failed Trove shortener! %s" % shortener_url)
        return None
    return short_url
    

def is_trove_url_hosted(trove_url):
    if not trove_url: return False
    params = url_util.get_params(trove_url)
    if params and params.get('utm_campaign')==trove_const.UTM_CAMPAIGN_HOSTED: return True
    return False
    
    
def are_urls_equivalent(url1, url2):
    try:
        url1 = trove_curl_normalizer.normalize(url1)
        url2 = trove_curl_normalizer.normalize(url2)
        if url1 == url2: return True
        if not url1 or not url2: return False
        if not is_url_in_non_redirect_whitelist(url1):
            url1_info = url_util.fetch_redirect_url(url1, retry=1)
            url1 = url1_info.actualUrl(ignore_error=True)
            if url1 == url2: return True
            url1_parser = pageparser.SPageParser()
            url1_parser.feed(url1_info.content)
            if url1_parser.og_url: url1 = url1_parser.og_url
            if url1 == url2: return True
        if not is_url_in_non_redirect_whitelist(url2):
            url2_info = url_util.fetch_redirect_url(url2, retry=1)
            url2 = url2_info.actualUrl(ignore_error=True)
            if url1 == url2: return True
            url2_parser = pageparser.SPageParser()
            url2_parser.feed(url2_info.content)
            if url1 == url2_parser.og_url: return True
        return False
    except:
        logging.exception("Error when comparing URL equivalence! %s %s" % (url1, url2))
        return False

    
def is_url_eligible_for_visor(url, is_iphone=True, is_phone=True):
    if is_iphone and not is_phone:
        logging.exception("Wrong context is_iphone is true while is_phone is false!")
    domain = url_util.full_domain_excluding_www(url)
    if domain in trove_const.VISOR_FRIENDLY_WHITESET: return True
    if is_iphone:
        blacklist = trove_const.VISOR_IPHONE_UNFRIENDLY_BLACKSET
    elif is_phone:
        blacklist = trove_const.VISOR_PHONE_UNFRIENDLY_BLACKSET
    else:
        blacklist = trove_const.VISOR_UNFRIENDLY_BLACKSET
    if is_subdomain_in_collection(domain, blacklist): return False
    if is_subdomain_in_collection(domain, trove_const.VISOR_FRIENDLY_WHITESET): return True
    return not is_iphone


def is_url_in_unhosted_blacklist(url):
    domain = url_util.full_domain_excluding_www(url)
    return is_subdomain_in_collection(domain, trove_const.VISOR_UNFRIENDLY_BLACKSET)


def is_url_in_correctness_validation_whitelist(url):
    domain = url_util.root_domain(url)
    return domain in trove_const.URL_CORRECTNESS_VALIDATION_WHITESET


def is_url_in_non_redirect_whitelist(url):
    domain = url_util.root_domain(url)
    return domain in trove_const.NON_REDIRECT_WHITESET


def is_url_in_hosted_whitelist(url):
    domain = url_util.root_domain(url)
    return domain in trove_const.HOSTED_WHITESET


def is_url_in_visor_possibly_friendly_whitelist(url):
    domain = url_util.root_domain(url)
    return domain in trove_const.VISOR_POSSIBLY_FRIENDLY_WHITESET


def is_url_in_ingested_whitelist(url):
    return is_url_in_hosted_whitelist(url) or is_url_in_visor_possibly_friendly_whitelist(url)


def is_url_in_collection(url, collection):
    return is_subdomain_in_collection(url_util.full_domain(url), collection)


def is_subdomain_in_collection(domain, collection):
    tokens = domain.split('.')
    for i in range(len(tokens)):
        subdomain = '.'.join(tokens[i:])
        subdomain = str_util.lower_strip(subdomain)
        if subdomain in collection: return True
    return False


def _fetch_url_mapping_info(url, retry=1):
    return _fetch_api_url(get_v1_api_item(url), retry=retry)


def _fetch_api_url(api_url, retry=1):
    retried = 0
    while retry:
        try:
            retried += 1
            info = None
            headers = {'User-Agent': trove_const.USER_AGENT}
            req = urllib2.Request(api_url, headers=headers)
            usock = urllib2.urlopen(req)
            info = usock.read()
            return json.loads(info)
        except Exception:
            if retry == 1: logging.exception("Trove API error mapping url after %d times! %s"  % (retried, api_url))
        retry -= 1
    return None


def fetch_short_url_info(shortener_url, retry=3):
    while retry:
        try:
            info = None
            headers = {'User-Agent': trove_const.USER_AGENT}
            req = urllib2.Request(shortener_url, headers=headers)
            usock = urllib2.urlopen(req)
            info = usock.read()
            return json.loads(info)
        except Exception:
            if retry == 1: logging.exception("Trove URL Shortener error! %s"  % shortener_url)
        retry -= 1
    return None


def is_topic_key_in_blacklist(topic_key):
    return topic_key in trove_const.TOPIC_KEY_BLACKSET



