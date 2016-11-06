from django import forms
from sns.serverutils.event_const import _COMMAND_HANDLER_MAP,SEND_MAILS
from sns.view.baseform import BaseForm
from sns.api import consts as api_const



class CampaignForm(BaseForm):
    
    def __init__(self, *args, **kwargs):
        super(CampaignForm, self ).__init__( *args, **kwargs )
        event_list=[(SEND_MAILS,SEND_MAILS)]
#        for n in _COMMAND_HANDLER_MAP.keys():
#            event_list.append((n,n))
        self.fields['event'] = forms.ChoiceField(choices=event_list,widget=forms.Select(),required=True)
        
        
    
    name = forms.CharField(widget=forms.TextInput(attrs={'size':'30'}),max_length=30,required=True)
    
    
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
    
    scheduleType=forms.ChoiceField(choices=[(0,"now"),(1,"onetime"),(2,"recurring")],
                                   widget=forms.Select(
                                   attrs={"onchange":"sns.rule.onScheduleTypeChange(this)"}),required=True)
    
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
        return api_const.API_M_CAMPAIGN

class CampaignUpdateForm(CampaignForm):
    id = forms.CharField(widget=forms.HiddenInput)

class CampaignCreateForm(CampaignForm):
    pass
    
        