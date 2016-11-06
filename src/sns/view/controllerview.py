from google.appengine.api import users

import conf
from common.view.controllerview import ControllerView as CommonControllerView
from sns.log.consts import PATTERN_GA_LIST, PATTERN_DOS_LIST, PATTERN_AD_SITE, PATTERN_FRAME_SITE, PATTERN_REDIRECT_USER


class ControllerView(CommonControllerView):
    def __init__(self, viewName=None, pageTitle=None, request=None):
        CommonControllerView.__init__(self)
        self.raise_error_if_no_login()
        self.navigation = self.getMenu()
        if viewName:
            self.viewName = viewName
        else:
            self.viewName = "Home"
        if pageTitle:
            self.pageTitle = pageTitle
        else:
            self.pageTitle = "SNS Analytics - Largest Publisher on Twitter."

    def getMenu(self):
        return self.get_menu()
        
    def get_menu(self):
        cls = self.__class__
        if users.is_current_user_admin():
            menus = [cls.CHANNEL_TAB, 
                    cls.MESSAGE_CAMAPAIGN_TAB, 
                    cls.ADMIN_FEED_CAMAPAIGN_TAB, 
                    cls.MAIL_TAB, 
                    cls.DM_TAB, 
                    cls.REPORT_TAB, 
                    cls.CMP_TAB, 
                    cls.SYSTEM_TAB,
                    ]
            if conf.EXTRA_FEATURES: menus.append(cls.DEAL_TAB)
        else:
            menus = [cls.CHANNEL_TAB, 
                    cls.MESSAGE_CAMAPAIGN_TAB, 
                    cls.FEED_CAMAPAIGN_TAB, 
                    cls.REPORT_TAB, 
                    ] 
        return menus
    
    CHANNEL_TAB = ("Social Channels" , None,   [
                        ("Twitter Accounts", "/chan/"),
                        ("Twitter Conversations","/chan/conversation/"),
                        ("Facebook Accounts","/chan/facebook/"),
                        ("FB Pages (Admin)","/chan/fbpage/"),
                        ("FB Pages (Fan)","/chan/fanpage/"),
                        ("FB Groups","/chan/groupmember/"),
                            ])
    
    MESSAGE_CAMAPAIGN_TAB = ("Scheduled Messages", None,    [ 
                                ("Messages", "/message/"),  
                                ("Schedules", "/post/rule/article/"),  
                                    ])

    FEED_CAMAPAIGN_TAB = ("Feed Campaigns", None,  [
                                ("Feeds", "/rssfeed/"),
                                ("Feed Campaigns", "/post/rule/feed/"),
                                    ])
    
    ADMIN_FEED_CAMAPAIGN_TAB = ("Feed Campaigns", None,  [
                                ("Feeds", "/rssfeed/"),
                                ("Feed Builders", "/feedbuilder/"),
                                ("Feed Campaigns", "/post/rule/feed/"),
                                    ])
    
    CUSTOM_CAMPAIGN_TAB = ("Custom Campaigns", None,  [
                                ("Custom Campaigns", "/cust/rule/"),
                                ("Custom Links", "/cust/linking/"),
                                    ])

    REPORT_TAB = ("Reports", None, [
                                ("Click-through Charts", "/graph/chart"),           
                                ("Click-through Ranks", "/graph/clickranking"),
                                ("Quick Post Records", "/graph/quickpost/record"),
                                ("Post Failures", "/graph/postfailurelist"),
                                    ])

    MAIL_TAB = ("Mail Campaigns", None,   [
                                ("Mail Lists", "/email/list/"),
                                ("Mail Templates", "/email/template/"),
                                ("Mail Campaigns", "/email/campaign/"),
                                    ])  
    
    DM_TAB = ("DM Campaigns", None,   [
                                ("Basic DMs","/dm/rule/"),
                                ("Advanced DMs","/dm/rule/advanced/"),
                                ("All Basic DMs","/dm/all/rule/list/"),
                                    ])                         
    
    DEAL_TAB = ("Deals", None,   [
                                ("Deal Feeds","/deal/"),
                                ("Deal Stats","/deal/stats/"),
                                    ])                         
    
    cmp_menu = [
        ("CMP Campaigns","/mgmt/"),
        ("CMP Users ", "/usr/?type=2"),
        ("CMP Feeds","/rssfeed/custom/"),
        ("CMP Acct Click Stats", "/log/channelstats/?orderby=latelyclick&type=desc"),
        ("CMP Acct TSEO Stats", "/log/channelstats/tseo/?orderby=retweets&type=desc"),
        ("CMP Acct CS Stats", "/log/csstats/?orderby=clicks&type=desc"),
        ("CMP Acct Upload", "/acctmgmt/cmp/upload/"),
        ("Topics w/o Twitter Acct", "/mgmt/topic/nochannel/"),
        ("Twitter Accts w/o Topic", "/mgmt/topic/notopic/"),
        ]                
    if conf.EXTRA_FEATURES: cmp_menu.extend([
        ("CMP Acct FE Stats", "/log/channelstats/fe/"),
        ("Topic Campaigns", "/mgmt/topic/"),
        ])
    CMP_TAB = ("CMP", None, cmp_menu)
    
    system_menu = [
        ("System Stats","/log/stats/?type=-1"),
        ("Topics","/sns/topic/list/"),
        ("Users", "/usr/"),
        ]
    if conf.EXTRA_FEATURES: system_menu.extend([
        ("System Settings", "/log/system/setting/"),
        ("GA Blacklist", "/log/blacklist/?botType="+PATTERN_GA_LIST),
        ("DOS Blacklist", "/log/blacklist/?botType="+PATTERN_DOS_LIST),
        ("Ads Blacklist", "/log/blacklist/?botType="+PATTERN_AD_SITE), 
        ("IFRAME Blacklist", "/log/blacklist/?botType="+PATTERN_FRAME_SITE), 
        ("RippleOne Users", "/log/blacklist/?botType="+PATTERN_REDIRECT_USER), 
        ("Content Sources","/url/website/list/"),
        ("Suspended by Twitter", "/chan/twitter/suspended"),
        ("Restored by Twitter", "/chan/twitter/restored"),
        ("Twitter Profiles", "/log/twitter/upload/"),
        ("Seed Accounts", "/acctmgmt/"),
        ])                      
    SYSTEM_TAB = ("System", None, system_menu)
