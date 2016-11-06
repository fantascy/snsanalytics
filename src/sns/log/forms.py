from django import forms

from sns.view.baseform import NoNameBaseForm

from api import getBlackList
from sns.log import consts as log_const

class BlackListForm(NoNameBaseForm):
    patternValue=forms.CharField(widget=forms.TextInput(attrs={'size':'100'}),label="Pattern Value",required=False)
    

class DemoUserForm(NoNameBaseForm):
    def __init__( self, *args, **kwargs ):
        super(DemoUserForm, self ).__init__( *args, **kwargs )
        demoList = getBlackList(log_const.PATTERN_DEMO_LIST)
        demos = []
        for demo in demoList:
            demos.append((demo,demo))
        self.fields['demos'] = forms.ChoiceField(choices=demos,widget=forms.Select(
                                   attrs={"id":"demo_user"}),required=True)
        

log_const.GLOBAL_STATS_DISPLAY_LIST = (
             log_const.GLOBAL_STATS_TOTAL_CLICKS,
             log_const.GLOBAL_STATS_TOTAL_POSTS,
             log_const.GLOBAL_STATS_TOTAL_UNIQUE_URLS,
             log_const.GLOBAL_STATS_CMP_CLICKS,
             log_const.GLOBAL_STATS_CMP_POSTS,
             log_const.GLOBAL_STATS_CMP_CLICKED_URLS,
             log_const.GLOBAL_STATS_CMP_FOLLOWERS,
             log_const.GLOBAL_STATS_CMP_TWITTER_ACCTS,
             log_const.GLOBAL_STATS_CMP_ACTIVE_FE_CAMPAIGNS,
             log_const.GLOBAL_STATS_KLOUT_SCORE_100TH,
             log_const.GLOBAL_STATS_KLOUT_SCORE_1000TH,
             log_const.GLOBAL_STATS_TWITTER_SEARCH_RANK_TOP_3,
             log_const.GLOBAL_STATS_TWITTER_SEARCH_RANK_TOP_20,
             ) 


class GlobalStatsForm(NoNameBaseForm):
    type = forms.ChoiceField(choices=log_const.GLOBAL_STATS_DISPLAY_NAME_TUPLE,
            widget=forms.Select(
            attrs={"onchange": "chooseStatsType(this)"}),
            required=True)


class CmpTwitterAcctStatsForm(NoNameBaseForm):
    type = forms.ChoiceField(choices=log_const.CHANNEL_STATS_CHART_CHOICES,
                             widget=forms.Select(attrs={"onchange":"chooseChannelStatsType(this)"}),required=True)
    
    
class ChannelFollowStatsForm(NoNameBaseForm):
    state = forms.ChoiceField(choices=[(-1,"All"),(0,"Inactivated"),(1,"Activated"),(2,"Protected"),(3,"Suspended")],
                              widget=forms.Select(attrs={"id":"follow-state","onchange":"chooseChannelFollowState(this)"}),required=True)
    server = forms.ChoiceField(choices=log_const.FOLLOW_ENGINE_CHOICES,
                               widget=forms.Select(attrs={"id":"follow-server","onchange":"chooseChannelFollowServer(this)"}),required=True)
    priority = forms.ChoiceField(choices=[(-1,"All"),(0,'None'),(1,'P1'),(2,'P2'),(3,'P3')],
                                 widget=forms.Select(attrs={"id":"follow-priority","onchange":"chooseChannelFollowPriority(this)"}),required=True)
    pagination = forms.ChoiceField(choices=[(10,10),(20,20),(50,50)],
                                   widget=forms.Select(attrs={"onchange":"chooseChannelFollowPagination(this)","id":"follow-pagination"}),required=True)
    

class ContentSourceDailyStatsForm(NoNameBaseForm):
    type = forms.ChoiceField(choices=log_const.CS_STATS_CHART_CHOICES,
                             widget=forms.Select(attrs={"onchange":"chooseContentSourceDailyStatsType(this)"}),required=True)
    
    
class TwitterUploadForm(NoNameBaseForm):
    file  = forms.FileField()
