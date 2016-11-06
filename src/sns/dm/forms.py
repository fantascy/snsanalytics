from google.appengine.ext import db
from sns.api.facade import iapi
from sns.api import consts as api_const
from django import forms
from sns.deal import consts as deal_const
from sns.deal import api as deal_api
from sns.dm import consts as dm_const
from sns.view import consts as view_const
from sns.view.baseform import BaseForm, NameMultipleChoiceField
from common.utils import string as str_util


class DMCampaignForm(BaseForm):
    
    def __init__( self, *args, **kwargs ):
        super(BaseForm, self ).__init__( *args, **kwargs )
        if self.__class__.__name__.find('CreateForm')!=-1:
            channelChoice=[]
            channels = iapi(api_const.API_M_CHANNEL).query_base().fetch(limit=1000)
            for channel in channels:
                channelChoice.append((channel.key(),channel.name))
            self.fields['sourceChannel'] = forms.ChoiceField(choices=channelChoice,widget=forms.Select(
                                       attrs={"name":"channel","id":"channel"}),label="Define DM Source Twitter account", required=False)
            
        articleChoice=[]
        articles=iapi(api_const.API_M_ARTICLE).query_base().fetch(limit=100) 
        for article in articles:
            articleChoice.append((article.id,article.msgShort80))
        self.fields['contents'] = NameMultipleChoiceField(choices=articleChoice, label_attr='msg', required=False)
        
        choices = []
        cities = deal_api.GrouponApi.get_city_2_division_map().keys()
        cities.sort()
        for location in cities:
            choices.append((location,location))
        self.fields['locations'] = forms.MultipleChoiceField(choices=choices,required=False)
        
        choices = []
        cats = deal_const.TOPIC_2_GROUPON_CATEGORY_MAP.keys()
        cats.sort()
        for cat in cats:
            choices.append((str_util.name_2_key(cat),cat))
        self.fields['nationalTopics'] = forms.MultipleChoiceField(choices=choices,required=False)
        
        choices = []
        cats = deal_const.TOPIC_2_GROUPON_CATEGORY_MAP.keys()
        cats.sort()
        for cat in cats:
            choices.append((str_util.name_2_key(cat),cat))
        self.fields['topics'] = forms.MultipleChoiceField(choices=choices,required=False)
    
    sendOrder =  forms.ChoiceField(choices=[(dm_const.DM_LATEST_TO_OLDEST,'Latest to Oldest'),(dm_const.DM_OLDEST_TO_LATEST,'Oldest to Latest')],required=True)
    interval_candidates=[]
    for i in dm_const.DM_INTERVALS:
        interval_candidates.append((i,dm_const.INTERVAL_MAP[i]))                     
    scheduleInterval=forms.ChoiceField(choices=interval_candidates,widget=forms.Select(
                                   attrs={"id":"schedule_interval"}),required=False)
    dailyTarget = forms.IntegerField(required=False)
    totalTarget = forms.IntegerField(required=False)
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
    
    
    def api_module(self):
        return api_const.API_M_DM_RULE
    

class DMCampaignCreateForm(DMCampaignForm): 
    pass

class DMCampaignUpdateForm(DMCampaignForm):
    id=forms.CharField(widget=forms.HiddenInput)
    current_page=forms.CharField(widget=forms.HiddenInput,required=False)
    sChannel  = forms.CharField(widget=forms.HiddenInput(attrs={'size':'50'}),label="DM source account")
      
class AdvancedDMCampaignForm(DMCampaignForm):
    promoteType=forms.ChoiceField(choices=[(dm_const.PROMOTE_TYPE_ACCOUNT,'Promote Accounts'),(dm_const.PROMOTE_TYPE_DEAL,'Promote Deals')],widget=forms.Select(
                                   attrs={'class':'retro promoteCheck','onchange':'togglePromote(this)'}),required=False)
    accountPromoteType=forms.ChoiceField(choices=[(dm_const.ACCOUNT_PROMOTE_TYPE_CITY,'City Accounts'),
                                                  (dm_const.ACCOUNT_PROMOTE_TYPE_CITY_CATEGORY,'City Category Accounts')],widget=forms.Select(
                                   attrs={'class':'retro promoteCityCat','onchange':'toggleCityCat(this)'}),required=False)
    categoryType = forms.ChoiceField(choices=[(dm_const.PROMOTE_CATEGORY_TYPE_NATION,'National Category'),(dm_const.PROMOTE_CATEGORY_TYPE_CITY,'City Category')], widget=forms.Select(
                                   attrs={'class':'retro promoteCategory','onchange':'toggleCategory(this)'}),required=False)        
    
    def api_module(self):
        return api_const.API_M_ADVANCED_DM_RULE
    
    def clean_topics(self):
        locations =  self.cleaned_data['locations']
        topics = self.cleaned_data['topics']
        nationalTopics = self.cleaned_data['nationalTopics']
        catType = self.cleaned_data['categoryType']
        if catType == dm_const.PROMOTE_CATEGORY_TYPE_NATION:
            if len(nationalTopics) == 0:
                raise forms.ValidationError('National category is required!')
        elif catType == dm_const.PROMOTE_CATEGORY_TYPE_CITY:
            if len(locations) == 0 and len(topics) == 0 :
                raise forms.ValidationError('Location or category is required!')
        return topics
    
    
class AdvancedDMCampaignCreateForm(AdvancedDMCampaignForm): 
    pass

class AdvancedDMCampaignUpdateForm(AdvancedDMCampaignForm):
    id=forms.CharField(widget=forms.HiddenInput)
    current_page=forms.CharField(widget=forms.HiddenInput,required=False)

      
class DMCampaignChartForm(BaseForm):
    def __init__( self,id, *args, **kwargs ):
        super(BaseForm, self ).__init__( *args, **kwargs )
        choices = []
        choices.append((999,"send count"))
        rule = db.get(id)
        for t in range(0,len(rule.sendTurn)):
            choices.append((t,"click count - "+str(t)))
        self.fields['type'] = forms.ChoiceField(choices=choices,
                                         widget=forms.Select(
                                         attrs={"id":"chartType","onchange":"chooseDMChartType(this)","class":"retro loadDMChart"}),required=True)

class AdvancedDMCampaignChartForm(BaseForm):
    def __init__( self, *args, **kwargs ):
        super(BaseForm, self ).__init__( *args, **kwargs )
        choices = []
        choices.append((0,"click count"))
        self.fields['type'] = forms.ChoiceField(choices=choices,
                                         widget=forms.Select(
                                         attrs={"id":"chartType","onchange":"chooseDMChartType(this)","class":"retro loadDMChart"}),required=True)


class DMCampaignSortByForm(forms.Form):    
    type = forms.ChoiceField(choices=[('nameLower','Name'),('state','Status')],
                                   widget=forms.Select(
                                   attrs={"id":"id_sortBy_type","name":"id_sortBy_type","onchange":"sortByKeyWord()"}),required=True)
    order = forms.ChoiceField(choices=view_const.LIST_ORDER,
                                   widget=forms.Select(
                                   attrs={"id":"id_direct_type","name":"id_direct_type","onchange":"sortByKeyWord()"}),required=True)
    paginate = forms.ChoiceField(choices=view_const.LIST_PAGINATE,
                                   widget=forms.Select(
                                   attrs={"id":"id_paginate_num","name":"id_paginate_num","onchange":"sortByKeyWord()"}),required=True)


class SystemSettingsForm(forms.Form):  
    monitor = forms.BooleanField(widget=forms.CheckboxInput(attrs={'onclick':"changeFollowMonitor('followmonitor')"}),
                                   required=False)
    weekStop = forms.BooleanField(widget=forms.CheckboxInput(attrs={'onclick':"changeFollowMonitor('followweekstop')"}),
                                   required=False)
        