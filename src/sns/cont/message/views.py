from django.template import RequestContext
from django.http import HttpResponse
from django.shortcuts import render_to_response

import context
from common.utils import string as str_util
from sns.api import consts as api_const
from sns import limits as limit_const
from common.utils import consts
from sns.view.baseview import BaseView
from sns.cont.api import MSG_LENGTH_60,MSG_LENGTH_80,MSG_LENGTH_100,MessageProcessor
from sns.cont.message.forms import MessageCreateForm,MessageUpdateForm,MessageSortByForm
from sns.cont.views import ContentControllerView
from sns.cont.models import Message
from sns.core.core import ContentParent
import json


class MessageControllerView(ContentControllerView):
    pass


class MessageView(BaseView,MessageControllerView):
    def __init__(self,left_length=140):
        BaseView.__init__(self,api_const.API_M_ARTICLE,MessageCreateForm,MessageUpdateForm)
        MessageControllerView.__init__(self)
        self.left_length=left_length
        
    def order_field(self):
        return "msgLower"

    def titleList(self):
        return "Messages"
    
    def titleCreate(self):
        return "Add Message"
    
    def titleUpdate(self):
        return "Modify Message"
    
    def titleDetail(self):
        return "Message Details"

    def create(self, request, view, template_name="form.html",ret_url = None,extra_params={}):
        r"""
        temlate
            template path
        """
        if request.method=="GET":
            form=self.initiate_create_form(request) # An unbound form
        elif request.method=='POST':
            form=self.create_form_class(request.POST)
            if form.is_valid():
                form.cleaned_data['msgShort60']=str_util.slice_double_byte_character_set(form.cleaned_data['msg'],MSG_LENGTH_60)
                form.cleaned_data['msgShort80']=str_util.slice_double_byte_character_set(form.cleaned_data['msg'],MSG_LENGTH_80)
                form.cleaned_data['msgShort100']=str_util.slice_double_byte_character_set(form.cleaned_data['msg'],MSG_LENGTH_100)
                self.create_object(form)
                return HttpResponse('Success')
                
        params={'form': form, 'view' : view, 'title' : self.titleCreate()}
        params.update(extra_params)
        return render_to_response('sns/' +self.api_module_name+'/'+template_name, 
                                   params,
                                   context_instance=RequestContext(request,{"path":request.path}))
        
    def update(self, request, view, template_name="form.html", ret_url = None, extra_params={}):
        if request.method=="GET":
            form=self.read_object(request)
        elif request.method=='POST':
            form=self.update_form_class(request.POST)      
            if form.is_valid():
                params=form.cleaned_data.copy()
                form.cleaned_data['msgShort60']=str_util.slice_double_byte_character_set(form.cleaned_data['msg'],MSG_LENGTH_60)
                form.cleaned_data['msgShort80']=str_util.slice_double_byte_character_set(form.cleaned_data['msg'],MSG_LENGTH_80)
                form.cleaned_data['msgShort100']=str_util.slice_double_byte_character_set(form.cleaned_data['msg'],MSG_LENGTH_100)                
                self.update_object(form)  
                
                params['page_title']='article_list_update'
                data=json.dumps(params)
                return HttpResponse(data, mimetype='application/javascript')              
   
        params = {'form': form, 'view' : view, 'title' : self.titleUpdate() }
        params.update(extra_params)
        return render_to_response('sns/' +self.api_module_name+'/' + template_name, 
                                  params,
                                  context_instance=RequestContext(request,{"path":request.path}))

        
    def get_object(self,request):
        id = long(request.GET.get('id'))
        obj = Message.get_by_id(id, ContentParent.get_or_insert_parent())
        return obj
    
def list(request):
    view=MessageView()
    limited=MessageProcessor().isAddLimited()
    limit_num = limit_const.LIMIT_ARTICLE_ADD_PER_USER 
    extra_params = dict(form=MessageSortByForm(), limited=limited, sortByType='msgLower',limit_num=limit_num,model_name='message')    
    return view.list(request, view, extra_params=extra_params)           

def create(request):
    articleView=MessageView()
    return articleView.create(request, articleView,"create_form.html")

def update(request):
    if request.method=='GET':
        id = long(request.GET.get('id'))
        obj = Message.get_by_id(id, ContentParent.get_or_insert_parent())
        if obj.type ==0:
            len_limit = 140
        elif obj.type ==1:
            len_limit = consts.FACEBOOK_MSG_LENGTH_LIMIT
        else:
            len_limit = 140
        if str_util.strip(obj.url) is None:
            left_length=len_limit-len(obj.msg)
        else:
            left_length = len_limit-len(obj.msg) - context.get_context().short_url_length()
        articleView=MessageView(left_length=left_length)
    elif request.method=='POST':
        articleView=MessageView()
           
    return articleView.update(request, articleView)
    
def delete(request):
    articleView=MessageView()
    response = articleView.delete(request)
    return response

    

