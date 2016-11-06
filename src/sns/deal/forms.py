from django import forms

from sns.view.baseform import BaseForm
from sns.api import consts as api_const
from sns.deal.models import DealBuilder
from sns.deal import consts as deal_const
from sns.deal.api import DealSourceApi
from sns.view import consts as view_const
from common.utils import string as str_util


class DealBuilderForm(BaseForm):
    name =forms.CharField(widget=forms.TextInput(attrs={
                             'size':'15'}),max_length=20,required=False)
    def __init__( self, *args, **kwargs ):
        super(DealBuilderForm, self ).__init__( *args, **kwargs )
        choices = []
        locations = list(DealSourceApi.get_all_deal_locations())
        locations.sort()
        for location in locations:
            choices.append((location, location))
        
        self.fields['location'] = forms.ChoiceField(choices=choices)
        
    def api_module(self):
        return api_const.API_M_DEAL_BUILDER
    
    def clean_location(self):
        location = self.cleaned_data['location']
        builder = DealBuilder.get_by_key_name(DealBuilder.keyName(location))
        if builder is not None and builder.deleted == False:
            raise forms.ValidationError('Deal feed already exist!')
        else:
            return location
    

class DealBuilderCreateForm(DealBuilderForm):
    ret_url=forms.CharField(widget=forms.HiddenInput,required=False)
            

class DealBuilderUpdateForm(DealBuilderForm):
    ret_url=forms.CharField(widget=forms.HiddenInput,required=False)
    current_page=forms.CharField(widget=forms.HiddenInput,required=False)
    

class DealStatsForm(forms.Form):    
    orderBy = forms.ChoiceField(choices=[('totalClicks', 'Clicks 30D'), ('totalDeals', 'Deals 30D'), ('followers', 'Followers'), ],
                                   widget=forms.Select(
                                   attrs={"id":"orderBy", "onchange":"dealStatsSort()"}), required=True)
    pagination = forms.ChoiceField(choices=view_const.LIST_PAGINATE,
                                   widget=forms.Select(
                                   attrs={"id":"pagination", "onchange":"dealStatsSort()"}), required=True)
    
    def __init__( self, *args, **kwargs ):
        super(DealStatsForm, self ).__init__( *args, **kwargs )
        choices = deal_const.SPECIAL_LOCATIONS
        cities = list(DealSourceApi.get_all_deal_locations())
        cities.sort()
        for location in cities:
            choices.append((location,location))
        
        self.fields['location'] = forms.ChoiceField(choices=choices,
                                   widget=forms.Select(
                                   attrs={"id":"location","onchange":"dealStatsSort()"}),required=True)
        
        choices = deal_const.SPECIAL_CATEGORIES
        cats = deal_const.TOPIC_2_GROUPON_CATEGORY_MAP.keys()
        cats.sort()
        for cat in cats:
            choices.append((str_util.name_2_key(cat),cat))
        
        self.fields['cat'] = forms.ChoiceField(choices=choices,
                                   widget=forms.Select(
                                   attrs={"id":"cat","onchange":"dealStatsSort()"}),required=True)