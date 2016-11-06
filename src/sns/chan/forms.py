from django import forms
from sns.api.facade import iapi
from sns.api import consts as api_const
from sns.view.baseform import BaseForm,NoNameBaseForm,NameModelMultipleChoiceField,NameMultipleChoiceField
from sns.cont.message.forms import MessageForm
from sns.view import consts as view_const
import logging

class ChannelForm(NoNameBaseForm):
    keywords=forms.CharField(widget=forms.TextInput(attrs={'size':'80'}),max_length=100,required=False)

    def api_module(self):
        return api_const.API_M_CHANNEL
        
    
class ChannelUpdatePasswdForm(ChannelForm):
    id = forms.CharField(widget=forms.HiddenInput)
    login = forms.CharField(widget=forms.HiddenInput)
    avatarAcc_url = forms.CharField(widget=forms.HiddenInput)
    callback = forms.CharField(widget=forms.HiddenInput)
    

class ChannelUpdateForm(ChannelForm):
    id = forms.CharField(widget=forms.HiddenInput)
    callback = forms.CharField(widget=forms.HiddenInput)

class FChannelUpdateForm(ChannelUpdateForm):
    
    def api_module(self):
        return api_const.API_M_FCHANNEL
    
class PageChannelUpdateForm(ChannelForm):
    id = forms.CharField(widget=forms.HiddenInput)
    
    def api_module(self):
        return api_const.API_M_FBPAGE
    
class ChannelCreateForm(ChannelForm):
    login = forms.CharField(widget=forms.TextInput(attrs={'size':'30'}),max_length=30,required=True)
    

class ChannelDetailsForm(forms.Form):
    type = forms.ChoiceField(choices=[(0,"DM inbox"),(1,"DM outbox"),(2,"Home tweets")
                                           ,(3,"Mentions"),(4,"Followers"),(5,"Followings"),(6,"Sent tweets"),
                                           (7,"RTs by others"),
                                           (8,"RTs by self"),
                                           (9,"Tweets being RTed"),
                                           (10,"Favorites"),],
                                   widget=forms.Select(
                                   attrs={"onchange":"chooseChannalDetailType(this)","class":"retro loadChannelDetail"}),required=True)
    
class ChannelReplyDMForm(MessageForm):   
    def __init__( self, *args, **kwargs ):
        super(ChannelReplyDMForm, self ).__init__( *args, **kwargs )
        self.fields['channels'] = NameModelMultipleChoiceField(queryset=iapi(api_const.API_M_CHANNEL).query_base().order('nameLower'), label_attr='name')
        logging.debug("reply form channels:%s" % iapi(api_const.API_M_CHANNEL).query_base().order('nameLower')[0].id)

    uid=forms.CharField(widget=forms.HiddenInput)
    avatarUrl=forms.CharField(widget=forms.HiddenInput)
    type=forms.CharField(widget=forms.HiddenInput)
    
    fbName = forms.CharField(required=False)
    fbDescription = forms.CharField(required=False)
    fbPicture=forms.CharField(widget=forms.HiddenInput,required=False)
    
class ChannelReweetForm(forms.Form):   
    def __init__( self, *args, **kwargs ):        
        super(ChannelReweetForm, self ).__init__( *args, **kwargs )
        query=iapi(api_const.API_M_CHANNEL).query_base().order('nameLower').fetch(limit=1000)
        channels=[]
        if 'initial' in kwargs:
            if 'channel' in kwargs['initial']:
                except_channel_list=kwargs['initial']['channel']
            elif 'channel_string' in kwargs['initial']:
                except_channel_list=eval(kwargs['initial']['channel_string'])
        
        for channel in query:
            is_exception=False
            for except_channel in except_channel_list:
                if channel.name == except_channel:
                    is_exception = True
            if not is_exception:
                channels.append(( channel.id,channel.name))
        
        self.fields['channels'] = NameMultipleChoiceField(choices=channels, label_attr='name')
      
    uid=forms.CharField(widget=forms.HiddenInput)
    avatarUrl=forms.CharField(widget=forms.HiddenInput)
    type=forms.CharField(widget=forms.HiddenInput) 
    msg=forms.CharField(widget=forms.HiddenInput)
    id=forms.CharField(widget=forms.HiddenInput)
    channel=forms.CharField(widget=forms.HiddenInput)

class ChannelSendDM(MessageForm): 
    uid=forms.CharField(widget=forms.HiddenInput)
    avatarUrl=forms.CharField(widget=forms.HiddenInput)
    type=forms.CharField(widget=forms.HiddenInput)
    
    fbName = forms.CharField(required=False)
    fbDescription = forms.CharField(required=False)
    fbPicture=forms.CharField(widget=forms.HiddenInput,required=False)
    
class ChannelSortByForm(forms.Form):    
    type = forms.ChoiceField(choices=[('nameLower','Twitter Account'),('modifiedTime','Last modified time')],
                                   widget=forms.Select(
                                   attrs={"id":"id_sortBy_type","name":"id_sortBy_type","onchange":"sortByKeyWord()"}),required=True)
   
    order = forms.ChoiceField(choices=view_const.LIST_ORDER,
                                   widget=forms.Select(
                                   attrs={"id":"id_direct_type","name":"id_direct_type","onchange":"sortByKeyWord()"}),required=True)
    paginate = forms.ChoiceField(choices=view_const.LIST_PAGINATE,
                                   widget=forms.Select(
                                   attrs={"id":"id_paginate_num","name":"id_paginate_num","onchange":"sortByKeyWord()"}),required=True)
    
class FChannelSortByForm(forms.Form):    
    type = forms.ChoiceField(choices=[('nameLower','Facebook Account'),('modifiedTime','Last modified time')],
                                   widget=forms.Select(
                                   attrs={"id":"id_sortBy_type","name":"id_sortBy_type","onchange":"sortByKeyWord()"}),required=True)
    order = forms.ChoiceField(choices=view_const.LIST_ORDER,
                                   widget=forms.Select(
                                   attrs={"id":"id_direct_type","name":"id_direct_type","onchange":"sortByKeyWord()"}),required=True)
    paginate = forms.ChoiceField(choices=view_const.LIST_PAGINATE,
                                   widget=forms.Select(
                                   attrs={"id":"id_paginate_num","name":"id_paginate_num","onchange":"sortByKeyWord()"}),required=True)
    
class PageChannelSortByForm(forms.Form):    
    type = forms.ChoiceField(choices=[('nameLower','Facebook Page')],
                                   widget=forms.Select(
                                   attrs={"id":"id_sortBy_type","name":"id_sortBy_type","onchange":"sortByKeyWord()"}),required=True)
    order = forms.ChoiceField(choices=view_const.LIST_ORDER,
                                   widget=forms.Select(
                                   attrs={"id":"id_direct_type","name":"id_direct_type","onchange":"sortByKeyWord()"}),required=True)
    paginate = forms.ChoiceField(choices=view_const.LIST_PAGINATE,
                                   widget=forms.Select(
                                   attrs={"id":"id_paginate_num","name":"id_paginate_num","onchange":"sortByKeyWord()"}),required=True)

class SuspendedTwitterSortByForm(forms.Form):    
    type = forms.ChoiceField(choices=[('modifiedTime','Status Modified Time'),('nameLower','Twitter Account'),('userEmail','User Email')],
                                   widget=forms.Select(
                                   attrs={"id":"id_sortBy_type","name":"id_sortBy_type","onchange":"sortByKeyWord()"}),required=True)
    order = forms.ChoiceField(choices=[('desc','Descending'),('asc','Ascending')],
                                   widget=forms.Select(
                                   attrs={"id":"id_direct_type","name":"id_direct_type","onchange":"sortByKeyWord()"}),required=True)
    paginate = forms.ChoiceField(choices=view_const.LIST_PAGINATE,
                                   widget=forms.Select(
                                   attrs={"id":"id_paginate_num","name":"id_paginate_num","onchange":"sortByKeyWord()"}),required=True)        
                
  
class FchannelPageForm(BaseForm):
    def __init__( self, fchannels ,*args, **kwargs ):
        super(BaseForm, self ).__init__( *args, **kwargs )
        choices=[]
        for c in fchannels:
            choices.append((c.id,c.name))
        self.fields['fchannels'] = forms.ChoiceField(choices=choices,widget=forms.Select(
                                   attrs={"id":"fchannels","onchange":"chooseTheFchannel(this)"}),required=False)
        
class FchannelAppForm(BaseForm):
    def __init__( self, apps ,*args, **kwargs ):
        super(BaseForm, self ).__init__( *args, **kwargs )
        choices=[]
        for c in apps:
            choices.append((c['app_id'],c['display_name']))
        self.fields['apps'] = forms.ChoiceField(choices=choices,widget=forms.Select(
                                   attrs={"id":"apps","onchange":"chooseTheFchannel(this)"}),required=False)
        
class FanPageForm(BaseForm):
    showHidden = forms.BooleanField(widget=forms.CheckboxInput(attrs={'onclick':'changePageShow(this)','id':'showHidden'}),
                                   required=False)
       
class MemberGroupForm(BaseForm):
    showHidden = forms.BooleanField(widget=forms.CheckboxInput(attrs={'onclick':'changeGroupShow(this)','id':'showHidden'}),
                                   required=False)
