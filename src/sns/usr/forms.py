from django import forms

from sns.api import consts as api_const
from sns.core.core import get_user
from sns.view.baseform import BaseForm,NoNameBaseForm
from common.utils import timezone as ctz_util

class UserForm(BaseForm):
    timeZone = forms.ChoiceField(required=False, label='Time Zone', choices=ctz_util.TZ_LIST)
    acceptedTerms = forms.BooleanField(widget=forms.CheckboxInput(), required=True)
    subSystemNotification  = forms.BooleanField(widget=forms.CheckboxInput(), required=False)
    subNewsletter   = forms.BooleanField(widget=forms.CheckboxInput(), required=False)
    subWeeklyReport = forms.BooleanField(widget=forms.CheckboxInput(), required=False)
    
    def __init__( self, *args, **kwargs ):
        super(BaseForm, self ).__init__( *args, **kwargs )
        self.fields['id']=forms.CharField(widget=forms.HiddenInput,initial=get_user().id)

    def api_module(self):
        return api_const.API_M_USER
        
        
class UserBlackListForm(NoNameBaseForm):
    listValue = forms.CharField(widget=forms.TextInput(attrs={'size':'60'}),required=False)
 

class UserCountForm(NoNameBaseForm):
    type = forms.ChoiceField(choices=[("year","year"),("month","month"),("week","week"),("day","day")], initial="month",
                                   widget=forms.Select(
                                   attrs={"onchange":"chooseUserCount(this)","class":"retro loadUserCount"}),required=True)
    

class UserDateForm(NoNameBaseForm):
    type = forms.ChoiceField(choices=[("first","first visit"),("last","last visit")],
                                   widget=forms.Select(
                                   attrs={"onchange":"chooseUserDate(this)","class":"retro loadUserDate"}),required=True)

    
class UserTagForm(NoNameBaseForm):
    tags = forms.CharField(widget=forms.TextInput(attrs={'size':'30','id':'user-tag'}))