# -*- coding: utf-8 -*-

MSG_CAMPAIGN_SCHEDULE_CHOICES_ADMIN = [(0, "now"), (1, "onetime"), (2, "recurring")]
MSG_CAMPAIGN_SCHEDULE_CHOICES = [(0, "now"), (1, "onetime")]

LIMIT_CHANNEL_PER_RULE = 5
LIMIT_CONTENT_PER_RULE = 5
LIMIT_POST_PER_RULE = 125

POSTING_RULE_PER_BATCH = 5

POST_TYPE_FEED = 0
POST_TYPE_MESSAGE = 1
MAX_POSTING_PER_RULE = 100

SCHEDULE_START_MEM_KEY = 'schedulestartkey'


ORIGINAL_URL_DOMAINS = set([
    'hark.com',
                          ])
