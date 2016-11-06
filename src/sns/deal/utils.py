import urllib
import logging
import datetime
import math

from common.utils import url as url_util, string as str_util
from common.utils import timezone as ctz_util
from common.utils import datetimeparser
from common.content import pageparser
from common.content import feedfetcher
from sns.deal import consts as deal_const


class DealSource():
    def __init__(self, key, name, affiliation):
        self.key = key
        self.name = name
        self.affiliation = affiliation
    
    @classmethod
    def get_by_key(cls, key):
        if key is None :
            return None
        source = deal_const.DEAL_SOURCE_MAP.get(key, None)
        if source is None :
            return DealSource(key, None, None)
        else :
            return DealSource(key, source[0], source[1])


class Deal():
    def __init__(self, url=None, title=None, sourceKey=None, price=None, bought=None, expireTime=None, national=False, cats=[]):
        self.url = url
        self.title = str_util.strip_one_line(title)
        self.sourceKey = sourceKey
        self.price = price
        self.bought = bought
        self.national = national
        self.expireTime = expireTime
        if cats is not None or type(cats)!=list :
            self.cats = cats
        else :
            self.cats = []
    
    def addAffInfo2Url(self):
        self.url = DealUrlHandler(self.sourceKey).handle(self.url)

    def source(self):
        return DealSource.get_by_key(self.sourceKey)
        
    def affiliated(self):
        return affiliated(self.sourceKey) 
    
    def is_expiring(self, now=datetime.datetime.utcnow()):
        if self.expireTime:
            return datetimeparser.timedelta_in_hours(self.expireTime - now) <= deal_const.DEAL_EXPIRE_CUTOFF_HOURS
        else:
            return False 
    
    @classmethod
    def get_affiliated_deals(cls, deals):
        affiliated = []
        for deal in deals :
            if deal.affiliated() :
                affiliated.append(deal)
        return affiliated
    
    def isEligible(self):
        if self.expireTime is None :
            return False
        return self.expireTime > datetime.datetime.utcnow() + datetime.timedelta(days=1)
    
    def rank(self):
        OPTIMAL_PRICE = 5000
        if self.price is None or self.price <= 0 or self.bought is None or self.bought <= 1:
            return 0
        volume_weight = math.log(self.bought)
        price_weight = OPTIMAL_PRICE * math.log(self.price, OPTIMAL_PRICE) if self.price > OPTIMAL_PRICE else self.price
        return int(price_weight * volume_weight)
    
    @classmethod
    def sort(cls, deals):
        deals.sort(lambda x,y: cmp(x.rank(), y.rank()), reverse=True)
        return deals

    @classmethod
    def dedupe_sort(cls, deals):
        """ New deal info should be put in front of old deal info. """
        dealMap = {}
        for deal in deals:
            if dealMap.has_key(deal.title):
                continue
            dealMap[deal.title] = deal
        return cls.sort(dealMap.values())

    @classmethod
    def filter_expiring(cls, deals):
        if deals: 
            now = datetime.datetime.utcnow()
            return filter(lambda x: not x.is_expiring(now=now), deals)
        else:
            return []

    def text(self):
        return unicode({
                    'url': self.url,
                    'title': self.title,
                    'sourceKey': self.sourceKey,
                    'price': self.price,
                    'bought': self.bought,
                    'expireTime': self.expireTime,
                    })
    

def aff_program(dealSourceKey):
    if dealSourceKey is None :
        return None
    sourceInfo = deal_const.DEAL_SOURCE_MAP.get(dealSourceKey, None)
    if sourceInfo is None :
        return None
    return sourceInfo[1]


def affiliated(dealSourceKey):
    aff = aff_program(dealSourceKey)
    return aff is not None


class DealUrlHandler:
    def __init__(self, sourceKey):
        self.sourceKey = sourceKey

    def handle(self, url):
        clazz = self.__class__
        handlerName = clazz.handler_name(self.sourceKey)
        if hasattr(clazz, handlerName) :
            url = getattr(clazz, handlerName)(url)
        return clazz.handle_aff(url, self.sourceKey)

    @classmethod
    def handler_name(cls, sourceKey):
        return "handle_%s" % sourceKey.lower()

    @classmethod
    def has_handler(cls, sourceKey):
        return hasattr(cls, cls.handler_name(sourceKey))
    
    @classmethod
    def handle_aff(cls, url, sourceKey):
        affProgram = aff_program(sourceKey)
        if affProgram is None :
            return url
        if affProgram==deal_const.AFF_CJ :
            return cls.handle_cj(url)
        if deal_const.AFF_ID_URL_PARAMS.has_key(affProgram) :
            return url_util.add_params_2_url(url, deal_const.AFF_ID_URL_PARAMS[affProgram])
        return url

    @classmethod
    def handle_cj(cls, url):
        return "http://www.anrdoezrs.net/click-%s-10804307?%s" % (deal_const.AFF_ID_CJ, urllib.urlencode({"url":url}))

    @classmethod
    def cj_twitter_2_mobile(cls, url):
        return url.replace(deal_const.AFF_ID_CJ_TWITTER, deal_const.AFF_ID_CJ_MOBILE)

    @classmethod
    def handle_crowdsavings(cls, url):
        return url_util.remove_all_params(url)

    @classmethod
    def handle_dealon(cls, url):
        return url
    
    @classmethod
    def handle_zozi(cls, url):
        return url_util.remove_all_params(url)

    @classmethod
    def handle_tippr(cls, url):
        if url.startswith("http://jump.tippr.com/") :
            offerParam = url_util.get_param(url, 'params', decode=True)
            if offerParam.find('%3D')!=-1 :
                offer = url_util.urldecode(offerParam).split('=', 2)[1]
            else :
                offer = offerParam.split('=', 2)[1]
        else :
            offer = url.split('/offer/')[1].split('/')[0]
        return "http://jump.tippr.com/aff_c?offer_id=2&aff_id=1309&params=%2526offer%253D" + offer
    
    @classmethod
    def handle_dealster(cls, url):
        return cls._handle_redirect(url)
    
    @classmethod
    def handle_plumdistrict(cls, url):
        return cls._handle_redirect(url, param='redirect')
    
    @classmethod
    def handle_saveology(cls, url):
        return cls._handle_redirect(url)
    
    @classmethod
    def _handle_redirect(cls, url, param='url'):
        redirect = url_util.urldecode(url_util.get_param(url, param, decode=True))
        if redirect is not None :
            return redirect
        else :
            return url
    

class DealSurfUrlHandler(DealUrlHandler):
    @classmethod
    def handle_dealon(cls, url):
        return url.replace("dealsurf.dealon.com", "www.dealon.com")


def is_on_dealsurf(dealSourceKey):
    if dealSourceKey is None :
        return False
    sourceInfo = deal_const.DEAL_SOURCE_MAP.get(dealSourceKey, None)
    if sourceInfo is None :
        return False
    return sourceInfo[2]
    

class DealSurfPageParser(pageparser.SPageParser):
    def reset(self):
        pageparser.SPageParser.reset(self)
        self.isDealsurf = False
        self.dealUrl = None
        
    def start_div(self, attrs):
        for k, v in attrs:
            k = k.strip()
            v = v.strip()
            if k == 'style' and v == 'font-size: 9px;margin-top: 5px':
                self.isDealsurf = True
                
    def end_div(self):
        self.isDealsurf = False
        
    def start_a(self, attrs):
        if self.isDealsurf:
            for k, v in attrs:
                if k.strip() == "onclick":
                    try:
                        v = v.strip()
                        dealUrl = v[v.index('(')+1:v.index(')')].replace('"','')
                        if url_util.is_valid_url(dealUrl):
                            self.dealUrl = dealUrl
                    except Exception, ex:
                        logging.info("Skipped a dealsurf deal on parsing error: %s" % str(ex))


class DealFeedEntry(feedfetcher.FeedEntry):
    def __init__(self, feid, feed_fetcher=None, oe=None, url=None, title=None, keywords=[], updated=None, summary=None, extra={}):
        feedfetcher.FeedEntry.__init__(self, feid, feed_fetcher=feed_fetcher, oe=oe, url=url, title=title, keywords=keywords, updated=updated, summary=summary, extra=extra)
        self.deal_location_category = None


class DealFeedUtilFetcher(feedfetcher.DynamicFeedFetcher):
    DEAL_FEED_STUB = '/deal/rss/'
    REPEAT_TIMES_BY_RANK = ((2, 10), )
    REPEAT_TIMES_BY_COUNT = ((2, 5), )
    REPEAT_INTERVALS_BY_COUNT = ((10, 10), (5, 5), (2, 2))

    @classmethod
    def entry_model(cls):
        return DealFeedEntry
    
    @classmethod
    def max_history(cls):
        return 50
    
    def ads_on(self):
        return False 
    
    @classmethod
    def is_deal_feed(cls, url):
        return url.find(cls.DEAL_FEED_STUB) != -1

    @classmethod
    def entry_to_deal(cls, entry):
        try:
            title = entry.title
            url = entry.link
            summary = entry.summary
            if summary:
                details = eval(summary)
                return Deal(url=url, 
                            title=title,
                            sourceKey=details['sourceKey'],
                            price=details['price'],
                            bought=details['bought'],
                            )
            else:
                return Deal(url=url, title=title)
                pass
        except:
            logging.exception("Error parsing deal feed entry to deal:")
            return None

    def get_location_category_tuple(self):
        if self.urlFileStreamOrString is None:
            return None, None
        tokens = self.urlFileStreamOrString.split('/')
        if len(tokens[-1]) == 0:
            tokens = tokens[:-1]
        if len(tokens) < 3:
            return None, None
        if tokens[-2] == 'rss':
            return tokens[-1], deal_const.CATEGORY_KEY_GENERAL
        else:
            return tokens[-2], tokens[-1]

    def get_location_category_str(self):
        location, category = self.get_location_category_tuple()
        if location and category:
            return "%s_%s" % (location, category)
        else:
            return None
        
    def get_location(self):
        return self.get_location_category_tuple()[0]

    def extra_fetch_limit(self):
        return 50

    def predefined_top_deal(self):
        pass
    
    def execute_fetch(self):
        predefined_top_deal = self.predefined_top_deal()
        deals = [predefined_top_deal] if predefined_top_deal else [] 
        deals.extend([self.__class__.entry_to_deal(entry) for entry in self.parser.entries])
        dealMap = dict([(deal.title, deal) for deal in deals])
        feidSet = set(dealMap.keys())
        if len(feidSet)==0 :
            return []
        historyCountMap = {}
        for feid in self.feid_history:
            count = historyCountMap.get(feid, 0)
            count += 1
            historyCountMap[feid] = count 
        now = ctz_util.uspacificnow()
        hourRank = self.HOUR_RANKS[now.hour]
        index = 0
        offset = int(self.limit*60.0/self.freq*(hourRank-1))
        dealCount = len(deals)
        dealInterval = self.repeat_interval(dealCount)
        logging.debug("deal_fetch: now=%s; hourRank=%s; offset=%s; dealCount=%s; dealInterval=%s" % (now, hourRank, offset, dealCount, dealInterval))
        logging.debug("deal_fetch: feed=%s; len(history)=%s" % (self.urlFileStreamOrString, len(self.feid_history)))
        if dealInterval:
            recentlyPosted = self.feid_history[-(dealInterval-1):]
        else:
            recentlyPosted = self.feid_history
        dealIndex = -1
        dealRank = 0
        results = []
        for deal in deals:
            dealIndex += 1 
            dealRank += 1
            repeatTimes = self.entry_repeat_times(dealRank, dealCount)
            index += repeatTimes
            if index<offset or historyCountMap.get(deal.title, 0)>=repeatTimes or deal.title in recentlyPosted:
                continue
            results.append(dealIndex)
            logging.debug("deal_fetch: dealIndex=%d; index=%d; repeatTimes=%d; deal=%s" % (dealIndex, index, repeatTimes, deal.text()))
            if len(results)>=self.limit:
                break
        entries = []
        for result in results:
            deal = deals[result]
            self.append_history(deal.title, deal.url)
            entry = DealFeedEntry(deal.title, feed_fetcher=self)
            entry.url = deal.url 
            entry.title = deal.title
            if result == 0:
                entry.deal_location_category = self.get_location_category_str()   
            entries.append(entry)
        return entries


def main():
    print DealSurfUrlHandler(deal_const.DEAL_SOURCE_PLUMDISTRICT).handle("http://gan.doubleclick.net/gan_click?lid=41000000032568685&pubid=21000000000291686&mid=4ed25258bda18368601625&redirect=http%3A%2F%2Fwww.plumdistrict.com%2Fmoms%2Fdiscount%2Feverywhere%2Fhome-and-garden-deals%2Fdiscount-mags-plum-steal-10-for-issues-of-better-homes-gardens-ladies-home-journa-ACjqDJ%3Fsub%3Dtrue")
    print DealFeedUtilFetcher.repeat_interval(1)
    print DealFeedUtilFetcher.repeat_interval(3)
    print DealFeedUtilFetcher.repeat_interval(5)
    print DealFeedUtilFetcher.repeat_interval(7)
    print DealFeedUtilFetcher.entry_repeat_times(1, 1)
    print DealFeedUtilFetcher.entry_repeat_times(2, 2)
    print DealFeedUtilFetcher.entry_repeat_times(3, 3)
    print DealFeedUtilFetcher.entry_repeat_times(4, 4)
    print DealFeedUtilFetcher.entry_repeat_times(5, 5)
    print DealFeedUtilFetcher.entry_repeat_times(6, 20)
    print DealFeedUtilFetcher.entry_repeat_times(10, 20)
    print DealFeedUtilFetcher.entry_repeat_times(11, 20)

    url = "http://www.dpbolvw.net/click-5517529-10795773"
    parser = pageparser.SPageParser.get_prepared_parser(url) 
    print url, parser.get_title()
    

if __name__=='__main__':
    main()
    