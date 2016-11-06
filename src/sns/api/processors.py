import consts as api_const
from sns.usr.api import UserProcessor,UserClickCounterProcessor
from sns.admin.api import AdminProcessor
from sns.ads.api import AdsProcessor
from sns.feedbuilder.api import FeedBuilderProcessor, TopicScoreFeedBuilderProcessor
from sns.chan.api import TAccountProcessor, FAccountProcessor, FAdminPageProcessor, ChannelClickCounterProcessor, TwitterOAuthTokenProcessor
from sns.cont.api import ContentProcessor, MessageProcessor, FeedProcessor, FeedClickCounterProcessor, BaseFeedProcessor,\
    RawContentProcessor, TopicCSContentProcessor
from sns.cont.topic.api import TopicProcessor
from sns.post.api import StandardCampaignProcessor, MessageCampaignProcessor, FeedCampaignProcessor, QuickMessageCampaignProcessor,\
    SExecutionProcessor, PostProcessor
from sns.url.api import ShortUrlProcessor, UrlClickCounterProcessor, ShortUrlClickCounterProcessor, GlobalUrlProcessor, GlobalUrlCounterProcessor,\
    SiteMapProcessor, WebsiteProcessor
from sns.email.api import EmailListProcessor, EmailContactProcessor, EmailTemplateProcessor, EmailCampaignProcessor, EmailExecutionProcessor
from sns.camp.api import CampaignProcessor, ExecutionProcessor
from sns.log.api import CmpTwitterAcctStatsProcessor
from sns.log.globalstatsapi import GlobalStatsProcessor
from sns.log.hourlystatsapi import HourlyStatsProcessor
from sns.mgmt.api import ContentCampaignProcessor, TopicCampaignProcessor
from sns.deal.api import DealBuilderProcessor
from sns.dm.api import BasicDMCampaignProcessor, AdvancedDMCampaignProcessor
from sns.acctmgmt.api import YahooProcessor, CmpAccountProcessor
from sns.femaster.api import FeMasterProcessor, TargetProcessor as FeMasterTargetProcessor, SourceProcessor as FeMasterSourceProcessor,\
    TopicTargetProcessor as FeMasterTopicTargetProcessor, TopicTargetErrorProcessor as FeMasterTopicTargetErrorProcessor,\
    TgtflwrAllocationLogProcessor, TgtflwrFollowLogProcessor 


API_PROCESSOR_MAP = {
    api_const.API_M_ADMIN                 :AdminProcessor,
    api_const.API_M_ADS                   :AdsProcessor,
    api_const.API_M_CHANNEL               :TAccountProcessor,
    api_const.API_M_FCHANNEL              :FAccountProcessor,
    api_const.API_M_FBPAGE                :FAdminPageProcessor,
    api_const.API_M_TWITTER_OAUTH_TOKEN   :TwitterOAuthTokenProcessor,
    api_const.API_M_MAIL_CONTACT          :EmailContactProcessor,
    api_const.API_M_MAIL_LIST             :EmailListProcessor,
    api_const.API_M_MAIL_TEMPLATE         :EmailTemplateProcessor,
    api_const.API_M_MAIL_CAMPAIGN         :EmailCampaignProcessor,
    api_const.API_M_MAIL_EXECUTION        :EmailExecutionProcessor,
    api_const.API_M_CAMPAIGN              :CampaignProcessor,
    api_const.API_M_CAMPAIGN_RECORD       :ExecutionProcessor,
    api_const.API_M_CONTENT               :ContentProcessor,
    api_const.API_M_ARTICLE               :MessageProcessor,
    api_const.API_M_BASE_FEED             :BaseFeedProcessor,
    api_const.API_M_FEED                  :FeedProcessor,
    api_const.API_M_RAW_CONTENT           :RawContentProcessor,
    api_const.API_M_TOPIC_CS_CONTENT      :TopicCSContentProcessor,
    api_const.API_M_FEED_BUILDER          :FeedBuilderProcessor,
    api_const.API_M_FEED_BUILDER_TOPIC_SCORE            :TopicScoreFeedBuilderProcessor,
    api_const.API_M_FE_MASTER             :FeMasterProcessor,
    api_const.API_M_FE_MASTER_SOURCE      :FeMasterSourceProcessor,
    api_const.API_M_FE_MASTER_TARGET      :FeMasterTargetProcessor,
    api_const.API_M_FE_MASTER_TOPIC_TARGET_ERROR        :FeMasterTopicTargetErrorProcessor,
    api_const.API_M_FE_MASTER_TOPIC_TARGET              :FeMasterTopicTargetProcessor,
    api_const.API_M_FE_MASTER_ALLOC_LOG                 :TgtflwrAllocationLogProcessor,
    api_const.API_M_FE_MASTER_FOLLOW_LOG                :TgtflwrFollowLogProcessor,
    api_const.API_M_POSTING_RULE          :StandardCampaignProcessor,
    api_const.API_M_POSTING_RULE_ARTICLE  :MessageCampaignProcessor,
    api_const.API_M_POSTING_RULE_FEED     :FeedCampaignProcessor,
    api_const.API_M_POSTING_RULE_QUICK    :QuickMessageCampaignProcessor,
    api_const.API_M_POSTING_POSTING       :SExecutionProcessor,
    api_const.API_M_POSTING_POST          :PostProcessor,
    api_const.API_M_URLSHORTENER          :ShortUrlProcessor,
    api_const.API_M_USER                  :UserProcessor,
    api_const.API_M_GLOBAL_URL            :GlobalUrlProcessor,
    api_const.API_M_URL_COUNTER           :UrlClickCounterProcessor,
    api_const.API_M_CHANNEL_COUNTER       :ChannelClickCounterProcessor,
    api_const.API_M_FEED_COUNTER          :FeedClickCounterProcessor,
    api_const.API_M_SURL_COUNTER          :ShortUrlClickCounterProcessor,
    api_const.API_M_USER_COUNTER          :UserClickCounterProcessor,
    api_const.API_M_GLOBAL_COUNTER        :GlobalUrlCounterProcessor,
    api_const.API_M_SITE_MAP              :SiteMapProcessor,
    api_const.API_M_TOPIC                 :TopicProcessor,
    api_const.API_M_WEBSITE               :WebsiteProcessor,
    api_const.API_M_LOG_GLOBAL_STATS      :GlobalStatsProcessor,
    api_const.API_M_LOG_HOURLY_STATS      :HourlyStatsProcessor,
    api_const.API_M_LOG_CMP_TWITTER_STATS :CmpTwitterAcctStatsProcessor,
    api_const.API_M_MGMT                  :ContentCampaignProcessor ,
    api_const.API_M_MGMT_TOPIC            :TopicCampaignProcessor,
    api_const.API_M_DEAL_BUILDER          :DealBuilderProcessor,
    api_const.API_M_DM_RULE               :BasicDMCampaignProcessor,
    api_const.API_M_ADVANCED_DM_RULE      :AdvancedDMCampaignProcessor,
    api_const.API_M_ACCTMGMT_YAHOO        :YahooProcessor,
    api_const.API_M_ACCTMGMT_CMP          :CmpAccountProcessor,
                  }


