from common.utils import url as url_util
from common.content import feedfetcher
from sns.cont import consts as cont_const


def get_topic_number_by_fsid(fsid):
    return cont_const.FEED_SOURCE_TOPIC_NUMBER_MAP.get(fsid, 1)


class ContentItem:
    def __init__(self, params):
        self.url = params.get('url', None)        
        self.title = params.get('title', None)
        self.keywords = params.get('keywords', [])        
        self.description = params.get('description', None)
        self.publish_date = params.get('publish_date', None)        

    def to_dict(self):
        return {
                'url': self.url,
                'title': self.title,
                'keywords': self.keywords,
                'description': self.description,
                'publish_date': self.publish_date,
                }
        
    @classmethod
    def sort(cls, items):
        items.sort(lambda x,y: cmp(x.publish_date, y.publish_date), reverse=True)
        return items

    @classmethod
    def merge_sort(cls, old_items, new_items):
        items_map = dict([(item.url, item) for item in old_items])
        for new_item in new_items:
            items_map[new_item.url] = new_item
        items = items_map.values()
        return cls.sort(items) 


class FeedCrawlerJob:
    def __init__(self, cskey, feed_url, keywords=[]):
        self.cskey = cskey
        self.feed_url = feed_url
        self.keywords = keywords

    def __str__(self):
        return "(%d, %s, [%s]" % (self.cskey, self.feed_url, ', '.join(self.keywords))


class FeedCrawlerFeedEntry(feedfetcher.FeedEntry):
    @classmethod
    def preprocess_url_wo_fetch(cls, url):
        return url_util.remove_analytics_params(url)


class FeedCrawlerFeedFetcher(feedfetcher.DynamicFeedFetcher):
    FETCH_LIMIT = 200
    def __init__(self, urlFileStreamOrString, parseFeedUrlFromPage=False):
        feedfetcher.DynamicFeedFetcher.__init__(self, urlFileStreamOrString, parseFeedUrlFromPage=parseFeedUrlFromPage)

    @classmethod
    def entry_model(cls):
        return FeedCrawlerFeedEntry
        
    @classmethod
    def max_history(cls):
        return 500
    
    @classmethod
    def fetch_content_by_default(cls):
        return True

    def extra_fetch_limit(self):
        return 100

    def entry_domain_always_diff(self):
        return False
    
    def on_blacklist(self, url):
        return False


    
    
