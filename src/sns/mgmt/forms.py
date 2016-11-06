from django import forms
from sns.view.baseform import BaseForm, NoNameBaseForm
from sns.mgmt import consts as mgmt_const
from sns.camp import consts as camp_const
from sns.api import consts as api_const
from sns.cont import consts as cont_const

class ContentCampaignForm(BaseForm):
    gaOn=forms.BooleanField(widget=forms.CheckboxInput(attrs={'class':'retro analyticsCheck','onclick':'toggleAnalytics(this)'}),
                                   required=False)
    gaUseCampaignName=forms.BooleanField(widget=forms.CheckboxInput(attrs={'class':'retro campaignCheck','onclick':'toggleCampaign(this)'}),
                                   required=False)
    gaCampaign=forms.CharField(widget=forms.TextInput(attrs={'name':"utm_campaign",
                             'size':'25'}),required=False)
    gaSource=forms.CharField(widget=forms.TextInput(attrs={'name':"utm_source",
                             'size':'25'}),required=False)
    gaMedium=forms.CharField(widget=forms.TextInput(attrs={'name':"utm_medium",
                             'size':'25'}),required=False)
    gaTerm=forms.CharField(widget=forms.TextInput(attrs={'name':"utm_term",
                             'size':'25'}),required=False)
    gaContent=forms.CharField(widget=forms.TextInput(attrs={'name':"utm_content",
                             'size':'25'}),required=False)
    
    interval_candidates=[]
    for i in camp_const.SCHEDULE_FEED_POSTING_INTERVALS:
        interval_candidates.append((i,camp_const.INTERVAL_MAP[i])) 
    scheduleInterval=forms.ChoiceField(choices=interval_candidates ,required=False)
    randomize = forms.BooleanField(widget=forms.CheckboxInput(attrs={'id':'randomize_checkbox','class':'retro randomizeCheck','onclick':'toggleRandomize(this)'}),
                                   required=False)
    randomizeTimeWindow = forms.ChoiceField(choices=[(5,5),(10,10),(15,15),(30,30)],required=False)
    maxMessagePerFeed = forms.ChoiceField(choices=[(1,1),(2,2),(3,3),(4,4),(5,5)],required=False,initial=1)
    filters = forms.CharField(widget=forms.TextInput(attrs={
                             "size":"80", "placeholder":"Comma separated, case insensitive: \"San Jose, CA\", Tech, Silicon Valley"}),required=False)
    includedTags = forms.CharField(widget=forms.TextInput(attrs={
                             "size":"80", "placeholder":"Comma separated, lower case: youtube, vimeo"}),required=False)
    excludedTags = forms.CharField(widget=forms.TextInput(attrs={
                             "size":"80", "placeholder":"Comma separated, lower case: us cities, us states, european cities"}),required=False)
    filterType = forms.ChoiceField(choices=[(mgmt_const.CMP_RULE_FILTER_TYPE_EXCLUDED_USER,'Excluded user tags'),(mgmt_const.CMP_RULE_FILTER_TYPE_INCLUDED_USER,'Included user tags'),
                                            (mgmt_const.CMP_RULE_FILTER_TYPE_TOPIC,'Included topics')],widget=forms.Select(
                                   attrs={"onchange":"choosefilterType(this)","class":"retro loadFilterType"}),required=True)
    feedSources = forms.MultipleChoiceField(choices=cont_const.PRIMARY_FEED_SOURCE_CHOICES, required=True)
    choices = []
    for i in range(1,10):
        choices.append((i,i))
    priority = forms.ChoiceField(choices=choices)
    
    def api_module(self):
        return api_const.API_M_MGMT
        
class ContentCampaignCreateForm(ContentCampaignForm):
    pass


class ContentCampaignUpdateForm(ContentCampaignForm):
    id=forms.CharField(widget=forms.HiddenInput)
    

class TopicContentCampaignForm(BaseForm):
    interval_candidates=[]
    for i in camp_const.SCHEDULE_FEED_POSTING_INTERVALS:
        interval_candidates.append((i,camp_const.INTERVAL_MAP[i])) 
    scheduleInterval=forms.ChoiceField(choices=interval_candidates ,required=False)
    maxMessagePerFeed = forms.ChoiceField(choices=[(1,1),(2,2),(3,3),(4,4),(5,5)],required=False,initial=1)
    feedSources = forms.MultipleChoiceField(choices=cont_const.FEED_SOURCE_CHOICES[1:], required = False )
    
    def api_module(self):
        return api_const.API_M_MGMT_TOPIC
    
class TopicContentCampaignCreateForm(TopicContentCampaignForm):
    pass


class TopicContentCampaignUpdateForm(TopicContentCampaignForm):
    id=forms.CharField(widget=forms.HiddenInput)

class NoChannelForm(NoNameBaseForm):
    priority = forms.ChoiceField(choices=[(-1,"All"),(0,'Unspecified'),(1,'P1'),(2,'P2'),(3,'P3'),(4,"Don't Add Channel"),(5,'Not Interesting')],
                             widget=forms.Select(attrs={"onchange":"chooseNoChannelPriority(this)","id":"priority"}),required=True)
    pagination = forms.ChoiceField(choices=[(10,10),(20,20),(50,50)],
                             widget=forms.Select(attrs={"onchange":"chooseNoChannelPagination(this)","id":"pagination"}),required=True)

class NoTopicForm(NoNameBaseForm):
    pagination = forms.ChoiceField(choices=[(10,10),(20,20),(50,50)],
                             widget=forms.Select(attrs={"onchange":"chooseNoTopicPagination(this)","id":"pagination"}),required=True)
