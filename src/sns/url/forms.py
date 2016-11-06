'''
Created on 2010-3-29

@author: alanxing
'''
from django import forms
from sns.view.baseform import NoNameBaseForm
from sns.api import consts as api_const


class RedirectForm(forms.Form):
    url = forms.CharField(widget=forms.HiddenInput)
    urlHash = forms.CharField(widget=forms.HiddenInput)
    username = forms.CharField(widget=forms.HiddenInput)
    country = forms.CharField(widget=forms.HiddenInput)
    referrer = forms.CharField(widget=forms.HiddenInput)
    type = forms.CharField(widget=forms.HiddenInput)
    

class EmailRedirectForm(RedirectForm):
    cid = forms.CharField(widget=forms.HiddenInput)
    mid = forms.CharField(widget=forms.HiddenInput)
    

class WebSiteForm(NoNameBaseForm):
    includedKeys = forms.CharField(widget=forms.TextInput(attrs={'size':'50'}), required=False)    
    excludedKeys = forms.CharField(widget=forms.TextInput(attrs={'size':'50'}), required=False)
    
    def api_module(self):
        return api_const.API_M_WEBSITE
    
class WebSiteCreateForm(WebSiteForm):
    domain = forms.CharField(widget=forms.TextInput(attrs={'size':'50'}))       

class WebSiteUpdateForm(WebSiteForm):
    id=forms.CharField(widget=forms.HiddenInput)
    
class WebSiteUploadForm(NoNameBaseForm):
    file = forms.FileField()
