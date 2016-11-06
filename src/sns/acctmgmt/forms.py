from django import forms
from sns.api import consts as api_const
from sns.view.baseform import NoNameBaseForm
from sns.acctmgmt import consts as acctmgmt_const
from sns.view import consts as view_const


class CmpAccountUploadForm(NoNameBaseForm):
    file = forms.FileField()


class CmpAccountPwduploadForm(NoNameBaseForm):
    file = forms.FileField()


class YahooForm(NoNameBaseForm):
    num = forms.CharField(widget=forms.TextInput(attrs={'size':'10'}), max_length=10)
    name = forms.CharField(widget=forms.TextInput(attrs={'size':'20'}), max_length=30, required=True)
    state = forms.ChoiceField(choices=acctmgmt_const.YAHOO_STATE_CHOICES, widget=forms.Select(), required=True)
    password = forms.CharField(widget=forms.TextInput(attrs={'size':'20'}), max_length=20, required=True)
    passwordClue = forms.CharField(widget=forms.TextInput(attrs={'size':'20'}), max_length=30, required=True)
    oldPassword = forms.CharField(widget=forms.TextInput(attrs={'size':'20'}), max_length=20)
    newPassword = forms.CharField(widget=forms.TextInput(attrs={'size':'20'}), max_length=20)
    lastLoginTime = forms.DateField(widget=forms.DateInput(
                                            attrs={'size':'25',
                                             "class":'Wdate',
                                             "onfocus":"WdatePicker({dateFmt:'yyyy-MM-dd',lang:'en'})"}))
    lastPasswdChangeTime = forms.DateField(widget=forms.DateInput(
                                            attrs={'size':'25',
                                             "class":'Wdate',
                                             "onfocus":"WdatePicker({dateFmt:'yyyy-MM-dd',lang:'en'})"}))
    tHandle = forms.CharField(widget=forms.TextInput(attrs={'size':'20'}), max_length=20)
    tPassword = forms.CharField(widget=forms.TextInput(attrs={'size':'20'}), max_length=20)
    tOldPassword = forms.CharField(widget=forms.TextInput(attrs={'size':'20'}), max_length=20)
    tNewPassword = forms.CharField(widget=forms.TextInput(attrs={'size':'20'}), max_length=20)
    tState = forms.ChoiceField(choices=acctmgmt_const.TWITTER_STATE_CHOICES, widget=forms.Select(), required=True)
    tLastLoginTime = forms.DateField(widget=forms.DateInput(
                                            attrs={'size':'25',
                                             "class":'Wdate',
                                             "onfocus":"WdatePicker({dateFmt:'yyyy-MM-dd',lang:'en'})"}))
    tLastPasswdChangeTime = forms.DateField(widget=forms.DateInput(
                                            attrs={'size':'25',
                                             "class":'Wdate',
                                             "onfocus":"WdatePicker({dateFmt:'yyyy-MM-dd',lang:'en'})"}))

    def api_module(self):
        return api_const.API_M_ACCTMGMT_YAHOO
        

class YahooUpdateForm(YahooForm):
    id = forms.CharField(widget=forms.HiddenInput)
    

class YahooCreateForm(YahooForm):
    pass

    
class YahooSortByForm(forms.Form):    
    type = forms.ChoiceField(choices=[('nameLower','Yahoo Account'),('state','State'),('modifiedTime','Last Modified Time'),],
                                   widget=forms.Select(
                                   attrs={"id":"id_sortBy_type","name":"id_sortBy_type","onchange":"sortByKeyWord()"}),required=True)
    order = forms.ChoiceField(choices=view_const.LIST_ORDER,
                                   widget=forms.Select(
                                   attrs={"id":"id_direct_type","name":"id_direct_type","onchange":"sortByKeyWord()"}),required=True)
    paginate = forms.ChoiceField(choices=view_const.LIST_PAGINATE,
                                   widget=forms.Select(
                                   attrs={"id":"id_paginate_num","name":"id_paginate_num","onchange":"sortByKeyWord()"}),required=True)
