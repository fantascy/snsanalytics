from django import forms

from fe.api import consts as api_const
from sns.view import consts as view_const
from sns.view.baseform import BaseForm


class FollowCampaignForm(BaseForm):
    def __init__( self, *args, **kwargs ):
        super(BaseForm, self ).__init__( *args, **kwargs )
        self.fields['infoType'] = forms.CharField(widget=forms.HiddenInput(attrs={
                                 'id':'infoType'}),required=False,initial=type)
       
    def api_module(self):
        return api_const.API_M_FOLLOW
    
        
class FollowCampaignCreateForm(FollowCampaignForm):
    ret_url=forms.CharField(widget=forms.HiddenInput,required=False)
    

class FollowCampaignSafeCreateForm(FollowCampaignForm):
    ret_url=forms.CharField(widget=forms.HiddenInput,required=False)

class FollowCampaignUpdateForm(FollowCampaignForm):
    id=forms.CharField(widget=forms.HiddenInput)
    ret_url=forms.CharField(widget=forms.HiddenInput,required=False)
    
class FollowCampaignChartForm(BaseForm):
    type = forms.ChoiceField(choices=[(0,"total followers"),(1,"follow and unfollow"),(2,"follow and new follower")],
                                     widget=forms.Select(
                                     attrs={"id":"chartType","onchange":"chooseFollowType(this)","class":"retro loadFollowChart"}),required=True)
    

class FollowCampaignSortByForm(forms.Form):    
    type = forms.ChoiceField(choices=[('nameLower','Name'),('state','Status')],
                                   widget=forms.Select(
                                   attrs={"id":"id_sortBy_type","name":"id_sortBy_type","onchange":"sortByKeyWord()"}),required=True)
   
    order = forms.ChoiceField(choices=view_const.LIST_ORDER,
                                   widget=forms.Select(
                                   attrs={"id":"id_direct_type","name":"id_direct_type","onchange":"sortByKeyWord()"}),required=True)
    paginate = forms.ChoiceField(choices=view_const.LIST_PAGINATE,
                                   widget=forms.Select(
                                   attrs={"id":"id_paginate_num","name":"id_paginate_num","onchange":"sortByKeyWord()"}),required=True)

class AllFollowCampaignSortByForm(forms.Form):    
    type = forms.ChoiceField(choices=[('twitter_account','Twitter Account'),('nameLower','Name'),('user_email','User Name'), ('state','Status')],
                                   widget=forms.Select(
                                   attrs={"id":"id_sortBy_type","name":"id_sortBy_type","onchange":"sortByKeyWord()"}),required=True)
   
    order = forms.ChoiceField(choices=view_const.LIST_ORDER,
                                   widget=forms.Select(
                                   attrs={"id":"id_direct_type","name":"id_direct_type","onchange":"sortByKeyWord()"}),required=True)
    paginate = forms.ChoiceField(choices=view_const.LIST_PAGINATE,
                                   widget=forms.Select(
                                   attrs={"id":"id_paginate_num","name":"id_paginate_num","onchange":"sortByKeyWord()"}),required=True)


class SystemSettingsForm(forms.Form):  
    stop_on_suspension = forms.BooleanField(widget=forms.CheckboxInput(attrs={'onclick':"toggleFollowConfig('stop_on_suspension')"}),
                                   required=False)
    stop_in_weekend = forms.BooleanField(widget=forms.CheckboxInput(attrs={'onclick':"toggleFollowConfig('stop_in_weekend')"}),
                                   required=False)
            