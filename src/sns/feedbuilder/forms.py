from sns.view.baseform import BaseForm
from django import forms
from sns.view.baseform import NameModelMultipleChoiceField
from sns.api.facade import iapi
from google.appengine.ext import db
from models import FeedBuilder
from sns.api import consts as api_const
from sns.view import consts as view_const


class FeedBuilderForm(BaseForm):
    uri =forms.CharField(widget=forms.TextInput(attrs={
                             'size':'15'}),max_length=20,required=False)
    def __init__( self, *args, **kwargs ):
        super(FeedBuilderForm, self ).__init__( *args, **kwargs )
        
        self.fields['feeds'] = NameModelMultipleChoiceField(queryset=iapi(api_const.API_M_FEED).query_base().order('name'), label_attr='name',
                                                               widget=forms.SelectMultiple(attrs={}),required=True)
    def api_module(self):
        return api_const.API_M_FEED_BUILDER
    
    def clean_uri(self):
        value =  self.cleaned_data['uri'].lower()
        if not value.isalnum():
            raise forms.ValidationError('All characters in URL must be alphanumeric!')
        try:
            id = self.data['id']
            obj = db.get(id)
            if obj.uri == value:
                return value
        except:
            pass
        builder = FeedBuilder.all().filter('uri', value).filter('deleted', False).fetch(limit=1)
        if len(builder) > 0 :
            raise forms.ValidationError("The Feed URL is not available, please choose a different one.")
        else:
            return value
           
    def clean_feeds(self):
        feeds = self.cleaned_data['feeds']
        if len(feeds) > 5:
            raise forms.ValidationError('You can not choose more than 5 feeds!')
        else:
            return feeds

class FeedBuilderCreateForm(FeedBuilderForm):
    ret_url=forms.CharField(widget=forms.HiddenInput,required=False)
            

class FeedBuilderUpdateForm(FeedBuilderForm):
    id=forms.CharField(widget=forms.HiddenInput)
    ret_url=forms.CharField(widget=forms.HiddenInput,required=False)
    current_page=forms.CharField(widget=forms.HiddenInput,required=False)
    

class FeedBuilderSortByForm(forms.Form):    
    type = forms.ChoiceField(choices=[('nameLower',"Name")],
                                   widget=forms.Select(
                                   attrs={"id":"id_sortBy_type","name":"id_sortBy_type","onchange":"sortByKeyWord()"}),required=True)
    order = forms.ChoiceField(choices=view_const.LIST_ORDER,
                                   widget=forms.Select(
                                   attrs={"id":"id_direct_type","name":"id_direct_type","onchange":"sortByKeyWord()"}),required=True)
    paginate = forms.ChoiceField(choices=view_const.LIST_PAGINATE,
                                   widget=forms.Select(
                                   attrs={"id":"id_paginate_num","name":"id_paginate_num","onchange":"sortByKeyWord()"}),required=True)
