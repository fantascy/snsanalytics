import urllib

from django import forms

from common.utils import string as str_util, url as url_util
from sns.core.core import User
from sns.api import consts as api_const
from sns.api.facade import iapi
from sns.chan import consts as channel_const
from sns.cont.api import FeedProcessor
from sns.camp import consts as camp_const
from sns.post import consts as post_const
from sns.view import consts as view_const
from sns.view.baseform import BaseForm, NoNameBaseForm, NameModelMultipleChoiceField, NameMultipleChoiceField, \
                             NameModelMultipleChoiceSmallField, NameMultipleChoiceChangeField


CHANNEL_SELECT_VALIDATION_MSG = "You must select at least one account!"

class PostingCampaignForm(BaseForm):
    keywords=forms.CharField(widget=forms.TextInput(attrs={
                             'size':'100'}),max_length=100,required=False)
    scheduleStart=forms.DateTimeField(widget=forms.DateTimeInput(
                                            attrs={'size':'25',
                                             "class":'Wdate',
                                             "onfocus":"WdatePicker({dateFmt:'yyyy-MM-dd HH:mm',lang:'en'})"}),
                                             required=False)
    scheduleEnd=forms.DateTimeField(widget=forms.DateTimeInput(
                                            attrs={'size':'25',
                                             "class":'Wdate',
                                             "onfocus":"WdatePicker({dateFmt:'yyyy-MM-dd HH:mm',lang:'en'})"}),
                                             required=False)
    
    msgPrefix=forms.CharField(max_length=20,label="Message Prefix:", required=False)
    msgSuffix=forms.CharField(max_length=15,label="Message Suffix:", required=False)

    disableChannelFilter = forms.BooleanField(required=False)
    
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
    
    fbName = forms.CharField(widget=forms.TextInput(attrs={'name':"fbName",
                             'size':'60'}),required=False)
    fbCaption = forms.CharField(widget=forms.Textarea(attrs={'name':"fbCaption",
                             'size':'60'}),required=False)
    fbDescription = forms.CharField(widget=forms.TextInput(attrs={'name':"fbDescription",
                             'size':'60'}),required=False)
    fbPicture=forms.CharField(widget=forms.HiddenInput,required=False)
    
    hideTwitter=forms.BooleanField(widget=forms.CheckboxInput(attrs={'id':"is_twitter_campaign",'class':'retro hideTwitter','onclick':'choosePostTypeCampaign(this)'}),
                                   required=False)
    hideFacebook=forms.BooleanField(widget=forms.CheckboxInput(attrs={'id':"is_facebook_campaign",'class':'retro hideFacebook','onclick':'choosePostTypeCampaign(this)'}),
                                   required=False)
    randomize = forms.BooleanField(widget=forms.CheckboxInput(attrs={'id':'randomize_checkbox','class':'retro randomizeCheck','onclick':'toggleRandomize(this)'}),
                                   required=False)
    randomizeTimeWindow = forms.ChoiceField(choices=[(5,5),(10,10),(15,15)],required=False)
    
    
    def __init__( self, *args, **kwargs ):
        super(PostingCampaignForm, self ).__init__( *args, **kwargs )
        self.fields['channels'] = NameModelMultipleChoiceField(queryset=iapi(api_const.API_M_CHANNEL).query_base().order('nameLower').filter('state',channel_const.CHANNEL_STATE_NORMAL), label_attr='name',
                                                               widget=forms.SelectMultiple(attrs={'id':'channels_campaign','onchange':'changeTwitterInfo(this)'}),required=False)
        
        self.fields['fbDestinations'] = NameMultipleChoiceChangeField(choices=getFchannels(), label_attr='name',
                                                                    widget=forms.SelectMultiple(attrs={'id':'fchannels_campaign','onchange':'changeFacebookInfo(this)'}),required=False)
    
    def clean_name(self):
        """
        Validate name duplication before save.
        We use the convention of form name to check if we need to do a uniqueness check. There must be some better methods.
        """
        name = self.cleaned_data['name']
        nameLower = str_util.lower_strip(name)
        object = self.iapi().query(dict(nameLower=nameLower, limit=1))
        if len(object)>0:
            if self.__class__.__name__.endswith("CreateForm"):
                raise forms.ValidationError("Duplicated name!")
            if self.__class__.__name__.endswith("UpdateForm"):
                id = self.data['id']
                if object[0].id != id:
                    raise forms.ValidationError("Duplicated name!")
        return name
    
    def clean_channels(self):
        channels=self.cleaned_data['channels']
        if len(channels) == 0 and not self.data.has_key('fbDestinations'):
            raise forms.ValidationError(CHANNEL_SELECT_VALIDATION_MSG)        
        if len(channels)>post_const.LIMIT_CHANNEL_PER_RULE:
            raise forms.ValidationError("A marketing campaign can have at most %d twitter channels!" %post_const.LIMIT_CHANNEL_PER_RULE)        
        return channels
    
    def clean_fbDestinations(self):
        channels=self.cleaned_data['fbDestinations']
        if len(channels)>post_const.LIMIT_CHANNEL_PER_RULE:
            raise forms.ValidationError("A marketing campaign can have at most %d facebook channels!" %post_const.LIMIT_CHANNEL_PER_RULE)        
        return channels

class MessageCampaignForm(PostingCampaignForm):
    interval_candidates=[]
    for i in camp_const.SCHEDULE_ARTICLE_POSTING_INTERVALS:
        interval_candidates.append((i,camp_const.INTERVAL_MAP[i]))                     
    scheduleInterval=forms.ChoiceField(choices=interval_candidates,widget=forms.Select(
                                   attrs={"id":"schedule_interval","onchange":"modifyRandomizeTimeCount(this)",'class':'retro randomizeTimeCount'}),required=False)
    fbPostStyle=forms.BooleanField(widget=forms.CheckboxInput(attrs={'id':'is_attach','onclick':'attach_link(this)','type':'hidden'}),
                                    required=False)
    
    def __init__( self, *args, **kwargs ):
        super(MessageCampaignForm, self ).__init__( *args, **kwargs )
        self.fields['scheduleType'] = forms.ChoiceField(
            choices=post_const.MSG_CAMPAIGN_SCHEDULE_CHOICES_ADMIN if User.is_admin() else post_const.MSG_CAMPAIGN_SCHEDULE_CHOICES,
            widget=forms.Select(attrs={"onchange":"sns.rule.onScheduleTypeChange(this)","class":"retro scheduleTypeCheck"}),
            required=True)
        articles=iapi(api_const.API_M_ARTICLE).query_base(showSmall=True).order('msgShort80').fetch(limit=1000)
        choices=[]
        for article in articles:
            choices.append((article.id,article.msgShort80))
        self.fields['contents'] = NameMultipleChoiceField(choices=choices, label_attr='msg') 
   
    def api_module(self):
        return api_const.API_M_POSTING_RULE_ARTICLE
    
    def clean_contents(self):
        contents=self.cleaned_data['contents']
        if len(contents)>post_const.LIMIT_CONTENT_PER_RULE:
            raise forms.ValidationError("You can schedule at most %d messages a time!"%post_const.LIMIT_CONTENT_PER_RULE)        
        return contents
    
    def clean_url(self):
        """
        check url
        """
        if self.cleaned_data['url']:
            sanitized_url=url_util.sanitize_url(self.cleaned_data['url'])
            if not sanitized_url:
                raise forms.ValidationError("invalid url!")
            return sanitized_url
        else:
            return ""    

class MessageCampaignCreateForm(MessageCampaignForm):
    ret_url=forms.CharField(widget=forms.HiddenInput,required=False)
    
class MessageCampaignUpdateForm(MessageCampaignForm):
    id=forms.CharField(widget=forms.HiddenInput)
    ret_url=forms.CharField(widget=forms.HiddenInput,required=False)
    current_page=forms.CharField(widget=forms.HiddenInput,required=False)


#quick article post form
class QuickMessageCampaignCreateForm(NoNameBaseForm):
    url  = forms.URLField(max_length=url_util.MAX_URL_LENGTH, widget=forms.TextInput(attrs={'size':'70','onkeyup':'shift_link(this)','onchange':'shift_link(this)'}), required=False)
    msg = forms.CharField(max_length=420, widget=forms.Textarea(attrs={'cols':'45','rows':'4'}),required=True)
    
    type =  forms.MultipleChoiceField(choices=[(0,"Twitter"),(1,"Facebook"),(2,"Twitter & Facebook")], required = True ,widget= forms.SelectMultiple(attrs={'class':'hidden'}))
    fbName = forms.CharField(required=False,max_length=256,widget=forms.TextInput(attrs={'id':'id_fbName','name':"fbName",'type':"text",'style':"width: 400px;"}))
    fbDescription = forms.CharField(required=False,max_length=500,widget=forms.Textarea(attrs={'id':'id_fbDescription','name':"fbDescription",'style':"width: 400px;height:100px;"}))
    fbPicture=forms.CharField(required=False,widget=forms.TextInput(attrs={'id':'id_fbPicture','name':"fbPicture"}))
    
    fbPostStyle=forms.BooleanField(widget=forms.CheckboxInput(attrs={'id':'is_attach','name':"mode",'class':'retro fbPostStyle','onclick':'attach_link(this)','style':'width: auto;'}),
                                    required=False)
    twitter=forms.BooleanField(widget=forms.CheckboxInput(attrs={'id':"is_twitter",'class':'retro hideTwitter','onclick':'choosePostToType(this,false)','style':"width: auto;"}),
                                   required=False)
    facebook=forms.BooleanField(widget=forms.CheckboxInput(attrs={'id':"is_facebook",'class':'retro hideFacebook','onclick':'choosePostToType(this,false)','style':"width: auto;"}),
                                   required=False)
    
    pic_current=forms.CharField(required=False,widget=forms.TextInput(attrs={'id':'id_fbPicture_current','name':"fbPicture_current"}))
    pic_total=forms.CharField(required=False,widget=forms.TextInput(attrs={'id':'id_fbPicture_total','name':"fbPicture_total"}))
    ret_url=forms.CharField(widget=forms.HiddenInput(attrs={'id':'ret_url_quickpost'}),required=False)
    
    def __init__( self, *args, **kwargs ):
        super(QuickMessageCampaignCreateForm, self ).__init__( *args, **kwargs )
        self.fields['channels'] = NameModelMultipleChoiceSmallField(queryset=iapi(api_const.API_M_CHANNEL).query_base().order('nameLower').filter('state',channel_const.CHANNEL_STATE_NORMAL),label_attr='name',required=False)
        self.fields['fbDestinations'] = forms.MultipleChoiceField(choices=getFchannels(), required = False ,widget= forms.SelectMultiple(attrs={'class':'multiselect'}))

    def clean_url(self):
        """
        check url
        """
        if self.cleaned_data['url']:
            sanitized_url=url_util.sanitize_url(self.cleaned_data['url'])
            if not sanitized_url:
                raise forms.ValidationError("invalid url!")
            return sanitized_url
        else:
            return ""
   
    def api_module(self):
        return api_const.API_M_POSTING_RULE_ARTICLE

    def clean_channels(self):
        channels=self.cleaned_data['channels']
        if len(channels) == 0 and not self.data.has_key('fbDestinations'):
            raise forms.ValidationError(CHANNEL_SELECT_VALIDATION_MSG)        
        if len(channels)>post_const.LIMIT_CHANNEL_PER_RULE:
            raise forms.ValidationError("A marketing campaign can have at most %d twitter channels!" %post_const.LIMIT_CHANNEL_PER_RULE)        
        return channels
    
    def clean_fbDestinations(self):
        channels=self.cleaned_data['fbDestinations']
        if len(channels)>post_const.LIMIT_CHANNEL_PER_RULE:
            raise forms.ValidationError("A marketing campaign can have at most %d facebook channels!" %post_const.LIMIT_CHANNEL_PER_RULE)        
        return channels

        
class FeedCampaignForm(PostingCampaignForm):
    maxMessagePerFeed = forms.ChoiceField(choices=[(1,1),(2,2),(3,3),(4,4),(5,5)],required=False,initial=1)
    #fbPostStyle = forms.ChoiceField(choices=[(common_const.FACEBOOK_POST_TYPE_STANDARD,"Standard"),(common_const.FACEBOOK_POST_TYPE_COMPACT,"Compact")],widget=forms.RadioSelect())

    interval_candidates=[]
    for i in camp_const.SCHEDULE_FEED_POSTING_INTERVALS:
        interval_candidates.append((i,camp_const.INTERVAL_MAP[i]))                     
    scheduleInterval=forms.ChoiceField(choices=interval_candidates,widget=forms.Select(
                                   attrs={"id":"schedule_interval","onchange":"modifyRandomizeTimeCount(this)",'class':'retro randomizeTimeCount'}),required=False)
    titleOnly = forms.BooleanField(widget=forms.CheckboxInput(attrs={'onclick':'chooseCampaignOnlyTitleCheck(this)'}),required=False)
    fbPostStyle=forms.BooleanField(widget=forms.CheckboxInput(),required=False)
    
    prefixTitle = forms.BooleanField(widget=forms.CheckboxInput(attrs={'id':'prefixTitle_id','onclick':'prefixTitleCheck(this)','class':'retro prefixTitileLoad'}),required=False)
    prefixDelimter = forms.CharField(widget=forms.HiddenInput(attrs={'id':'prefixDelimter'}),required=False)
    suffixTitle = forms.BooleanField(widget=forms.CheckboxInput(attrs={'id':'suffixTitle_id','onclick':'suffixTitleCheck(this)','class':'retro suffixTitileLoad'}),required=False)
    suffixDelimter = forms.CharField(widget=forms.HiddenInput(attrs={'id':'suffixDelimter'}),required=False)
     
    def __init__( self, *args, **kwargs ):
        super(FeedCampaignForm, self ).__init__( *args, **kwargs )
        feeds=iapi(api_const.API_M_FEED).query_base(showSmall=True).order('name').fetch(limit=1000)
        choices=[]
        for feed in feeds:
            name = str_util.slice(feed.name,'0:45')
            choices.append((feed.id,name)) 
        self.fields['contents'] = NameMultipleChoiceField(choices=choices)
           
    def api_module(self):
        return api_const.API_M_POSTING_RULE_FEED
 
    def clean_contents(self):
        contents=self.cleaned_data['contents']
        if len(contents)>post_const.LIMIT_CONTENT_PER_RULE:
            raise forms.ValidationError("A feed campaign can have at most %d feeds!"%post_const.LIMIT_CONTENT_PER_RULE)        
        return contents
   
    
class FeedCampaignCreateForm(FeedCampaignForm):
    ret_url=forms.CharField(widget=forms.HiddenInput,required=False)
    
class FeedCampaignUpdateForm(FeedCampaignForm):
    id=forms.CharField(widget=forms.HiddenInput)
    ret_url=forms.CharField(widget=forms.HiddenInput,required=False)
    current_page=forms.CharField(widget=forms.HiddenInput,required=False)

#quick feed post form
class QuickFeedCampaignCreateForm(NoNameBaseForm):
    url  = forms.CharField(max_length=url_util.MAX_URL_LENGTH, label="Feed URL:", widget=forms.TextInput(attrs={'size':'70'})) 
    interval_candidates=[]
    for i in camp_const.SCHEDULE_FEED_POSTING_INTERVALS:
        interval_candidates.append((i,camp_const.INTERVAL_MAP[i]))
    scheduleInterval=forms.ChoiceField(choices=interval_candidates,required=False)
    
    hideTwitter=forms.BooleanField(widget=forms.CheckboxInput(attrs={'id':"is_twitter_campaign",'class':'retro hideTwitter','onclick':'choosePostTypeCampaignQuickPost(this)'}),
                                   required=False)
    hideFacebook=forms.BooleanField(widget=forms.CheckboxInput(attrs={'id':"is_facebook_campaign",'class':'retro hideFacebook','onclick':'choosePostTypeCampaignQuickPost(this)'}),
                                   required=False)
    fbPostStyle=forms.BooleanField(widget=forms.CheckboxInput(),initial='on',required=False)
    ret_url=forms.CharField(widget=forms.HiddenInput(attrs={'id':'ret_url_quickpost'}),required=False)
    
    def __init__( self, *args, **kwargs ):
        super(QuickFeedCampaignCreateForm, self ).__init__( *args, **kwargs )
        self.fields['channels'] = NameModelMultipleChoiceSmallField(queryset=iapi(api_const.API_M_CHANNEL).query_base().order('nameLower').filter('state',channel_const.CHANNEL_STATE_NORMAL), label_attr='name',required=False)
        self.fields['fbDestinations'] = forms.MultipleChoiceField(choices=getFchannels(), required = False ,widget= forms.SelectMultiple(attrs={'class':'multiselect'}))
        
    def clean_url(self):
        """
        get feed name by reading its url
        """
        url=self.cleaned_data['url']
        fetcher = FeedProcessor.get_feed_fetcher_by_url(url)
        if not fetcher.is_valid:
            raise forms.ValidationError("invalid feed!")
        return "%s***%s***%s" % (fetcher.url(), fetcher.title, fetcher.url())
    
    def api_module(self):
        return api_const.API_M_POSTING_RULE_ARTICLE
    
    def clean_channels(self):
        channels=self.cleaned_data['channels']
        if len(channels) == 0 and not self.data.has_key('fbDestinations'):
            raise forms.ValidationError(CHANNEL_SELECT_VALIDATION_MSG)        
        if len(channels)>post_const.LIMIT_CHANNEL_PER_RULE:
            raise forms.ValidationError("A marketing campaign can have at most %d twitter channels!" %post_const.LIMIT_CHANNEL_PER_RULE)        
        return channels
    
    def clean_fbDestinations(self):
        channels=self.cleaned_data['fbDestinations']
        if len(channels)>post_const.LIMIT_CHANNEL_PER_RULE:
            raise forms.ValidationError("A marketing campaign can have at most %d facebook channels!" %post_const.LIMIT_CHANNEL_PER_RULE)        
        return channels

def getFchannels():
    fchannels = iapi(api_const.API_M_FCHANNEL).query_base().order('nameLower').fetch(limit=100)
    channels = []
    for fchannel in fchannels:
        if fchannel.state == channel_const.CHANNEL_STATE_SUSPENDED:
            continue
        key = fchannel.id + ':' + 'me'
        channels.append((key,fchannel.name))
        for g in fchannel.groups:
            index = g.find(':')
            id = g[index+1:]
            name = g[:index]
            name = name.encode('utf-8','ignore')
            key = fchannel.id + ':' +id
            channels.append((key,'--- group : '+urllib.unquote(name)))
        for g in fchannel.pages:
            index = g.find(':')
            id = g[index+1:]
            name = g[:index]
            name = name.encode('utf-8','ignore')
            key = fchannel.id + ':' +id
            channels.append((key,'--- page : '+urllib.unquote(name)))
    fbpages = iapi(api_const.API_M_FBPAGE).query_base().order('nameLower').fetch(limit=100)
    for page in fbpages:
        if page.state != channel_const.CHANNEL_STATE_SUSPENDED:
            key = page.id + ':' + 'admin'
            name = page.name
            channels.append((key,name))
    return channels
    
class MessageCampaignSortByForm(forms.Form):    
    type = forms.ChoiceField(choices=[('nameLower',"Name"),('state',"Status")],
                                   widget=forms.Select(
                                   attrs={"id":"id_sortBy_type","name":"id_sortBy_type","onchange":"sortByKeyWord()"}),required=True)
    order = forms.ChoiceField(choices=view_const.LIST_ORDER,
                                   widget=forms.Select(
                                   attrs={"id":"id_direct_type","name":"id_direct_type","onchange":"sortByKeyWord()","style":"display:none"}),required=True)
    paginate = forms.ChoiceField(choices=view_const.LIST_PAGINATE,
                                   widget=forms.Select(
                                   attrs={"id":"id_paginate_num","name":"id_paginate_num","onchange":"sortByKeyWord()"}),required=True)
    
class FeedCampaignSortByForm(forms.Form):    
    type = forms.ChoiceField(choices=[('nameLower',"Name"),('state',"Status")],
                                   widget=forms.Select(
                                   attrs={"id":"id_sortBy_type","name":"id_sortBy_type","onchange":"sortByKeyWord()"}),required=True)
    order = forms.ChoiceField(choices=view_const.LIST_ORDER,
                                   widget=forms.Select(
                                   attrs={"id":"id_direct_type","name":"id_direct_type","onchange":"sortByKeyWord()","style":"display:none"}),required=True)
    paginate = forms.ChoiceField(choices=view_const.LIST_PAGINATE,
                                   widget=forms.Select(
                                   attrs={"id":"id_paginate_num","name":"id_paginate_num","onchange":"sortByKeyWord()"}),required=True)
            