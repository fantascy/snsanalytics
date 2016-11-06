import csv
import StringIO

from google.appengine.ext import db
from google.appengine.api import users
from django.template import RequestContext
from django.http import HttpResponse
from django.shortcuts import render_to_response

from common.utils import string as str_util
from sns.serverutils import deferred
from sns.view.baseview import BaseView
from sns.api import consts as api_const
from sns.cont.feed.forms import FeedCreateForm,FeedUpdateForm,FeedSortByForm, CustomTypeForm, FeedTopicForm, CustomFeedUploadForm
from sns.cont.api import FeedProcessor
from sns.cont.models import Feed
from sns.core.core import ContentParent
from sns import limits as limit_const
from sns.cont.views import ContentControllerView
import json
from django.views.generic.list_detail import object_list
from sns.cont import consts as cont_const
from sns.cont.feedsources import FeedSource, FeedSourceConfig


class FeedControllerView(ContentControllerView):
    pass
        

class FeedView(BaseView,FeedControllerView):
    def __init__(self):
        BaseView.__init__(self,api_const.API_M_FEED,FeedCreateForm,FeedUpdateForm)
        FeedControllerView.__init__(self)

    def custom_form2api(self,form_params):
        r"""
        custom form2api, translate form clean data to a dict acceptable to model api
        """
        form_params = BaseView.custom_form2api(self, form_params)
        (feedurl,name,encoding)=form_params["url"].split("***")
        if form_params.has_key('id'):
            form_params['url'] = feedurl
            form_params['feedurl'] = feedurl
            form_params['encoding'] = encoding
            return form_params
        else:
            return {"url":feedurl,"name":name,"feedurl":feedurl,'encoding':encoding}
        
    def custom_api2form(self,api_params):
        params = BaseView.custom_api2form(self,api_params)
        return params 
       
    def titleList(self):
        return "Feeds" 
    
    def titleCreate(self):
        return "Add Feed"
    
    def titleUpdate(self):
        return "Modify Feed"
    
    def titleDetail(self):
        return "Feed Details"
    
    def update(self, request, view, template_name="form.html", ret_url = None, extra_params={}):
        if request.method=="GET":
            form=self.read_object(request)
        elif request.method=='POST':
            form=self.update_form_class(request.POST)      
            if form.is_valid():
                params=form.cleaned_data.copy()
                self.update_object(form)  
                
                params['page_title']='feed_list_update'
                data=json.dumps(params)
                return HttpResponse(data, mimetype='application/javascript')              
   
        params = {'form': form, 'view' : view, 'title' : self.titleUpdate() }
        params.update(extra_params)
        return render_to_response('sns/' +self.api_module_name+'/' + template_name, 
                                  params,
                                  context_instance=RequestContext(request,{"path":request.path}))
    
    def get_object(self,request):
        return Feed.get_by_id(long(request.GET.get('id')), ContentParent.get_or_insert_parent())


def feed_list(request):
    view=FeedView()
    limited=FeedProcessor().isAddLimited() 
    limit_num = limit_const.LIMIT_FEED_ADD_PER_USER
    extra_params = dict(form=FeedSortByForm(), showTopic = users.is_current_user_admin(),
                        limited=limited, sortByType='nameLower', limit_num=limit_num,model_name='feed')    
    return view.list(request, view, extra_params= extra_params)


def feed_create(request):
    feedView=FeedView()
    return feedView.create(request, feedView, template_name='create_form.html')


def feed_edit(request):
    name = request.POST.get('update_value')
    params = {
        'id': request.POST.get('element_id'),
        'name': name,
        }
    FeedProcessor().update(params)
    return HttpResponse(name)


def feed_update(request):
    feedView=FeedView()
    return feedView.update(request, feedView)


def feed_delete(request):
    feedView=FeedView()
    response = feedView.delete(request)
    return response


def topic(request):
    if request.method=="GET":
        _id = request.GET.get('id')
        feed = db.get(_id)
        initial = {'topics':feed.topics,'id':_id}
        form = FeedTopicForm(initial=initial)
        
    elif request.method=='POST':
        form = FeedTopicForm(request.POST)
        if form.is_valid():
            params = form.cleaned_data.copy()
            feed = db.get(params['id'])
            topics = params['topics']
            feed.topics = topics
            feed.put()
            return HttpResponse('s!')
    return render_to_response('sns/rssfeed/topic.html', 
                                      {'form':form},
                                      context_instance=RequestContext(request,{"path":request.path}))


def feed_custom(request):
    fsid = request.GET.get('fsid', cont_const.FEED_SOURCE_GOOGLE_NEWS)
    keyword = request.GET.get('query', '')
    _map = FeedSourceConfig.get_custom_feed_map(fsid)
    objs = []
    if keyword == '':
        for key in _map.keys():
            objs.append((key,_map[key]))
    else:
        if _map.has_key(keyword):
            objs.append((keyword,_map[keyword]))
    form = CustomTypeForm(initial={'fsid':fsid})
    name = FeedSource.get_name(fsid)
    return object_list( request, 
                            objs,
                            paginate_by=20,
                            extra_context = {'fsid':fsid,'form':form,'name':name,'keyword':keyword,'post_path':'/rssfeed/custom/?paginate_by=20&type='+str(fsid)},
                            template_name="sns/rssfeed/custom.html"
                           ) 
    

def feed_custom_upload(request):
    fsid = request.GET.get('fsid',cont_const.FEED_SOURCE_GOOGLE_NEWS)
    name = FeedSource.get_name(fsid)
    if request.method == 'POST':
        _file = request.FILES['file']
        data = StringIO.StringIO(_file.read())
        deferred.defer(FeedSourceConfig.deferred_set_custom_feed, fsid, data)
        return HttpResponse('succeeded')   
    else:
        form = CustomFeedUploadForm()
    return render_to_response('sns/rssfeed/custom_upload.html', {'form':form, 'view':ContentControllerView(), 'fsid':fsid,'title':name}, context_instance=RequestContext(request,{"path":request.path}))


