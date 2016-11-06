from string import atoi
from django import forms

import context
from common.utils import consts
from common.utils import url as url_util
from sns.view.baseform import NoNameBaseForm
from sns.api import consts as api_const
from sns.view import consts as view_const

class MessageForm(NoNameBaseForm):
    url  = forms.CharField(max_length=url_util.MAX_URL_LENGTH, widget=forms.TextInput(attrs={'size':'50'}),required=False)
    msg=forms.CharField(max_length=consts.FACEBOOK_MSG_LENGTH_LIMIT,widget=forms.Textarea(attrs={'cols':'50','rows':'4'}),required=True)
    type = forms.ChoiceField(choices=[(0,"Twitter"),(1,"Facebook")],
                                   widget=forms.Select(
                                   attrs={"onchange":"chooseMsgType(this)"}),required=False)
    
    
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
        
    def clean_msg(self):
        msg=self.data['msg']
        url=self.data['url']
        type= atoi(self.data['type'])
        if type== 0:
            len_limit = 140
        elif type == 1:
            len_limit = consts.FACEBOOK_MSG_LENGTH_LIMIT
        else:
            len_limit = 140
        if url:
            max_length=len_limit - context.get_context().short_url_length()
            if len(msg)>max_length:
                raise forms.ValidationError('Ensure this value has at most %d characters (it has %d).'%(max_length,len(msg)))            
            return msg
        else:
            max_length=len_limit
            if len(msg)>max_length:
                raise forms.ValidationError('Ensure this value has at most %d characters (it has %d).'%(max_length,len(msg)))   
            return msg  
        

    def api_module(self):
        return api_const.API_M_ARTICLE


class MessageCreateForm(MessageForm):
    pass
    
class MessageUpdateForm(MessageForm):
    id=forms.CharField(widget=forms.HiddenInput)
    
class MessageSortByForm(forms.Form):    
    type = forms.ChoiceField(choices=[('msgLower',"Message"),('modifiedTime',"Last modified time")],
                                   widget=forms.Select(
                                   attrs={"id":"id_sortBy_type","name":"id_sortBy_type","onchange":"sortByKeyWord()"}),required=True)
    order = forms.ChoiceField(choices=view_const.LIST_ORDER,
                                   widget=forms.Select(
                                   attrs={"id":"id_direct_type","name":"id_direct_type","onchange":"sortByKeyWord()"}),required=True)
    paginate = forms.ChoiceField(choices=view_const.LIST_PAGINATE,
                                   widget=forms.Select(
                                   attrs={"id":"id_paginate_num","name":"id_paginate_num","onchange":"sortByKeyWord()"}),required=True)

    
