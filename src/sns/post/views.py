from django.views.generic.list_detail import object_list
from django.http import HttpResponseRedirect, HttpResponse
from django.shortcuts import render_to_response
from django.template import RequestContext
from sns.view.baseview import BaseView
from sns.camp import consts as camp_const
from common.utils import consts as common_const
from common.utils import string as str_util, url as url_util
from sns import limits as limit_const
from sns.api import consts as api_const
from sns.post.forms import MessageCampaignCreateForm, MessageCampaignUpdateForm,\
    FeedCampaignCreateForm, FeedCampaignUpdateForm, QuickMessageCampaignCreateForm,\
    QuickFeedCampaignCreateForm, MessageCampaignSortByForm, FeedCampaignSortByForm
from sns.api.facade import iapi
from sns.chan.models import TAccount, FAccount
from sns.post.models import SExecution, SPost, FCampaign , MCampaign
from sns.post.api import MessageCampaignProcessor,FeedCampaignProcessor
from google.appengine.ext import db
from sns.view.controllerview import ControllerView
from common.content import pageparser
from common.utils.string import slice_double_byte_character_set
from sns.core.core import get_user, StandardCampaignParent
from sns.core.base import parseValue
from sns.cont.api import MessageProcessor, FeedProcessor, MSG_LENGTH_60,MSG_LENGTH_80,MSG_LENGTH_100
from sns.chan.api import TAccountProcessor, FAccountProcessor, FAdminPageProcessor
from sns.view import consts as view_const
from sns.url.api import is_ads 
import random,datetime
import urllib
import json
import logging
import string

QUICK_POST_RULE_NAME = 'Quick Posts'

class PostingCampaignControllerView(ControllerView):
    def __init__(self):
        ControllerView.__init__(self, "Social Campaigns")
        

class PostingCampaignView(BaseView,PostingCampaignControllerView):
    def __init__(self):
        BaseView.__init__(self, api_const.API_M_POSTING_RULE, None, None)
        PostingCampaignControllerView.__init__(self)
    
    def create(self, request, view, template_name="form.html",ret_url = None,extra_params={},initial_params={}):
        r"""
        temlate
            template path
        """
        if request.method=="GET":
            form=self.initiate_create_form(request,initial_params) # An unbound form
        elif request.method=='POST':
            form=self.create_form_class(request.POST)
            if form.is_valid():
                params=form.cleaned_data.copy()
                if params.has_key('ret_url'):
                    ret_url=params['ret_url']
                form.cleaned_data['randomizeTimeWindow']=getMinuteCount(request.POST.get('randomize_time_count',''))
                
                self.create_object(form)
                return HttpResponse('success','text/html')
                
        ret_url = '/'+self.api_module_name+'/'
        params={'form': form, 'view' : view, 'title' : self.titleCreate(), 'action':'/'+self.api_module_name+'/create/', 'ret_url':ret_url}
        params.update(extra_params)
        return render_to_response('sns/' +self.api_module_name+'/'+template_name, 
                                   params,
                                   context_instance=RequestContext(request,{"path":request.path}))
        
        
    def update(self, request, view, template_name="form.html", ret_url = None, extra_params={},initial_params={}):
        if request.method=="GET":
            form=self.read_object(request,initial_params)
        elif request.method=='POST':
            form=self.update_form_class(request.POST)      
            if form.is_valid():
                params=form.cleaned_data.copy()
                if params.has_key('ret_url'):
                    ret_url=params['ret_url']
                    if params.has_key('current_page'):
                        ret_url=ret_url+"&page="+params['current_page']
                form.cleaned_data['randomizeTimeWindow']=getMinuteCount(request.POST.get('randomize_time_count',''))
                self.update_object(form)                
                return HttpResponse('success','text/html')
            
        ret_url = '/'+self.api_module_name+'/'
        params = {'form': form, 'view' : view, 'title' : self.titleUpdate(), 'action':'/'+self.api_module_name+'/update/', 'ret_url':ret_url}
        params.update(extra_params)
        return render_to_response('sns/' +self.api_module_name+'/' + template_name, 
                                  params,
                                  context_instance=RequestContext(request,{"path":request.path}))


   
    def read_object(self,request,initial_params):
        obj = self.get_object(request)
        params = iapi(self.api_module_name).convertFormat(obj,'python')
        if params :
            params=self.custom_api2form(params)
            params['ret_url']=request.GET.get('ret_url','')
            params['current_page']=request.GET.get('current_page','')
            params.update(initial_params)
            form = self.update_form_class(initial=params)
        return form
    
    def get_object(self,request):
        id = long(request.GET.get('id'))
        batch = int(request.GET.get('batch'))
        obj = iapi(self.api_module_name).getModel().get_by_id(id, StandardCampaignParent.get_or_insert_parent(batch))
        return obj
    
    def initiate_create_form(self,request,initial_params):
        initial_params.update(self.initiate_create_params(request))
        return self.create_form_class(initial=initial_params)

                
    def input_datetime_params(self):
        r"""
        list of param keys that are type of date, time, or datetime. these params need timezone translation.
        """
        return BaseView.input_datetime_params(self) + ['scheduleStart','scheduleEnd','scheduleNext']
    
    def output_datetime_params(self):
        return BaseView.output_datetime_params(self) + ['scheduleStart','scheduleEnd','scheduleNext']
    
    def initiate_create_params(self,request):
        params = BaseView.initiate_create_params(self, request)
        params['scheduleInterval']='1Hr'
        params['gaSource']=camp_const.CAMPAIGN_ANALYTICS_SOURCE_DEFAULT
        params['gaMedium']='Twitter'
        params['gaUseCampaignName']=True
        params['fbPostStyle']=True
        return params
    
    def custom_api2form(self,api_params):
        params = BaseView.custom_api2form(self,api_params)
        if params['gaSource'] is None or params['gaSource']=='':
            params['gaSource']=camp_const.CAMPAIGN_ANALYTICS_SOURCE_DEFAULT
        if params['gaMedium'] is None or params['gaMedium']=='':
            params['gaMedium']='Twitter'
        params['contents'] = map(lambda x: db.get(x).smallModel.id, params['contents'])
        return params
    
    def custom_form2api(self,form_params):
        params = BaseView.custom_form2api(self, form_params)
        params['contents'] = map(lambda x: db.get(x).modelKeyStr(), params['contents'])
        return params
    
    def titleList(self):
        return "Campaigns" 

def getMinuteCount(randomizeTimeWindow):
    if randomizeTimeWindow=='':
        randomizeTimeWindow=0
    elif randomizeTimeWindow.find('Hr')!=-1:
        randomizeTimeWindow=int(randomizeTimeWindow.split('Hr')[0])*60
    elif randomizeTimeWindow.find('Wk')!=-1:
        randomizeTimeWindow=int(randomizeTimeWindow.split('Wk')[0])*60*24*7
    elif randomizeTimeWindow.find('Mo')!=-1:
        randomizeTimeWindow=int(randomizeTimeWindow.split('Mo')[0])*60*24*30
    else:
        randomizeTimeWindow=int(randomizeTimeWindow.split('Min')[0])
    return randomizeTimeWindow

def getTimeCount(randomizeTimeWindow):
    if randomizeTimeWindow==0:
        return '0Min'
    elif randomizeTimeWindow%(60*24*30)==0:
        randomizeTimeWindow = str(randomizeTimeWindow/(60*24*30))+'Mo'
    elif randomizeTimeWindow%(60*24*7)==0:
        randomizeTimeWindow = str(randomizeTimeWindow/(60*24*7))+'Wk'
    elif randomizeTimeWindow%(60)==0:
        randomizeTimeWindow = str(randomizeTimeWindow/(60))+'Hr'
    else:
        randomizeTimeWindow = str(randomizeTimeWindow)+'Min'
    return randomizeTimeWindow
    
class MessageCampaignView(PostingCampaignView):
    def __init__(self):
        BaseView.__init__(self, api_const.API_M_POSTING_RULE_ARTICLE, MessageCampaignCreateForm, MessageCampaignUpdateForm)
        PostingCampaignControllerView.__init__(self)
   
    def custom_form2api(self, form_params):
        api_params = PostingCampaignView.custom_form2api(self, form_params)
        api_params['channels'] = map(lambda x: x.id, api_params['channels'])
        api_params['contents'] = map(lambda x: x, api_params['contents'])
        if 'fbPostStyle' in api_params:
            if api_params['fbPostStyle']:
                api_params['fbPostStyle'] = common_const.FACEBOOK_POST_TYPE_STANDARD
            else:
                api_params['fbPostStyle'] = common_const.FACEBOOK_POST_TYPE_COMPACT
        return api_params
    
    def custom_api2detail(self, api_params):
        detail_params = PostingCampaignView.custom_api2detail(self, api_params)
        detail_params['channels'] = [iapi(api_const.API_M_CHANNEL).call('get', {"id":x}) for x in detail_params["channels"]]
        fc = []
        g_info = []
        p_info = []
        admin = []
        for fchannel in detail_params['fbDestinations']:
            index = fchannel.find(':')
            info = fchannel[index+1:]
            key = fchannel[:index]
            channel = db.get(key)
            if info == 'me':
                fc.append({'name':channel.name,'avatarUrl':channel.avatarUrl,'profileUrl':channel.profileUrl})
            elif info == 'admin':
                admin.append({'name':channel.name,'url':channel.avatarUrl,'profileUrl':channel.url})
            else:
                for g in channel.groups:
                    index = g.find(':')
                    id = g[index+1:]
                    if info == id:
                        name = g[:index]
                        name = name.encode('utf-8','ignore')
                        name = urllib.unquote(name).decode('utf-8','ignore')
                        g_info.append({'name':name,'pre_name':channel.name,'pre_avatarUrl':channel.avatarUrl,'pre_profileUrl':channel.profileUrl,'id':id})
                for g in channel.pages:
                    index = g.find(':')
                    id = g[index+1:]
                    if info == id:
                        name = g[:index]
                        flag = 'snsanalytics'
                        name = name.encode('utf-8','ignore')
                        name = urllib.unquote(name).decode('utf-8','ignore')
                        p_info.append({'name':name,'pre_name':channel.name,'pre_avatarUrl':channel.avatarUrl,'pre_profileUrl':channel.profileUrl,'id':id,'flag':flag})
            
        detail_params['fbDestinations'] = fc
        detail_params['groups'] = g_info
        detail_params['pages'] = p_info
        detail_params['adminpages'] = admin
        detail_params['contents'] = [iapi(api_const.API_M_ARTICLE).call('get', {"id":x}) for x in detail_params["contents"]]
        detail_params['randomize_time_count_value'] = camp_const.INTERVAL_MAP[getTimeCount(detail_params['randomizeTimeWindow'])]
        return detail_params
        
    
    def initiate_create_params(self,request):
        params = PostingCampaignView.initiate_create_params(self, request)
        params['scheduleType'] = camp_const.SCHEDULE_TYPE_NOW
        params['gaOn'] = True
        return params

    def titleList(self):
        return "Message Schedules"
    
    def titleCreate(self):
        return "Add a Message Schedule"
    
    def titleUpdate(self):
        return "Modify Message Schedule"
    
    def titleDetail(self):
        return "Message Schedule Details"


def articlerule_list(request):
    view = MessageCampaignView()
    limited = MessageCampaignProcessor().isAddLimited()
    limit_num = limit_const.LIMIT_ARTICLERULE_ADD_PER_USER
    extra_params = dict(form=MessageCampaignSortByForm(), limited=limited, sortByType='nameLower', limit_num=limit_num,model_name='message campaign')
    return view.list(request, view, extra_params=extra_params)  
    

def articlerule_create(request):
    articlePostingCampaignView = MessageCampaignView()
    return_tag,response=check_contents_create_update_authority(request,MessageProcessor,'message','message','schedule a message')  
    if return_tag:
        return response  
    params={}
    if request.method=="GET":
        params = {'hideTwitter':False,'hideFacebook':False,'fbPostStyle':'on'}
        articles=iapi(api_const.API_M_ARTICLE).query_base().order('msgLower').fetch(limit=10)
        if len(articles)==1:
            params['contents']=[articles[0].smallModel.id]
    extra_params=get_content_page_params()    
    extra_params['schedule_interval_order']='.'.join(camp_const.SCHEDULE_ARTICLE_POSTING_INTERVALS)
    return articlePostingCampaignView.create(request, articlePostingCampaignView,initial_params=params,extra_params=extra_params)


def articlerule_update(request):
    articlePostingCampaignView = MessageCampaignView()
    return_tag,response=check_contents_create_update_authority(request,MessageProcessor,'message','message','update this message schedule')
    if return_tag:
        return response
    extra_params=get_content_page_params()
    extra_params['schedule_interval_order']='.'.join(camp_const.SCHEDULE_ARTICLE_POSTING_INTERVALS)  
    extra_params['campaign_update']=True
    params={}
    if request.method=="GET":
        id = long(request.GET.get('id'))
        batch = int(request.GET.get('batch'))
        rule = MCampaign.get_by_id(id, StandardCampaignParent.get_or_insert_parent(batch))
        if len(rule.channels)==0:
            params['hideTwitter']=False
        else:
            params['hideTwitter']='on'
        if len(rule.fbDestinations)==0:
            params['hideFacebook']=False
        else:
            params['hideFacebook']='on'
        if rule.titleOnly:
            params['titleOnly']='on'
        if rule.fbPostStyle == common_const.FACEBOOK_POST_TYPE_COMPACT:
            params['fbPostStyle']=False
        elif rule.fbPostStyle == common_const.FACEBOOK_POST_TYPE_STANDARD:
            params['fbPostStyle']='on'
        extra_params['randomize_time_count_value'] = getTimeCount(rule.randomizeTimeWindow)    

    return articlePostingCampaignView.update(request, articlePostingCampaignView,initial_params=params,extra_params=extra_params)

def get_content_page_params():
    params={}
    params['twitter_count']= iapi(api_const.API_M_CHANNEL).query_base().count()
    facebook_count= iapi(api_const.API_M_FCHANNEL).query_base().count()
    params['facebook_count']= facebook_count + iapi(api_const.API_M_FBPAGE).query_base().count()
    if params['facebook_count']==1 and facebook_count==1:
        fchannel=FAccountProcessor().query(dict(limit=1))[0]
        params['facebook_count']=params['facebook_count']+len(fchannel.groups)+len(fchannel.pages)    
    params['schedule_interval_json']=json.dumps(camp_const.INTERVAL_MAP)
    return params  

def check_contents_create_update_authority(request,processor,name,type,action):
    return_tag=False
    objects=processor().query(dict(limit=1))
    channels=TAccountProcessor().query(dict(limit=1))
    fchannels=FAccountProcessor().query(dict(limit=1))
    pchannels=FAdminPageProcessor().query(dict(limit=1))
    tag=True
    if len(channels)==0 and len(fchannels)==0 and len(pchannels)==0:
        tag=False
    if len(objects)==0 and not tag:
        return_tag=True
        return return_tag,render_to_response("sns/exception/rule_create_both.html", dict(action=action,ruleType=name,nameOne=name,locationOne=type+'/create',nameTwo='twitter account',locationTwo='chan/twitter/login',nameThree='facebook account',locationThree='chan/facebook/login',nameFour='facebook page',locationFour='chan/fbpage/login',view=ControllerView()), context_instance=RequestContext(request))
    elif not tag:
        return_tag=True
        return return_tag,render_to_response("sns/exception/rule_create.html", dict(action=action,ruleType=name,nameTwo='twitter account',locationTwo='chan/twitter/login',nameThree='facebook account',locationThree='chan/facebook/login',nameFour='facebook page',locationFour='chan/fbpage/login',view=ControllerView()), context_instance=RequestContext(request)) 
    elif len(objects)==0:
        return_tag=True
        return return_tag,render_to_response("sns/exception/rule_create_popup.html", dict(action=action,ruleType=name,name=name,location=type+'/create',view=ControllerView()), context_instance=RequestContext(request))
    return  return_tag,'success'
    

def articlerule_delete(request):
    try:
        articlePostingCampaignView=MessageCampaignView()
        response = articlePostingCampaignView.delete(request)
        return response
    except Exception,ex:
        logging.error('Delete article rule error:%s' % str(ex))
        return HttpResponse("Exception:"+str(ex))

def articlerule_edit(request):
    id = request.POST.get('element_id')
    name = request.POST.get('update_value')
    if len(MessageCampaignProcessor().query(dict(nameLower=str_util.lower_strip(name), limit=1))) > 0:
        return HttpResponse(name+'&nbsp;&nbsp;<span style="color:red">duplicated name</span>')
    params = {
        'id' : id,
        'name' : name,
        }
    MessageCampaignProcessor().update(params)
    return HttpResponse(name)

def articlerule_detail(request, id):
    articlePostingCampaignView = MessageCampaignView()
    return articlePostingCampaignView.detail(request, id, articlePostingCampaignView)

def articlerule_activate(request):
    articlePostingCampaignView = MessageCampaignView()
    return articlePostingCampaignView.activate(request)

def articlerule_deactivate(request):
    articlePostingCampaignView = MessageCampaignView()
    return articlePostingCampaignView.deactivate(request)


class QuickPostingCampaignControllerView(ControllerView):
    def __init__(self, name="Quick Post"):
        self.channelCount = len(iapi(api_const.API_M_CHANNEL).query({}))
        ControllerView.__init__(self, name)

#quickly create article posting rule and publish it
class QuickMessageCampaignView(BaseView,QuickPostingCampaignControllerView):
    def __init__(self):
        BaseView.__init__(self, api_const.API_M_POSTING_RULE_ARTICLE, QuickMessageCampaignCreateForm)
        QuickPostingCampaignControllerView.__init__(self, name="Quick Post")
   
    def create(self, request, view, template_name="form.html",ret_url = None,extra_params={}):
        if view is None :
            view = QuickPostingCampaignControllerView("Post a message") 
        if request.method=="GET":
            form=self.initiate_create_form(request) # An unbound form
        elif request.method=='POST':
            form=self.create_form_class(request.POST)
            if form.is_valid():
                params=form.cleaned_data.copy()
                if params.has_key('ret_url'):
                    ret_url=params['ret_url']
                if params.has_key('fbName'):
                    if len(params['fbName'])>256:
                        params['fbName']=params['fbName'][:256-view_const.TEXT_SUFFIX_LENGTH]+ '...'
                if params.has_key('fbDescription'):
                    if len(params['fbDescription'])>500:
                        params['fbDescription']=params['fbDescription'][:500-view_const.TEXT_SUFFIX_LENGTH]+ '...'
                form.cleaned_data['msgShort60']=slice_double_byte_character_set(form.cleaned_data['msg'],MSG_LENGTH_60)
                form.cleaned_data['msgShort80']=slice_double_byte_character_set(form.cleaned_data['msg'],MSG_LENGTH_80)
                form.cleaned_data['msgShort100']=slice_double_byte_character_set(form.cleaned_data['msg'],MSG_LENGTH_100)                
                tag,response=self.create_object(form)
                if not tag :
                    if not ret_url:
                        ret_url='/'+self.api_module_name+'/'         
                    return render_to_response("sns/exception/quickpost/post_msg_failure.html", dict(ret_url=ret_url,message=form.cleaned_data['msg'],result_twitter=response[0],result_facebook=response[1]), context_instance=RequestContext(request))
                if ret_url is None :
                    return HttpResponseRedirect('/'+self.api_module_name+'/') # Redirect after POST
                else:
                    return HttpResponse('success') # Redirect after POST

        params={'form': form,'action':'/post/rule/article/quickcreate/','view' : view, 'title' : self.titleCreate()}
        params.update(extra_params)
        page_params=get_content_page_params()
        params.update(page_params)
        
        return render_to_response('sns/' +self.api_module_name+'/'+template_name, 
                                   params,
                                   context_instance=RequestContext(request,{"path":request.path}))


    #override parent method, we do post and create at the same time
    def create_object(self,form,channel=None):
        form_params=form.cleaned_data.copy()
        api_params=self.custom_form2api(form_params)
        if api_params.has_key('url'):
            api_params['url'] = url_util.remove_utm(api_params['url'])
        api_params['type']=api_params['type'][0]
        article=iapi(api_const.API_M_ARTICLE).create(api_params)
        if channel is None:
            api_params['channels'] = map(lambda x: x.id, form_params['channels'])
        else:
            channels=[]
            channels.append(channel)
            api_params['channels'] = channels
        api_params['contents']=[article.id,]
        api_params['name'] = QUICK_POST_RULE_NAME
        api_params['skipKeywordMatch']=True
        api_params['fbPostStyle']= common_const.FACEBOOK_POST_TYPE_QUICK
        if (api_params['fbName'] and not api_params['fbName'] == '') or ( api_params['fbDescription'] and not api_params['fbDescription'] == ''):
            api_params['fbLink']=api_params['url']
        description = str_util.strip_one_line(api_params['fbDescription'])
        api_params['fbDescription'] = description
        api_params['gaUseCampaignName'] = False
        api_params['gaCampaign'] = 'Quick Post'
        
        rules = iapi(api_const.API_M_POSTING_RULE_QUICK).query({"nameLower":QUICK_POST_RULE_NAME.lower()})
        if len(rules) == 0:
            rule=iapi(api_const.API_M_POSTING_RULE_QUICK).create(api_params)
        else:
            rule=rules[0]
            rule.channels = parseValue(api_params['channels'],db.ListProperty(db.Key))
            rule.fbDestinations = api_params.get('fbDestinations',[])
            rule.contents = parseValue(api_params['contents'],db.ListProperty(db.Key))
            rule.fbName = api_params.get('fbName',None)
            rule.fbLink = api_params.get('fbLink',None)
            rule.fbDescription = api_params.get('fbDescription',None)
            rule.fbPicture = api_params.get('fbPicture',None)
            
        rule.state=camp_const.CAMPAIGN_STATE_ACTIVATED
        post_success,response=iapi(api_const.API_M_POSTING_RULE_ARTICLE).post(rule,immediate=True)
        article.deleted = True
        article.smallModel.deleted = True
        db.put([rule,article,article.smallModel])
        return post_success,response
    
    def initiate_create_params(self,request):
        params={}
        params['ret_url']=request.GET.get('ret_url','')
        params['left_length']=140
        params['fbPostStyle']=False
        return params
    
    def titleCreate(self):
        return "Post a message"
    
def quickarticlerule_link(request):
    url = request.POST.get('link','')
    url = url.strip()
    url = url_util.remove_utm(url)
    logging.info(url)
    description = ''
    links = []
    info = url_util.fetch_url(url)
    parser = pageparser.SPageParser()
    parser.feed(info,is_quick=True)
    title = parser.get_title()
    if len(parser.pics) > 0:
        links = [] 
        for pic in parser.pics: 
            if not is_ads(pic,parser.domain): 
                links.append(pic)
    if len(parser.ps) > 0:
        description = parser.ps[0]
    elif len(parser.br) > 0:
        description = parser.br[0]
    result = [title, description, links]
    return HttpResponse(json.dumps(result))
    
        
def quickarticlerule_check(request):
    channels = TAccount.all().ancestor(get_user()).filter('deleted', False).order('nameLower')
    twitterAccount = []
    for channel in channels:
        twitterAccount.append((channel.id,channel.name))
        
    fchannels = FAccount.all().ancestor(get_user()).order('nameLower').fetch(limit=100)
    faceboolAccount = []
    for fchannel in fchannels:
        key = fchannel.id + ':' + 'me'
        faceboolAccount.append((key,fchannel.name))
        for g in fchannel.groups:
            index = g.find(':')
            id = g[index+1:]
            name = g[:index]
            key = fchannel.id + ':' +id
            faceboolAccount.append((key,'--- group : '+urllib.unquote(name)))
        for g in fchannel.pages:
            index = g.find(':')
            id = g[index+1:]
            name = g[:index]
            key = fchannel.id + ':' +id
            faceboolAccount.append((key,'--- page : '+urllib.unquote(name)))
    fbpages = iapi(api_const.API_M_FBPAGE).query_base().order('nameLower').fetch(limit=100)
    for page in fbpages:
        key = page.id + ':' + 'admin'
        name = page.name
        faceboolAccount.append((key,name))
        
     
    result = [twitterAccount,faceboolAccount]
    return HttpResponse(json.dumps(result))
             

def quickarticlerule_create(request):
    quickMessageCampaignView = QuickMessageCampaignView()
    channels=TAccountProcessor().query(dict(limit=1))
    fchannels=FAccountProcessor().query(dict(limit=1))
    pchannels=FAdminPageProcessor().query(dict(limit=1))
    if len(channels)==0 and len(fchannels)==0 and len(pchannels)==0:
        return render_to_response("sns/exception/rule_create.html", dict(action='post a message',ruleType='message',nameTwo='twitter account',locationTwo='chan/twitter/login',nameThree='facebook account',locationThree='chan/facebook/login',nameFour='facebook page',locationFour='chan/fbpage/login',view=ControllerView()), context_instance=RequestContext(request)) 
    else :
        return quickMessageCampaignView.create(request, quickMessageCampaignView,template_name="quickcreateform.html")


class FeedCampaignView(PostingCampaignView):
    def __init__(self):
        BaseView.__init__(self, api_const.API_M_POSTING_RULE_FEED, FeedCampaignCreateForm, FeedCampaignUpdateForm)
        PostingCampaignControllerView.__init__(self)
   
    def custom_form2api(self, form_params):
        api_params = PostingCampaignView.custom_form2api(self, form_params)
        api_params['channels'] = map(lambda x: x.id, api_params['channels'])
        api_params['contents'] = map(lambda x: x, api_params['contents'])
        if 'fbPostStyle' in api_params:
            if api_params['fbPostStyle']:
                api_params['fbPostStyle'] = common_const.FACEBOOK_POST_TYPE_STANDARD
            else:
                api_params['fbPostStyle'] = common_const.FACEBOOK_POST_TYPE_COMPACT
        return api_params
    
    def custom_api2detail(self, api_params):
        detail_params = PostingCampaignView.custom_api2detail(self, api_params)
        detail_params['channels'] = [iapi(api_const.API_M_CHANNEL).call('get', {"id":x}) for x in detail_params["channels"]]
        fc = []
        g_info = []
        p_info = []
        admin = []
        for fchannel in detail_params['fbDestinations']:
            index = fchannel.find(':')
            info = fchannel[index+1:]
            key = fchannel[:index]
            channel = db.get(key)
            if info == 'me':
                fc.append({'name':channel.name,'avatarUrl':channel.avatarUrl,'profileUrl':channel.profileUrl})
            elif info == 'admin':
                admin.append({'name':channel.name,'url':channel.avatarUrl,'profileUrl':channel.url})
            else:
                for g in channel.groups:
                    index = g.find(':')
                    id = g[index+1:]
                    if info == id:
                        name = g[:index]
                        name = name.encode('utf-8','ignore')
                        name = urllib.unquote(name).decode('utf-8','ignore')
                        #g_info.append({'name':name,'pre':channel.name+' : group : ','id':id})
                        g_info.append({'name':name,'pre_name':channel.name,'pre_avatarUrl':channel.avatarUrl,'pre_profileUrl':channel.profileUrl,'id':id})
                for g in channel.pages:
                    index = g.find(':')
                    id = g[index+1:]
                    if info == id:
                        name = g[:index]
                        flag = 'snsanalytics'
                        name = name.encode('utf-8','ignore')
                        name = urllib.unquote(name).decode('utf-8','ignore')
                        #p_info.append({'name':name,'pre':channel.name+' : page : ','flag':flag,'id':id})
                        p_info.append({'name':name,'pre_name':channel.name,'pre_avatarUrl':channel.avatarUrl,'pre_profileUrl':channel.profileUrl,'id':id,'flag':flag})
                        
        detail_params['fbDestinations'] = fc
        detail_params['adminpages'] = admin
        detail_params['groups'] = g_info
        detail_params['pages'] = p_info
        detail_params['contents'] = [iapi(api_const.API_M_BASE_FEED).call('get', {"id":x}) for x in detail_params["contents"]]
        detail_params['randomize_time_count_value'] = camp_const.INTERVAL_MAP[getTimeCount(detail_params['randomizeTimeWindow'])]
        return detail_params

    def initiate_create_params(self,request):
        params = PostingCampaignView.initiate_create_params(self, request)
        params['gaOn'] = True
        return params
   
    def titleList(self):
        return "Feed Campaigns" 
    
    def titleCreate(self):
        return "Add Feed Campaign"
    
    def titleUpdate(self):
        return "Modify Feed Campaign"
    
    def titleDetail(self):
        return "Feed Campaign Details"
        
        


def feedrule_list(request):
    view = FeedCampaignView()
    limited = FeedCampaignProcessor().isAddLimited()
    limit_num = limit_const.LIMIT_FEEDRULE_ADD_PER_USER
    extra_params = dict(form=FeedCampaignSortByForm(), limited=limited, sortByType='nameLower',limit_num=limit_num,model_name='feed campaign')
    return view.list(request, view, extra_params= extra_params)

def feedrule_create(request):
    feedPostingCampaignView = FeedCampaignView()
    return_tag,response=check_contents_create_update_authority(request,FeedProcessor,'feed','rssfeed','add a feed campaign')
    if return_tag:
        return response

    params={}
    if request.method=="GET":
        params = {'hideTwitter':False,'hideFacebook':False,'fbPostStyle':common_const.FACEBOOK_POST_TYPE_STANDARD}
        feeds=iapi(api_const.API_M_FEED).query_base().order('nameLower').fetch(limit=10)
        if len(feeds)==1:
            params['contents']=[feeds[0].smallModel.id]
    extra_params=get_content_page_params()    
    extra_params['schedule_interval_order']='.'.join(camp_const.SCHEDULE_FEED_POSTING_INTERVALS)
    return feedPostingCampaignView.create(request, feedPostingCampaignView,initial_params=params,extra_params=extra_params)

def feedrule_update(request):
    feedPostingCampaignView = FeedCampaignView()
    return_tag,response=check_contents_create_update_authority(request,FeedProcessor,'feed','rssfeed','update this feed campaign')
    if return_tag:
        return response
    
    extra_params=get_content_page_params()
    extra_params['schedule_interval_order']='.'.join(camp_const.SCHEDULE_FEED_POSTING_INTERVALS)    
    extra_params['campaign_update']=True
    params={}
    if request.method=="GET":
        id = long(request.GET.get('id'))
        batch = int(request.GET.get('batch'))
        rule = FCampaign.get_by_id(id, StandardCampaignParent.get_or_insert_parent(batch))
        if len(rule.channels)==0:
            params['hideTwitter']=False
        else:
            params['hideTwitter']='on'
        if len(rule.fbDestinations)==0:
            params['hideFacebook']=False
        else:
            params['hideFacebook']='on'
        if rule.titleOnly:
            params['titleOnly']='on'
        if rule.fbPostStyle == common_const.FACEBOOK_POST_TYPE_COMPACT:
            params['fbPostStyle']=False
        elif rule.fbPostStyle == common_const.FACEBOOK_POST_TYPE_STANDARD:
            params['fbPostStyle']='on'
        extra_params['randomize_time_count_value'] = getTimeCount(rule.randomizeTimeWindow) 

    return feedPostingCampaignView.update(request, feedPostingCampaignView,initial_params=params,extra_params=extra_params)

def feedrule_delete(request):
    try:
        feedPostingCampaignView=FeedCampaignView()
        response = feedPostingCampaignView.delete(request)
        return response
    except Exception,ex:
        logging.error('Delete feed rule error:%s' % str(ex))
        return HttpResponse("Exception:"+str(ex))

def feedrule_edit(request):
    id = request.POST.get('element_id')
    name = request.POST.get('update_value')
    if len(FeedCampaignProcessor().query(dict(nameLower=str_util.lower_strip(name), limit=1))) > 0:
        return HttpResponse(name+'&nbsp;&nbsp;<span style="color:red">duplicated name</span>')
    params = {
        'id' : id,
        'name' : name,
        }
    FeedCampaignProcessor().update(params)
    return HttpResponse(name)

def feedrule_detail(request, id):
    feedPostingCampaignView = FeedCampaignView()
    return feedPostingCampaignView.detail(request, id, feedPostingCampaignView)


def feedrule_activate(request):
    feedPostingCampaignView = FeedCampaignView()
    return feedPostingCampaignView.activate(request)

def feedrule_deactivate(request):
    feedPostingCampaignView = FeedCampaignView()
    return feedPostingCampaignView.deactivate(request)


class QuickFeedCampaignView(BaseView,QuickPostingCampaignControllerView):
    def __init__(self):
        BaseView.__init__(self, api_const.API_M_POSTING_RULE_FEED, QuickFeedCampaignCreateForm)
        QuickPostingCampaignControllerView.__init__(self, name="Quick Post")
   
    
    def create(self, request, view, template_name="form.html",ret_url = None,extra_params={}):
        if view is None :
            view = QuickPostingCampaignControllerView("Post a Feed") 
        if request.method=="GET":
            form=self.initiate_create_form(request) # An unbound form
        elif request.method=='POST':
            form=self.create_form_class(request.POST)
            if form.is_valid():
                params=form.cleaned_data.copy()
                if params.has_key('ret_url'):
                    ret_url=params['ret_url']
                if not self.create_object(form) :
                    return render_to_response("sns/post/posting/quickpost_error.html", dict(), context_instance=RequestContext(request))
                if ret_url is None :
                    return HttpResponseRedirect('/'+self.api_module_name+'/') # Redirect after POST
                else:
                    ret_url=string.replace(ret_url,'andmarkreplace','&') 
                    return HttpResponse('success') # Redirect after POST

        params={'form': form,'action':'/post/rule/feed/quickcreate/','view' : view, 'title' : self.titleCreate()}
        params.update(extra_params)
        page_params=get_content_page_params()
        extra_params['schedule_interval_order']='.'.join(camp_const.SCHEDULE_FEED_POSTING_INTERVALS)
        params.update(page_params)
        return render_to_response('sns/' +self.api_module_name+'/'+template_name, 
                                   params,
                                   context_instance=RequestContext(request,{"path":request.path}))

    #override parent method, we do post and create at the same time
    def create_object(self,form):
        form_params=form.cleaned_data.copy()
        (url,name,encoding)=form_params["url"].split("***")
        if iapi(api_const.API_M_FEED).query({"nameLower":str_util.lower_strip(name)}):
            name=name+str(random.random())
        
        api_params={"url":url,"name":name,"feedurl":url,'encoding':encoding}
        #create feed first
        feed=iapi(api_const.API_M_FEED).create(api_params)
        if 'fbPostStyle' in form_params:
            if form_params['fbPostStyle']:
                api_params['fbPostStyle'] = common_const.FACEBOOK_POST_TYPE_STANDARD
            else:
                api_params['fbPostStyle'] = common_const.FACEBOOK_POST_TYPE_COMPACT
        api_params['channels'] = map(lambda x: x.id, form_params['channels'])
        api_params['contents']=[feed.id,]
        api_params['fbDestinations']=form_params['fbDestinations']
        api_params['scheduleInterval']=form_params['scheduleInterval']
        if not iapi(api_const.API_M_POSTING_RULE_FEED).query({"nameLower":feed.nameLower}):
            api_params['name']=feed.name
        else:
            api_params['name']=" ".join((feed.name,str(random.random())))

        api_params['scheduleStart']=datetime.datetime.utcnow()
        api_params['scheduleNext']=datetime.datetime.utcnow()
        api_params['gaOn']=True
        rule=iapi(api_const.API_M_POSTING_RULE_FEED).create(api_params)
        post_success=iapi(api_const.API_M_POSTING_RULE_FEED).post(rule)
        return post_success
    
    def titleCreate(self):
        return "Post a feed"
    
    def initiate_create_params(self,request):
        params = BaseView.initiate_create_params(self, request)
        params['scheduleInterval']='1Hr'
        return params       


def quickfeedrule_create(request):
    quickFeedCampaignView = QuickFeedCampaignView()
    feedLimited=FeedProcessor().isAddLimited()
    feedRuleLimited=FeedCampaignProcessor().isAddLimited()      
    channels=TAccountProcessor().query(dict(limit=1))
    fchannels=FAccountProcessor().query(dict(limit=1))
    pchannels=FAdminPageProcessor().query(dict(limit=1))
    if len(channels)==0 and len(fchannels)==0 and len(pchannels)==0:
        return render_to_response("sns/exception/rule_create.html", dict(action='post a feed',ruleType='message',nameTwo='twitter account',locationTwo='chan/twitter/login',nameThree='facebook account',locationThree='chan/facebook/login',nameFour='facebook page',locationFour='chan/fbpage/login',view=ControllerView()), context_instance=RequestContext(request)) 
    elif feedLimited:
        name='feed'
        number=limit_const.LIMIT_FEED_ADD_PER_USER
        return render_to_response("sns/usr/limit.html", dict(name=name,number=number), context_instance=RequestContext(request));
    elif feedRuleLimited:
        name='feed posting rule'
        number=limit_const.LIMIT_FEEDRULE_ADD_PER_USER
        return render_to_response("sns/usr/limit.html", dict(name=name,number=number), context_instance=RequestContext(request));   
    else:
        return quickFeedCampaignView.create(request, quickFeedCampaignView,template_name="quickcreateform.html")


def posting_list(request, ruleid=None):
    if ruleid:
        rule=db.get(ruleid)
        result=iapi(api_const.API_M_POSTING_POSTING).query_base().order('-executionTime').ancestor(rule)
    else:
        result=iapi(api_const.API_M_POSTING_POSTING).query_base().order('-executionTime')
    return object_list(request, 
                       result,paginate_by=view_const.DEFAULT_INITIAL_PAGE_SIZE, 
                       template_name='sns/' +api_const.API_M_POSTING_POSTING + '/list.html', 
                       extra_context={"ruleid":ruleid, 'view':PostingCampaignView(), 
                                      'post_path':request.path+'?paginate_by='+str(view_const.DEFAULT_INITIAL_PAGE_SIZE),'title':'Campaign Execution Records'})


def post_list(request, postingid=None, filters=None):
    if postingid:
        posting=SExecution.get(db.Key(postingid))
        result = SPost.all().filter('execution',posting).filter('revision', posting.revision)
    else:
        result=iapi(api_const.API_M_POSTING_POST).query_base()
    if filters is not None :
        for filter in filters :
            result.filter(filter[0], filter[1])
    return object_list(request,
                       result,paginate_by=view_const.DEFAULT_INITIAL_PAGE_SIZE, 
                       template_name='sns/' +api_const.API_M_POSTING_POST + '/list.html',
                       extra_context={"postingid":postingid, 'view':PostingCampaignView(), 
                                      'post_path':request.path+'?paginate_by='+str(view_const.DEFAULT_INITIAL_PAGE_SIZE),'title':'Posts'})

def postingrule_check(request): 
    id=request.GET.get('id','')
    rule=db.get(id)
    contents = rule.contents
    channelNum = 0
    for key in rule.channels:
        channel = db.get(key)
        if not channel.deleted:
            channelNum+=1
    for key in rule.fbDestinations:
        index = key.find(':')
        channel = db.get(key[:index])
        if not channel.deleted:
            channelNum+=1
    contentNum = 0
    for key in contents:
        content = db.get(key)
        if not content.deleted:
            contentNum+=1
    if channelNum==0:
        result='channel'
    elif contentNum==0:
        result='content' 
    else:
        result='pass'   
    data = json.dumps(dict(result=result), indent=4)
    return HttpResponse(data, mimetype='application/javascript') 
        
