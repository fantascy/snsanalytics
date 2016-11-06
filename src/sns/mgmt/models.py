from google.appengine.ext import db

from common.utils import string as str_util
from sns.core.base import SoftDeleteNamedBaseModel
from sns.camp import consts as camp_const
from sns.mgmt import consts as mgmt_const
from sns.cont import utils as cont_util
from sns.cont.feedsources import FeedSource
from sns.camp.models import GACampaignIF

class ContentCampaign(SoftDeleteNamedBaseModel, GACampaignIF):
    scheduleInterval = db.StringProperty(choices=camp_const.SCHEDULE_FEED_POSTING_INTERVALS)
    randomize = db.BooleanProperty()
    randomizeTimeWindow = db.IntegerProperty() 
    maxMessagePerFeed = db.IntegerProperty(default=1, choices=[1, 2, 3, 4, 5])    
    filterType = db.IntegerProperty(default=mgmt_const.CMP_RULE_FILTER_TYPE_EXCLUDED_USER)
    filters = db.TextProperty()
    includedTags = db.TextProperty()
    excludedTags = db.TextProperty()
    feedSources = db.ListProperty(int)
    priority = db.IntegerProperty()
    syncState = db.IntegerProperty(default=mgmt_const.CMP_RULE_STATE_NORMAL)
    
    @classmethod
    def camp_attrs(cls):
        attrs = ['scheduleInterval', 'randomize', 'randomizeTimeWindow', 'maxMessagePerFeed']
        attrs.extend(cls.ga_attrs())
        return attrs
    
    def get_fsid(self):
        return self.feedSources[0]

    def getFeedInfo(self, topics):
        fsid = self.get_fsid()
        return fsid, FeedSource(fsid).get_feed_by_topic_names(topics)
    
    def getTopicNumber(self):
        return cont_util.get_topic_number_by_fsid(self.get_fsid())

    def first_included_tag(self):
        tags = self.includedTags.split(',') if self.includedTags else []
        return str_util.lower_strip(tags[0]) if tags else None
    
    def including_tag(self, tag):
        tags = self.includedTags.split(',') if self.includedTags else []
        if tags and tag in tags: return True
        return False
    
    def excluding_tag(self, tag):
        tags = self.excludedTags.split(',') if self.excludedTags else []
        if tags and tag in tags: return True
        return False
    
    
class TopicContentCampaign(SoftDeleteNamedBaseModel):
    scheduleInterval = db.StringProperty(choices=camp_const.SCHEDULE_ARTICLE_POSTING_INTERVALS)
    maxMessagePerFeed = db.IntegerProperty(default=1, choices=[1, 2, 3, 4, 5])   
    feedSources = db.ListProperty(int)
    scheduleNext = db.DateTimeProperty()
    state = db.IntegerProperty(default=camp_const.CAMPAIGN_STATE_ACTIVATED, choices=camp_const.CAMPAIGN_STATES, required=True)
    
    def getScheduleType(self):
        return camp_const.SCHEDULE_TYPE_RECURRING 
    