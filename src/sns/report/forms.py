from django import forms
from sns.cont.api import FeedProcessor, MessageProcessor
from sns.chan.api import TAccountProcessor,FAccountProcessor,FAdminPageProcessor
from sns.post.api import StandardCampaignProcessor
from sns.camp.api import CampaignProcessor
from common.utils.string import slice_double_byte_character_set

    
class ReportBasicForm(forms.Form):
    type = forms.ChoiceField(choices=[(0,"all my posts"),(8,"all my quick posts"),(1,"one post"),
                                      (3,"one Twitter account"),(4,"one feed"),
                                           (5,"one campaign"),(7,"one Facebook Account/Page")],
                                   widget=forms.Select(
                                   attrs={"id":"chart_report_type","onchange":"chooseReportType(this)","class":"retro loadReportChart"}),required=True)
    
    surl_value=forms.CharField(widget=forms.HiddenInput(attrs={
                                 'id':'surl_value'}),required=False)
    
    url_value=forms.CharField(widget=forms.HiddenInput(attrs={
                                 'id':'url_value'}),required=False)
    
    feed_value=forms.CharField(widget=forms.HiddenInput(attrs={
                                 'id':'feed_value'}),required=False)

    channel_value=forms.CharField(widget=forms.HiddenInput(attrs={
                                 'id':'channel_value'}),required=False)
    fchannel_value=forms.CharField(widget=forms.HiddenInput(attrs={
                                 'id':'fchannel_value'}),required=False)
    campaign_value=forms.CharField(widget=forms.HiddenInput(attrs={
                                 'id':'campaign_value'}),required=False)
    direct_value=forms.CharField(widget=forms.HiddenInput(attrs={
                                 'id':'direct_value'}),required=False)

class SurlTopForm(forms.Form):
    surl = forms.CharField(widget=forms.TextInput(attrs={
                           'name':'urlHash','id':'urlHash','size':10,
                           'onkeydown':"enterPress(event);"}))
    
class UrlTopForm(forms.Form):
    url = forms.CharField(widget=forms.TextInput(attrs={
                           'name':'url','id':'url','size':60,
                           'onkeydown':"enterPress(event);"}))
    
class ChannelTopForm(forms.Form):
    def __init__( self, *args, **kwargs ):
        super(ChannelTopForm, self ).__init__( *args, **kwargs )
        channelChoice=[]
        channels = TAccountProcessor().query(dict(limit=1000))
        for channel in channels:
            channelChoice.append((channel.keyNameStrip(),slice_double_byte_character_set(channel.name,50)))
            
        self.fields['channel'] = forms.ChoiceField(choices=channelChoice,widget=forms.Select(
                                   attrs={"name":"channel","id":"channel","onchange":"updateChannelAll()"}),required=True)
        
        channelChoice.insert(0, (None,'None'))
        self.fields['channelCompare'] = forms.ChoiceField(choices=channelChoice,widget=forms.Select(
                                   attrs={"name":"channel","id":"channel_compare","onchange":"updateChannelHisDetail()"}),required=True)
        

class FChannelTopForm(forms.Form):
    def __init__( self, *args, **kwargs ):
        super(FChannelTopForm, self ).__init__( *args, **kwargs )
        fchannelChoice=[]
        fchannels = FAccountProcessor().query(dict(limit=1000))
        for fchannel in fchannels:
            fchannelChoice.append((fchannel.id,slice_double_byte_character_set(fchannel.name,50)))
        pchannels = FAdminPageProcessor().query(dict(limit=1000))
        for pchannel in pchannels:
            fchannelChoice.append((pchannel.id,slice_double_byte_character_set(pchannel.name,50)))
           
        self.fields['fchannel'] = forms.ChoiceField(choices=fchannelChoice,widget=forms.Select(
                                   attrs={"name":"fchannel","id":"fchannel","onchange":"updateFChannelAll()"}),required=True)
        
        fchannelChoice.insert(0, (None,'None'))
        self.fields['fchannelCompare'] = forms.ChoiceField(choices=fchannelChoice,widget=forms.Select(
                                   attrs={"name":"fchannel","id":"fchannel_compare","onchange":"updateFChannelHisDetail()"}),required=True)
        

class FeedTopForm(forms.Form):
    def __init__( self, *args, **kwargs ):
        super(FeedTopForm, self ).__init__( *args, **kwargs )
        feedChoice=[]
        feeds = FeedProcessor().query(dict(limit=1000))
        for feed in feeds:
            feedChoice.append((feed.id,feed.name))
            
        self.fields['feed'] = forms.ChoiceField(choices=feedChoice,widget=forms.Select(
                                   attrs={"name":"feed","id":"feed","onchange":"updateFeedAll()"}),required=True)
        
        feedChoice.insert(0, (None,'None'))
        self.fields['feedCompare'] = forms.ChoiceField(choices=feedChoice,widget=forms.Select(
                                   attrs={"name":"feed","id":"feed_compare","onchange":"updateFeedHisDetail()"}),required=True)
        
        
class CampaignTopForm(forms.Form):
    def __init__( self, *args, **kwargs ):
        super(CampaignTopForm, self ).__init__( *args, **kwargs )
        campaignChoice=[]
        
        campaigns = CampaignProcessor().query_base(showSmall=True).fetch(limit=1000)   
        for campaign in campaigns:
            if campaign.__class__.__name__ == 'MessageCampaignSmall' or campaign.__class__.__name__ == 'FeedCampaignSmall' or campaign.__class__.__name__ == 'CustomCampaignSmall' or campaign.__class__.__name__ == 'DirectMessageCampaignSmall':
                campaignChoice.append((campaign.modelKeyStr(), slice_double_byte_character_set(campaign.name,50)))
            
        self.fields['campaign'] = forms.ChoiceField(choices=campaignChoice,widget=forms.Select(
                                   attrs={"name":"campaign","id":"campaign","onchange":"updateCampaignAll()"}),required=True)
        campaignChoice.insert(0, (None,'None'))
        self.fields['campaignCompare'] = forms.ChoiceField(choices=campaignChoice,widget=forms.Select(
                                   attrs={"name":"campaign","id":"campaign_compare","onchange":"updateCampaignHisDetail()"}),required=True)
        
        
class ChannelFailureTopForm(forms.Form):
    def __init__( self, *args, **kwargs ):
        super(ChannelFailureTopForm, self ).__init__( *args, **kwargs )                
        channelChoice=[]
        channels = TAccountProcessor().query(dict(limit=1000))
        for channel in channels:
            channelChoice.append((channel.login(),slice_double_byte_character_set(channel.name,50)))
        self.fields['channelFailure'] = forms.ChoiceField(choices=channelChoice,widget=forms.Select(
                                   attrs={"name":"channelFailure","id":"channelFailure","onchange":"updateChannelFailureHisDetail()"}),required=True)
  

class FChannelFailureTopForm(forms.Form):
    def __init__( self, *args, **kwargs ):
        super(FChannelFailureTopForm, self ).__init__( *args, **kwargs )   
        fchannelChoice=[]
        fchannels = FAccountProcessor().query(dict(limit=1000))
        for fchannel in fchannels:
            fchannelChoice.append((fchannel.id,slice_double_byte_character_set(fchannel.name,50)))
        pchannels = FAdminPageProcessor().query(dict(limit=1000))
        for pchannel in pchannels:
            fchannelChoice.append((pchannel.id,slice_double_byte_character_set(pchannel.name,50)))
        self.fields['fchannelFailure'] = forms.ChoiceField(choices=fchannelChoice,widget=forms.Select(
                                   attrs={"name":"fchannelFailure","id":"fchannelFailure","onchange":"updateFChannelFailureHisDetail()"}),required=True)
        
class MessageFailureTopForm(forms.Form):
    def __init__( self, *args, **kwargs ):
        super(MessageFailureTopForm, self ).__init__( *args, **kwargs )  
        articleChoice=[]
        articles = MessageProcessor().query(dict(limit=1000))
        for article in articles:
            articleChoice.append((article.id,article.msgShort80))
        self.fields['articleFailure'] = forms.ChoiceField(choices=articleChoice,widget=forms.Select(
                                   attrs={"name":"articleFailure","id":"articleFailure","onchange":"updateMessageFailureHisDetail()"}),required=True)
        
class FeedFailureTopForm(forms.Form):
    def __init__( self, *args, **kwargs ):
        super(FeedFailureTopForm, self ).__init__( *args, **kwargs )  
        feeds = FeedProcessor().query(dict(limit=1000))
        feedFailureChoice=[]
        for feed in feeds:
            feedFailureChoice.append((feed.id,feed.name))        
        self.fields['feedFailure'] = forms.ChoiceField(choices=feedFailureChoice,widget=forms.Select(
                                   attrs={"name":"feedFailure","id":"feedFailure","onchange":"updateFeedFailureHisDetail()"}),required=True)
        
class CampaignFailureTopForm(forms.Form):
    def __init__( self, *args, **kwargs ):
        super(CampaignFailureTopForm, self ).__init__( *args, **kwargs )  
        campaigns = StandardCampaignProcessor().query_base(showSmall=True).fetch(limit=1000) 
        campaignFailureChoice=[]
        for campaign in campaigns:
            campaignFailureChoice.append((campaign.modelKeyStr(), campaign.name))        
        self.fields['campaignFailure'] = forms.ChoiceField(choices=campaignFailureChoice,widget=forms.Select(
                                   attrs={"name":"campaignFailure","id":"campaignFailure","onchange":"updateCampaignFailureHisDetail()"}),required=True)
        

class FailureBasicForm(forms.Form):
    failureType = forms.ChoiceField(choices=[(0,"all my posts"),(1,"one Twitter Account"),(2,"one message")
                                           ,(3,"one feed"),(4,"one campaign"),(5,"one Facebook Account/Page")],
                                   widget=forms.Select(
                                   attrs={"id":"report_failure_type","onchange":"chooseFailureType(this)","class":"retro loadFailure"}),required=True)
    
                  
    channel_failure_value=forms.CharField(widget=forms.HiddenInput(attrs={
                                 'id':'channel_failure_value'}),required=False)
    
    
    fchannel_failure_value=forms.CharField(widget=forms.HiddenInput(attrs={
                                 'id':'fchannel_failure_value'}),required=False)

    article_failure_value=forms.CharField(widget=forms.HiddenInput(attrs={
                                 'id':'article_failure_value'}),required=False)

    feed_failure_value=forms.CharField(widget=forms.HiddenInput(attrs={
                                 'id':'feed_failure_value'}),required=False)
    
    campaign_failure_value=forms.CharField(widget=forms.HiddenInput(attrs={
                                 'id':'campaign_failure_value'}),required=False)
    
    
