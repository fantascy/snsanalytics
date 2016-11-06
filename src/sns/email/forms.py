from django import forms

from sns.core.core import EmailCampaignParent
from sns.view.baseform import NoNameBaseForm, NameMultipleChoiceField
from sns.api import consts as api_const
from sns.view import consts as view_const

from sns.camp.forms import CampaignForm
from sns.camp import consts as camp_const
from sns.email import consts as mail_const
from sns.email.models import EmailList, EmailContact, EmailTemplate, DynamicEmailList, DefaultSystemEmailList


class EmailContactForm(NoNameBaseForm):
    
    def __init__(self, *args, **kwargs):
        super(EmailContactForm, self ).__init__( *args, **kwargs )
        mail_list=[]
        temp = EmailList.all().filter('type <', mail_const.MAIL_LIST_TYPE_SYSTEMLIST).filter('deleted =', False).ancestor(EmailCampaignParent.get_or_insert_parent())
        for k in temp:
            mail_list.append((k.id,k.name))
        self.fields['parent'] = forms.ChoiceField(choices=mail_list,widget=forms.Select(),required=True)
            
    email = forms.CharField(widget=forms.TextInput(attrs={'size':'30'}),max_length=256,required=True)
    fullName = forms.CharField(widget=forms.TextInput(attrs={'size':'30'}),max_length=30,required=True)
    firstName = forms.CharField(widget=forms.TextInput(attrs={'size':'30'}),max_length=30)
    lastName = forms.CharField(widget=forms.TextInput(attrs={'size':'30'}),max_length=30)
        
    def api_module(self):
        return api_const.API_M_MAIL_CONTACT


class EmailContactCreateForm(EmailContactForm):
    pass    
   
        
class EmailContactUpdateForm(EmailContactForm):
    id = forms.CharField(widget=forms.HiddenInput)
    

class EmailListForm(NoNameBaseForm):
    #passwd=forms.CharField(max_length=40, required=False)
    name = forms.CharField(widget=forms.TextInput(attrs={'size':'30'}),max_length=30,required=True)
    type = forms.ChoiceField(choices=[(mail_const.MAIL_LIST_TYPE_NORMAL,"normal"),(mail_const.MAIL_LIST_TYPE_BLACKLIST,"blacklist"),(mail_const.MAIL_LIST_TYPE_WHITELIST,"whitelist"),(mail_const.MAIL_LIST_TYPE_ADMINLIST,"adminlist")],
                                   widget=forms.Select(),required=True)
    
    def api_module(self):
        return api_const.API_M_MAIL_LIST
    
class EmailListCreateForm(EmailListForm):
    pass    
 
        
class EmailListUpdateForm(EmailListForm):
    id = forms.CharField(widget=forms.HiddenInput)
       
    
class EmailTemplateForm(NoNameBaseForm):
    
    def __init__(self, *args, **kwargs):
        super(EmailTemplateForm, self ).__init__( *args, **kwargs )
                
    name = forms.CharField(widget=forms.TextInput(attrs={'size':'50'}),max_length=300,required=True)
    subject = forms.CharField(widget=forms.TextInput(attrs={'size':'50'}),max_length=140,required=True)
    textBody = forms.CharField(widget=forms.Textarea(attrs={'cols':'77','rows':'8'}),required=False)
    types = []
    types.append((mail_const.MAIL_TEMPLATE_TYPE_GENERAL, 'General Marketing'))
    types.append((mail_const.MAIL_TEMPLATE_TYPE_NEWSLETTER, 'Newsletter'))
    types.append((mail_const.MAIL_TEMPLATE_TYPE_REPORT, 'Report'))
    type = forms.ChoiceField(choices=types, widget=forms.Select(), required=False)
    
    def api_module(self):
        return api_const.API_M_MAIL_TEMPLATE


class EmailTemplateUpdateForm(EmailTemplateForm):
    id = forms.CharField(widget=forms.HiddenInput)
    
    
class EmailTemplateSendForm(EmailTemplateForm):
    
    def __init__(self, *args, **kwargs):
        super(EmailTemplateSendForm, self ).__init__( *args, **kwargs )
        
        include_list=[]
        temp = EmailList.all().filter('type =', mail_const.MAIL_LIST_TYPE_NORMAL).filter('deleted =', False).ancestor(EmailCampaignParent.get_or_insert_parent())
        for j in temp:
            include_list.append((j.id,j.name))
        DSMLKN = DynamicEmailList.keyName('defaultSystemEmailList')
        defaultSystemEmailList = DefaultSystemEmailList.get_or_insert(key_name=DSMLKN, parent=EmailCampaignParent.get_or_insert_parent(), name='defaultSystemEmailList',nameLower='defaultSystemEmailList'.lower(), type=mail_const.MAIL_LIST_TYPE_SYSTEMLIST)
        include_list.append((defaultSystemEmailList.id,defaultSystemEmailList.name))
        self.fields['include'] = NameMultipleChoiceField(choices=include_list)
        
        exclude_list=[]
        tempp = EmailList.all().filter('type =', mail_const.MAIL_LIST_TYPE_BLACKLIST).filter('deleted = ' ,False).ancestor(EmailCampaignParent.get_or_insert_parent())
        for l in tempp:
            exclude_list.append((l.id,l.name))
        self.fields['exclude'] = forms.MultipleChoiceField(choices=exclude_list, required=False)
        
        
        sender_list=[]
        parents = EmailList.all().filter('type =', mail_const.MAIL_LIST_TYPE_ADMINLIST).filter('deleted = ' ,False).ancestor(EmailCampaignParent.get_or_insert_parent())
        for parent in parents:
            temppp = EmailContact.all().ancestor(parent)
            for m in temppp:
                sender_list.append((unicode(m.fullName)+unicode('<'+m.email+'>'), unicode(m.fullName)+unicode('<'+m.email+'>')))
        
        actualRecipient_list=[]
        actualRecipient_list.append((mail_const.NONE_MAIL_ACTUAL_RECIPIENT,"No ActualRecipient"))
        actualRecipient_list  = actualRecipient_list + sender_list
        self.fields['actualRecipient'] = forms.ChoiceField(choices=actualRecipient_list, widget=forms.Select(), required=False)
    
    id = forms.CharField(widget=forms.HiddenInput)      
        

class EmailTemplateCreateForm(EmailTemplateForm):
    pass

  
class EmailListUploadForm(NoNameBaseForm):
    
    def __init__(self, *args, **kwargs):
        super(EmailListUploadForm, self ).__init__( *args, **kwargs )
        mail_list=[]
        temp = EmailList.all().filter('type <', mail_const.MAIL_LIST_TYPE_SYSTEMLIST).filter('deleted =', False).ancestor(EmailCampaignParent.get_or_insert_parent())
        for k in temp:
            mail_list.append((k.id,k.name))
        self.fields['list'] = forms.ChoiceField(choices=mail_list,widget=forms.Select(
                                   attrs={"onchange":"getAjaxUploadProcessor('/email/list/importFromCSV/')"}))
    file = forms.FileField()
  
        
class EmailCampaignForm(CampaignForm):
    
    def __init__(self, *args, **kwargs):
        super(EmailCampaignForm, self ).__init__( *args, **kwargs )
        
        mail_list=[]
        temp = EmailTemplate.all().filter('deleted =', False).ancestor(EmailCampaignParent.get_or_insert_parent())
        for k in temp:
            mail_list.append((k.id, k.name))
        self.fields['param'] = forms.ChoiceField(choices=mail_list,widget=forms.Select(),required=True)
            
        interval_candidates=[]
        for i in camp_const.SCHEDULE_ARTICLE_POSTING_INTERVALS:
            interval_candidates.append((i,camp_const.INTERVAL_MAP[i]))
        self.fields['scheduleInterval']=forms.ChoiceField(choices=interval_candidates,required=False)
        
        
        include_list=[]
        temp = EmailList.all().filter('type =', mail_const.MAIL_LIST_TYPE_NORMAL).filter('deleted =', False).ancestor(EmailCampaignParent.get_or_insert_parent())
        for j in temp:
            include_list.append((j.id,j.name))
        DSMLKN = DynamicEmailList.keyName('defaultSystemEmailList')
        defaultSystemEmailList = DefaultSystemEmailList.get_or_insert(key_name=DSMLKN, parent=EmailCampaignParent.get_or_insert_parent(), name='defaultSystemEmailList', nameLower='defaultSystemEmailList'.lower(), type=mail_const.MAIL_LIST_TYPE_SYSTEMLIST)
        include_list.append((defaultSystemEmailList.id,defaultSystemEmailList.name))
        self.fields['toLists'] = forms.MultipleChoiceField(choices=include_list, required=False)
        
        exclude_list=[]
        tempp = EmailList.all().filter('type =', mail_const.MAIL_LIST_TYPE_BLACKLIST).filter('deleted = ' ,False).ancestor(EmailCampaignParent.get_or_insert_parent())
        for l in tempp:
            exclude_list.append((l.id,l.name))
        self.fields['toBlacklists'] = forms.MultipleChoiceField(choices=exclude_list, required=False)
        
        sender_list=[]
        parents = EmailList.all().filter('type =', mail_const.MAIL_LIST_TYPE_ADMINLIST).filter('deleted = ' ,False).ancestor(EmailCampaignParent.get_or_insert_parent())
        for parent in parents:
            temppp = EmailContact.all().ancestor(parent)
            for m in temppp:
                sender_list.append((unicode(m.fullName)+unicode('<'+m.email+'>'), unicode(m.fullName)+unicode('<'+m.email+'>')))
        self.fields['sender'] = forms.ChoiceField(choices=sender_list,widget=forms.Select(), required=True)
        
        actualRecipient_list=[]
        actualRecipient_list.append((mail_const.NONE_MAIL_ACTUAL_RECIPIENT,"No ActualRecipient"))
        actualRecipient_list  = actualRecipient_list + sender_list
        self.fields['actualRecipient'] = forms.ChoiceField(choices=actualRecipient_list, widget=forms.Select(), required=False)
        
    def api_module(self):
        return api_const.API_M_MAIL_CAMPAIGN
 
    
class EmailCampaignUpdateForm(EmailCampaignForm):
    ret_url=forms.CharField(widget=forms.HiddenInput,required=False)
    id = forms.CharField(widget=forms.HiddenInput)


class EmailCampaignCreateForm(EmailCampaignForm):
    ret_url=forms.CharField(widget=forms.HiddenInput,required=False)
    pass


class EmailCampaignSortByForm(forms.Form):    
    type = forms.ChoiceField(choices=[('nameLower','Name')],
                                   widget=forms.Select(
                                   attrs={"id":"id_sortBy_type","name":"id_sortBy_type","onchange":"sortByKeyWord()"}),required=True)
    order = forms.ChoiceField(choices=view_const.LIST_ORDER,
                                   widget=forms.Select(
                                   attrs={"id":"id_direct_type","name":"id_direct_type","onchange":"sortByKeyWord()"}),required=True)
    paginate = forms.ChoiceField(choices=view_const.LIST_PAGINATE,
                                   widget=forms.Select(
                                   attrs={"id":"id_paginate_num","name":"id_paginate_num","onchange":"sortByKeyWord()"}),required=True)
        
        
class EmailListSortByForm(forms.Form):    
    type = forms.ChoiceField(choices=[('type','Type')],
                                   widget=forms.Select(
                                   attrs={"id":"id_sortBy_type","name":"id_sortBy_type","onchange":"sortByKeyWord()"}),required=True)
    order = forms.ChoiceField(choices=view_const.LIST_ORDER,
                                   widget=forms.Select(
                                   attrs={"id":"id_direct_type","name":"id_direct_type","onchange":"sortByKeyWord()"}),required=True)
    paginate = forms.ChoiceField(choices=view_const.LIST_PAGINATE,
                                   widget=forms.Select(
                                   attrs={"id":"id_paginate_num","name":"id_paginate_num","onchange":"sortByKeyWord()"}),required=True)

'''TODO:sorted by name(first,last,full)'''
class EmailContactSortByForm(forms.Form):    
    type = forms.ChoiceField(choices=[('email','Email')],
                                   widget=forms.Select(
                                   attrs={"id":"id_sortBy_type","name":"id_sortBy_type","onchange":"sortByKeyWord()"}),required=True)
    order = forms.ChoiceField(choices=view_const.LIST_ORDER,
                                   widget=forms.Select(
                                   attrs={"id":"id_direct_type","name":"id_direct_type","onchange":"sortByKeyWord()"}),required=True)
    paginate = forms.ChoiceField(choices=view_const.LIST_PAGINATE,
                                   widget=forms.Select(
                                   attrs={"id":"id_paginate_num","name":"id_paginate_num","onchange":"sortByKeyWord()"}),required=True)
          
            
class EmailTemplateSortByForm(forms.Form):    
    type = forms.ChoiceField(choices=[('nameLower','Name')],
                                   widget=forms.Select(
                                   attrs={"id":"id_sortBy_type","name":"id_sortBy_type","onchange":"sortByKeyWord()"}),required=True)
    order = forms.ChoiceField(choices=view_const.LIST_ORDER,
                                   widget=forms.Select(
                                   attrs={"id":"id_direct_type","name":"id_direct_type","onchange":"sortByKeyWord()"}),required=True)
    paginate = forms.ChoiceField(choices=view_const.LIST_PAGINATE,
                                   widget=forms.Select(
                                   attrs={"id":"id_paginate_num","name":"id_paginate_num","onchange":"sortByKeyWord()"}),required=True)
            
        
        