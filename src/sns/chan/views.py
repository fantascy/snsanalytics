import cgi
import logging
import datetime
import urllib
import urllib2
import csv
import json

from twitter.api import TwitterApi
from twitter.oauth import TwitterOAuthClient

from google.appengine.api import users
from google.appengine.ext import db
from django.http import HttpResponseRedirect
from django.http import HttpResponse
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.views.generic.list_detail import object_list

from deploysns import FACEBOOK_OAUTH_MAP,DOMAIN_MAP
import context
from common.utils import string as str_util, request as req_util, timezone as ctz_util
from common.utils import consts
from common.utils.facebook import GraphAPI
from sns.api import consts as api_const
from sns.view import consts as view_const
from sns.core.core import ChannelParent, get_user
from sns.core.base import txn_put
from sns.api.facade import iapi
from sns.view.controllerview import ControllerView
from sns.view.baseview import BaseView
from sns.mgmt import consts as mgmt_const
from sns.mgmt.api import ContentCampaignProcessor
from sns.chan import consts as channel_const
from sns.cont.topic.api import TopicCacheMgr
from sns.chan.models import TAccount, FAccount, FGroup, FPage, FAdminPage
from sns.chan.api import TAccountProcessor
from sns.chan.forms import ChannelUpdateForm,ChannelCreateForm,ChannelUpdatePasswdForm,ChannelDetailsForm,FChannelUpdateForm,PageChannelUpdateForm,\
                           ChannelReplyDMForm,ChannelReweetForm,ChannelSendDM,ChannelSortByForm,FChannelSortByForm,PageChannelSortByForm,SuspendedTwitterSortByForm,\
                           FchannelPageForm,FanPageForm,MemberGroupForm


class ChannelControllerView(ControllerView):
    def __init__(self):
        ControllerView.__init__(self, "Social Channels")
        

class ChannelView(BaseView,ChannelControllerView):
    def __init__(self):
        BaseView.__init__(self,api_const.API_M_CHANNEL,ChannelCreateForm,ChannelUpdateForm,ChannelUpdatePasswdForm)
        ChannelControllerView.__init__(self)

    def titleList(self):
        return "Twitter Accounts"
    
    def titleCreate(self):
        return "Add Twitter Account"
    
    def titleUpdate(self):
        return "Modify Twitter Account"
    
    def titleDetail(self):
        return "Twitter Account Details"
           
    def get_object(self,request):
        uid = request.GET.get('id')
        obj = TAccount.get_by_key_name(TAccount.keyName(uid), ChannelParent.get_or_insert_parent())
        return obj
         

def list(request):
    view=ChannelView()
    limited=TAccountProcessor().isAddLimited()
    isAdmin = users.is_current_user_admin()
    extra_params = dict(form=ChannelSortByForm(),limited=limited,sortByType='nameLower',isAdmin=isAdmin)
    return view.list(request, view, extra_params= extra_params)


def delete(request):
    channelView=ChannelView()
    response = channelView.delete(request)
    return response


class PageChannelView(BaseView,ChannelControllerView):
    def __init__(self):
        BaseView.__init__(self,api_const.API_M_FBPAGE, ChannelCreateForm,PageChannelUpdateForm)
        ChannelControllerView.__init__(self)
        
    def titleList(self):
        return "Admin Authorized Facebook Pages"
    
    def get_object(self,request):
        uid = request.GET.get('id')
        obj = FAdminPage.get_by_key_name(FAdminPage.keyName(uid), ChannelParent.get_or_insert_parent())
        return obj
    

def fbpage_list(request):
    view=PageChannelView()
    extra_params = dict(form=PageChannelSortByForm(),sortByType='nameLower')
    return view.list(request, view, extra_params= extra_params)


def fbpage_delete(request):
    view=PageChannelView()
    response = view.delete(request)
    return response


class FChannelView(BaseView,ChannelControllerView):
    def __init__(self):
        BaseView.__init__(self,api_const.API_M_FCHANNEL,ChannelCreateForm,FChannelUpdateForm)
        ChannelControllerView.__init__(self)

    def titleList(self):
        return "Facebook Accounts"

    def titleUpdate(self):
        return "Modify Facebook Account"
    
    def get_object(self,request):
        uid = request.GET.get('id')
        obj = FAccount.get_by_key_name(FAccount.keyName(uid), ChannelParent.get_or_insert_parent())
        return obj
        

def facebook_list(request):
    view=FChannelView()
    extra_params = dict(form=FChannelSortByForm(),sortByType='nameLower')
    return view.list(request, view, extra_params= extra_params)


def facebook_delete(request):
    view=FChannelView()
    response = view.delete(request)
    return response
    

def facebook_group_change(request):
    action = request.GET.get('action')
    id = request.GET.get('id')
    name = request.GET.get('name')
    chid = request.GET.get('chid')
    fchannel = FAccount.get_by_key_name(FAccount.keyName(chid), ChannelParent.get_or_insert_parent())
    info = name+':'+id
    if action == 'Include':
        fchannel.groups.append(info)
        for s in fchannel.excludedGroups:
            index = s.find(':')
            i = s[index+1:]
            if i == id:
                fchannel.excludedGroups.remove(s)
        fchannel.put()
        group = FGroup.get_by_key_name(FGroup.keyName(fchannel.chid+':'+id), ChannelParent.get_or_insert_parent())
        group.excluded = False
        group.put()
        result = 'Included'
    elif action == 'Exclude':
        for s in fchannel.groups:
            index = s.find(':')
            i = s[index+1:]
            if i == id:
                fchannel.groups.remove(s)
        fchannel.excludedGroups.append(info)
        fchannel.put()
        group = FGroup.get_by_key_name(FGroup.keyName(fchannel.chid+':'+id), ChannelParent.get_or_insert_parent())
        group.excluded = True
        group.put()
        result = 'Excluded'
    
    data = json.dumps(dict(result=result), indent=4)
    return HttpResponse(data, mimetype='application/javascript')


def facebook_page_change(request):
    action = request.GET.get('action')
    id = request.GET.get('id')
    name = request.GET.get('name')
    chid = request.GET.get('chid')
    fchannel = FAccount.get_by_key_name(FAccount.keyName(chid), ChannelParent.get_or_insert_parent())
    info = name+':'+id
    if action == 'Include':
        fchannel.pages.append(info)
        for s in fchannel.excludedPages:
            index = s.find(':')
            i = s[index+1:]
            if i == id:
                fchannel.excludedPages.remove(s)
        fchannel.put()
        fanpage = FPage.get_by_key_name(FPage.keyName(fchannel.chid+':'+id), ChannelParent.get_or_insert_parent())
        fanpage.excluded = False
        fanpage.put()
        result = 'Included'
    elif action == 'Exclude':
        for s in fchannel.pages:
            index = s.find(':')
            i = s[index+1:]
            if i == id:
                fchannel.pages.remove(s)
        fchannel.excludedPages.append(info)
        fchannel.put()
        fanpage = FPage.get_by_key_name(FPage.keyName(fchannel.chid+':'+id), ChannelParent.get_or_insert_parent())
        fanpage.excluded = True
        fanpage.put()
        result = 'Excluded'
    
    data = json.dumps(dict(result=result), indent=4)
    return HttpResponse(data, mimetype='application/javascript')
    
           
def conversationDetails(request):
    view = ChannelView()    
    channel_list = iapi(api_const.API_M_CHANNEL).query_base().order('nameLower')
    if len(channel_list)==0:
        return render_to_response("sns/chan/error.html",dict(view=view,title='Twitter Conversations'),context_instance=RequestContext(request))       
        
    channel = channel_list[0]
    submenu=''    
    for acc in channel_list:
        logging.debug('submenu acc: %s' % acc)
        login=acc.name
        if login!=channel.login():
            submenu=submenu+'<a class="accountNameList" href="javascript:void(0);" onclick="conversationChangeAcc(\''+acc.id+'\',\''+acc.avatarUrl+'\');return false;"><img src="'+acc.avatarUrl+'" class="iconMedium"/>&nbsp; '+acc.name+'</a>'

    return render_to_response('sns/' +view.api_module_name+'/conversation/list.html', 
                                  {'form': ChannelDetailsForm(), 'view' : view,'title':'Twitter Conversations',
                                   'avatarUrl':channel.avatarUrl,
                                   'id':channel.id,
                                   'login':channel.login(),
                                   'detail_type':request.GET.get('type',3), 
                                   'submenu':submenu,
                                   },                                   
                                   context_instance=RequestContext(request,{"path":request.path}))


def details(request):
    view=ChannelView()
    channel=iapi(api_const.API_M_CHANNEL).get(params={"id":request.GET.get('id')})    
    
    channel_list=iapi(api_const.API_M_CHANNEL).query_base().order('nameLower')
    
    submenu=''    
    for acc in channel_list:
        logging.debug('submenu acc: %s' % acc)
        login=acc.name
        if login!=channel.login():
            submenu=submenu+'<a class="accountNameList" href="" onclick="conversationChangeAcc(\''+acc.id+'\',\''+acc.avatarUrl+'\');return false;"><img src="'+acc.avatarUrl+'" class="iconMedium"/>&nbsp; '+acc.name+'&nbsp&nbsp&nbsp'+'</a>'

    return render_to_response('sns/' +view.api_module_name+'/conversation/list.html', 
                                  {'form': ChannelDetailsForm(), 'view' : view,
                                   'avatarUrl':request.GET.get('avatarUrl', "None"),'title':'Twitter Conversations',
                                   'id':request.GET.get('id'),
                                   'login':channel.login(),
                                   'detail_type':request.GET.get('type',3), 
                                   'submenu':submenu,
                                   },                                   
                                   context_instance=RequestContext(request,{"path":request.path}))


def conversation_type_details(request, type, templateName, errorMsg, page_count=view_const.CONV_MGMT_PAGE_SIZE):
    try:
        view = ChannelView()
        max_id = request.GET.get("max_id","")
        channel = iapi(api_const.API_M_CHANNEL).get(params={"id":request.GET.get('id')})
        tapi = channel.get_twitter_api()
        objects = []
        if type=="dm inbox":
            if max_id:
                objects=tapi.direct_messages(max_id=max_id, count=page_count+1)
            else:
                objects=tapi.direct_messages(count=page_count+1)
        elif type=="dm outbox":
            if max_id:
                objects=tapi.direct_messages.sent(max_id=max_id, count=page_count+1)
            else:
                objects=tapi.direct_messages.sent(count=page_count+1)
        elif type=="home tweets":
            if max_id:
                objects=tapi.statuses.home_timeline(max_id=max_id, count=page_count+1)
            else:
                objects=tapi.statuses.home_timeline(count=page_count+1)
        elif type=="mentions":
            if max_id:
                objects=tapi.statuses.mentions_timeline(max_id=max_id, count=page_count+10)
            else:
                objects=tapi.statuses.mentions_timeline(count=page_count+10)
        elif type=="sent tweets":
            if max_id:
                objects=tapi.statuses.user_timeline(max_id=max_id, count=page_count+1)
            else:
                objects=tapi.statuses.user_timeline(count=page_count+1)
        elif type=="favorites":
            if max_id:
                objects=tapi.favorites.list(max_id=max_id, count=page_count+1)
            else:
                objects=tapi.favorites.list(count=page_count+1)
        elif type=="retweets by others":
            if max_id:
                objects=tapi.statuses.retweeted_to_me(max_id=max_id, count=page_count+1)
            else:
                objects=tapi.statuses.retweeted_to_me(count=page_count+1)
        elif type=="retweets by you":
            if max_id:
                objects=tapi.statuses.retweeted_by_me(max_id=max_id, count=page_count+1)
            else:
                objects=tapi.statuses.retweeted_by_me(count=page_count+1)
        elif type=="your tweets,retweeted":
            if max_id:
                objects=tapi.statuses.retweets_of_me(max_id=max_id, count=page_count+1)
            else:
                objects=tapi.statuses.retweets_of_me(count=page_count+1)
        params=dict(type=request.GET.get('type'),
                    uid=request.GET.get('id'),
                    avatarUrl=request.GET.get('avatarUrl'),
                   )
        if len(objects) > page_count:
            params['max_id'] = objects[page_count]['id']
            for i in range(0, len(objects) - page_count):
                objects.remove(objects[page_count])
        params['object_list'] = objects
        number = request.GET.get("div_number", None)
        params['div_number'] = str(int(number) + 1 if number else 0)
        if number:
            templateName = templateName + "_more"
        return render_to_response("sns/%s/conversation/%s.html" % (view.api_module_name, templateName), params, context_instance=RequestContext(request,{"path": request.path}))
    except Exception:
        logging.exception("Error when doing Twitter conversation!")
        return render_to_response("sns/chan/error_twitter_request.html", context_instance=RequestContext(request))


def details_dm_inbox(request):
    return conversation_type_details(request,"dm inbox","dm_inbox","twitter dm inbox request failed")

def details_dm_outbox(request):
    return conversation_type_details(request,"dm outbox","dm_outbox","twitter dm outbox request failed")

def details_home_tweets(request):
    return conversation_type_details(request,"home tweets","home_tweets","twitter home tweets request failed")

def details_mentions(request):
    return conversation_type_details(request,"mentions","mentions","twitter mentions request failed")
    
def details_sent_tweets(request):
    return conversation_type_details(request,"sent tweets","sent_tweets","twitter sent tweets request failed")    
    
def details_favorites(request):
    return conversation_type_details(request,"favorites","favorites","twitter favorites request failed")

def retweets_by_others(request):
    return conversation_type_details(request,"retweets by others","retweets_by_others","twitter retweets by others request failed")

def retweets_by_you(request):
    return conversation_type_details(request,"retweets by you","retweets_by_you","twitter retweets by you request failed")    
    

def your_tweets_retweeted(request):
    return conversation_type_details(request,"your tweets,retweeted","your_tweets_retweeted","twitter 'your tweets,retweeted request' failed")    
       

def details_my_followers(request):
    try:
        request_expire = datetime.datetime.utcnow() + datetime.timedelta(seconds=25)
        channel = iapi(api_const.API_M_CHANNEL).get(params={"id":request.GET.get('id')})
        tapi = channel.get_twitter_api()
        follower_ids = tapi.followers.ids(user_id=channel.chid_int(), cursor=-1)['ids']
        followers = tapi.users.lookup(user_id=follower_ids[:40])
        params = dict(type=request.GET.get('type'),
                    uid=request.GET.get('id'),
                    avatarUrl=request.GET.get('avatarUrl'),)  
        is_timeout = datetime.datetime.utcnow() + datetime.timedelta(seconds=0) > request_expire
        if is_timeout:
            return render_to_response("sns/chan/error_timeout.html", dict(user_a=channel.login()), context_instance=RequestContext(request))
        return object_list(request, 
                           followers,
                           extra_context=params,
                           paginate_by=view_const.DEFAULT_INITIAL_PAGE_SIZE, 
                           template_name='sns/chan/conversation/my_followers.html' 
                           )
    except Exception:
        logging.exception("Error when showing followers details!")
        return render_to_response("sns/chan/error_twitter_request.html", context_instance=RequestContext(request))
    

def details_my_friends(request):
    try:
        request_expire = datetime.datetime.utcnow() + datetime.timedelta(seconds=25)
        channel = iapi(api_const.API_M_CHANNEL).get(params={"id":request.GET.get('id')})
        tapi = channel.get_twitter_api()
        friend_ids = tapi.friends.ids(user_id=channel.chid_int(), cursor=-1)['ids']
        friends = tapi.users.lookup(user_id=friend_ids[:40])
        params=dict(type=request.GET.get('type'),
                    uid=request.GET.get('id'),
                    avatarUrl=request.GET.get('avatarUrl'),)
        is_timeout = datetime.datetime.utcnow() + datetime.timedelta(seconds=0) > request_expire
        if is_timeout:
            return render_to_response("sns/chan/error_timeout.html", dict(user_a=channel.login()), context_instance=RequestContext(request))
        return object_list(request, 
                           friends,
                           extra_context = params,
                           paginate_by=view_const.DEFAULT_INITIAL_PAGE_SIZE, 
                           template_name='sns/chan/conversation/my_friends.html' 
                           )
    except Exception:
        logging.exception("Error when showing friends details!")
        return render_to_response("sns/chan/error_twitter_request.html", dict(type=request.GET.get('type')), context_instance=RequestContext(request))


def deleteDM(request):
    channel = iapi(api_const.API_M_CHANNEL).get(params={"id": request.GET.get('uid')})
    tapi = channel.get_twitter_api()
    tapi.direct_messages.destroy(id=request.GET.get('id'))
    return HttpResponse("Success")

def deleteTweets(request):
    channel = iapi(api_const.API_M_CHANNEL).get(params={"id": request.GET.get('uid')})
    tapi = channel.get_twitter_api()
    tapi.statuses.destroy(id=request.GET.get('id'))
    return HttpResponse("Success")

def deleteFavorite(request):
    channel = iapi(api_const.API_M_CHANNEL).get(params={"id": request.GET.get('uid')})
    tapi = channel.get_twitter_api()
    tapi.favorites.destroy(id=request.GET.get('id'))
    return HttpResponse("Success")


def favorite_create(request):
    channel = iapi(api_const.API_M_CHANNEL).get(params={"id": request.GET.get('uid')})
    tapi = channel.get_twitter_api()
    tapi.favorites.create(id=request.GET.get('id'))
    return HttpResponse("Success")


def unFollowMyFriends(request):
    channel=iapi(api_const.API_M_CHANNEL).get(params={"id": request.GET.get('uid')})
    tapi = channel.get_twitter_api()
    tapi.friendships.destroy(user_id=int(request.GET.get('id')))
    return HttpResponse("Success")
    

def FollowFriends(request):
    channel=iapi(api_const.API_M_CHANNEL).get(params={"id":request.GET.get('uid')})
    target_screen_name = request.GET.get('id')
    tapi = channel.get_twitter_api()
    params={}
    if tapi.is_following_or_requested(screen_name=target_screen_name):
        user = tapi.friendships.create(screen_name=target_screen_name)
        logging.debug("%s followed %s: %s" % (channel.login(), target_screen_name, user))
    else:
        params = {'ret_url': '',
                  'user_a': channel.login(),
                  'user_b': target_screen_name,
                  }
        data=json.dumps(params)
        return HttpResponse(data, mimetype='application/javascript') 
    params['ret_url'] = '/chan/details/followers?id='+request.GET.get('uid', "")+'&avatarUrl='+request.GET.get('avatarUrl')+'&type='+request.GET.get('type')
    data = json.dumps(params)
    return HttpResponse(data, mimetype='application/javascript') 
    

def replyTweets(request):
    if request.method=="GET":
        uid=request.GET.get('uid', "None")
        replyto=request.GET.get('replyto', None)
        replyinit=""
        left_length=consts.TWITTER_MSG_LENGTH_LIMIT
        if replyto is not None:
            replyinit="@"+replyto+" "
            left_length=left_length-len(replyinit) 
        params={'left_length':left_length,
                'avatarUrl':request.GET.get('avatarUrl'),
                'type':request.GET.get('type'),
                'uid':uid,
                'msg':replyinit,
                'channels':[iapi(api_const.API_M_CHANNEL).get(params={"id":uid}).id],}
        logging.info("reply params:%s" % params)
        logging.info("reply params.channels:%s" % params['channels'])
        form=ChannelReplyDMForm(initial=params)
    elif request.method=='POST':
        form=ChannelReplyDMForm(request.POST)
        if form.is_valid():
            from sns.post.views import QuickMessageCampaignView
            ret_url='/chan/details/?id='+request.POST.get('uid', "")+'&avatarUrl='+request.POST.get('avatarUrl')+'&type='+request.POST.get('type')
            uid=request.POST.get('uid', "None")
            quickMessageCampaignView = QuickMessageCampaignView()
            quickMessageCampaignView.create_object(form=form)
            return HttpResponse("channel_home_tweet "+ret_url, mimetype='application/javascript')  # Redirect after POST
    
    return render_to_response('sns/chan/conversation/tweets_reply_form.html', 
                               {'form': form, 
                                'title' : 'Tweets Reply',
                                'home_tweet' : request.GET.get('home_tweet','')
                                },
                               context_instance=RequestContext(request,{"path":request.path}))
    
def Retweets(request):
    if request.method=="GET":
        origin_tweet_id = request.GET.get('origin_tweet_id', None)
        if not origin_tweet_id:
            origin_tweet_id = request.GET.get('id', None)
        uid=request.GET.get('uid', "None")
        replyto=request.GET.get('replyto', None)       
        text=request.GET.get('text', '')   
        tweet_origin_channel=request.GET.get('tweet_origin_channel', '')
        
        '''get what to display to user to review his reweet.'''
        replyinit=""
        if tweet_origin_channel!='':
            replyinit="RT @"+tweet_origin_channel+" "+text
        else:
            if replyto is not None:
                replyinit="RT @"+replyto+" "+text 
            
        '''channel is the list of channels not displayed in the retweet NameMultipleChoiceField'''    
        channel=[]
        if tweet_origin_channel!='':
            channel.append(tweet_origin_channel)
        channel.append(replyto)
        channel_twitter=iapi(api_const.API_M_CHANNEL).get(params={"id":uid})
        twitter=TwitterApi(oauth_access_token=channel_twitter.oauthAccessToken)
        response=twitter.statuses.retweets(id=origin_tweet_id) 
        for retweet in response:
            channel.append(retweet['user']['screen_name']) 
            
        params={'avatarUrl':request.GET.get('avatarUrl'),
                'type':request.GET.get('type'),
                'uid':uid,
                'msg':replyinit,
                'id':request.GET.get('id'),
                'channels':[iapi(api_const.API_M_CHANNEL).get(params={"id":uid}).id],
                'channel':channel,}

        form=ChannelReweetForm(initial=params)        
        
    elif request.method=='POST':
        channel=request.POST.get('channel', "")
        params={'channel_string':channel,}
        form=ChannelReweetForm(request.POST,initial=params)
        if form.is_valid():
            params=form.cleaned_data.copy()
            ret_url='/chan/details/?id='+request.POST.get('uid', "")+'&avatarUrl='+request.POST.get('avatarUrl')+'&type='+request.POST.get('type')
            uid=request.POST.get('uid', "None")
            channels=params['channels']
            for channel_choice in channels: 
                channel=iapi(api_const.API_M_CHANNEL).get(params={"id":channel_choice})
                tapi = channel.get_twitter_api()
                tapi.statuses.retweet(id=params['id'])           
            return HttpResponse("channel_retweet "+ret_url, mimetype='application/javascript')
        
    return render_to_response('sns/chan/conversation/retweet_form.html', 
                               {'form': form, 
                                'title' : 'Retweets'
                                },
                               context_instance=RequestContext(request,{"path":request.path}))

def sendDM(request):
    if request.method=="GET":
        uid=request.GET.get('uid', "None")
        params={'left_length':consts.TWITTER_MSG_LENGTH_LIMIT,
                'avatarUrl':request.GET.get('avatarUrl'),
                'type':request.GET.get('type'),
                'uid':uid,}
        sendto=request.GET.get('sendto', None)
        msg='d @'+sendto+' '
        params['msg']=msg
        left_length=consts.TWITTER_MSG_LENGTH_LIMIT-len(msg) 
        params['left_length']=left_length
        form=ChannelSendDM(initial=params)
    elif request.method=='POST':
        form=ChannelSendDM(request.POST)
        if form.is_valid():         
            from sns.post.views import QuickMessageCampaignView   
            uid=request.POST.get('uid', "None")
            quickMessageCampaignView = QuickMessageCampaignView()
            quickMessageCampaignView.create_object(form=form,channel=uid)
            ret_url='/chan/details/?id='+request.POST.get('uid', "")+'&avatarUrl='+request.POST.get('avatarUrl')+'&type='+request.POST.get('type')
            return HttpResponse("channel_send_dm "+ret_url, mimetype='application/javascript')
    return render_to_response('sns/chan/conversation/dm_send_form.html', 
                               {'form': form, 
                                'title' : 'DM Inbox reply'},
                               context_instance=RequestContext(request,{"path":request.path}))


def twitter_login(request):
    client = TwitterOAuthClient()
    url=client.get_request_token()
    return HttpResponseRedirect(url)


def twitter_sync(request):
    channel, succeeded = iapi(api_const.API_M_CHANNEL).sync({"id":request.GET.get('id')})
    if succeeded:
        params = {}
        params['screen_name'] = channel.name
        params['page_title'] = 'channel_list_sync'
        if channel.avatarUrl:    
            params['avatarUrl'] = channel.avatarUrl    
        else:    
            params['avatarUrl'] = channel_const.DEFAULT_TWITTER_AVATAR_URL    
        return HttpResponse(json.dumps(params), mimetype='application/javascript')
    else:
        return HttpResponse("Sync failed!")
    

def twitter_callback(request):
    client = TwitterOAuthClient()
    oauth_token = request.GET.get("oauth_token", '')
    if not oauth_token:
        return HttpResponseRedirect("/#/chan/")
    oauth_verifier = request.GET.get("oauth_verifier")
    access_token = client.callback(oauth_token, oauth_verifier)
    twitterInfo = TwitterApi(oauth_access_token=access_token).account.verify_credentials()
    chid = str(twitterInfo["id"])
    channel = TAccount.get_by_key_name(TAccount.keyName(chid), ChannelParent.get_or_insert_parent())
    if channel is None or channel.deleted:
        avatarUrl=twitterInfo["profile_image_url"]
        channel=iapi(api_const.API_M_CHANNEL).create({"chid":chid,"type":channel_const.CHANNEL_TYPE_TWITTER,"oauthAccessToken":access_token,
                                "login":access_token.handle,"avatarUrl":avatarUrl,"parent":ChannelParent.get_or_insert_parent()})
    return HttpResponseRedirect("/chan/twitter/confirm?id=%s&login=%s&avatarUrl=%s" % (channel.id, access_token.handle, channel.avatarUrl))
    

def twitter_confirm(request):
    if context.get_context().cmp_on() and get_user().isContent:
        tags = str_util.split_strip(get_user().tags,',')
        cmp_rules = ContentCampaignProcessor().query_base().order('-priority').fetch(limit=100)
        match = False
        contentRule = None
        for contentRule in cmp_rules:
            if contentRule.filterType == mgmt_const.CMP_RULE_FILTER_TYPE_INCLUDED_USER:
                itags = str_util.split_strip(contentRule.includedTags,',')
                for t in tags:
                    if t!= '' and t.lower() in itags:
                        match = True
                        break
                if match:
                    break
        if contentRule is not None and match:
            topicNumber = contentRule.getTopicNumber()
        else:
            topicNumber = 1
        return render_to_response('sns/chan/content_callback.html' , 
                              {'view':ChannelView(), 'id':request.GET.get('id'), 'login':request.GET.get('login'), 'avatarUrl':request.GET.get('avatarUrl'),
                               'topicNames':TopicCacheMgr.get_all_topic_names(), 'topicNumber':topicNumber},
                              context_instance=RequestContext(request, {"path": request.path}))    
        
    else:
        return HttpResponseRedirect("/chan/")
#        channelView=ChannelView()
#        if not request.REQUEST.has_key('tweet'):        
#            left_length=consts.TWITTER_MSG_LENGTH_LIMIT-len(channel_const.TWITTER_CALLBACK_TWEET)
#            return render_to_response('sns/chan/callbackform.html' , 
#                                      {'view':channelView, 'id':request.GET.get('id'), 'login':request.GET.get('login'), 'avatarUrl':request.GET.get('avatarUrl'), 'left_length':left_length, 'tweet_msg':channel_const.TWITTER_CALLBACK_TWEET},
#                                      context_instance=RequestContext(request,{"path":request.path}))    
#        else :
#            try:
#                tweet=request.POST.get('tweet')
#                like=request.POST.get('like_checkbox')
#                key_str = request.POST.get('id')
#                channel=db.get(key_str)
#                tapi = tapi
#                if like=='on' and not tapi.is_following_or_requested(screen_name='snsanalytics'):
#                    tapi.friendships.create(screen_name='snsanalytics')
#                if tweet!='':
#                    status = tapi.statuses.update(status=str_util.slice(tweet, "0:140"))
#                    logging.debug("Twitter update status: %s" % status)
#            except Exception:
#                logging.exception("Failded to like our page or post for twitter account: %s." % key_str)
#            return HttpResponseRedirect("/chan/")
        

def facebook_login(request):
    params = {}
    params['client_id'] = FACEBOOK_OAUTH_MAP[context.get_context().application_id()]['id']
    params['redirect_uri'] = 'http://'+DOMAIN_MAP[context.get_context().application_id()]+'/callback/facebook/'
    params['display']='page'
    params['scope']='publish_stream,publish_checkins,sms,offline_access,create_event,rsvp_event,manage_pages,user_birthday,user_location,user_hometown,user_events,user_groups,user_likes,user_interests,email,read_stream,friends_birthday,friends_location,friends_hometown,friends_likes,friends_groups,friends_interests,friends_checkins'
    url = 'https://graph.facebook.com/oauth/authorize?' + urllib.urlencode(params)
    return HttpResponseRedirect(url) 

def facebook_callback(request):
    params={}
    params['code'] = request.GET.get('code')
    params['redirect_uri'] = 'http://'+DOMAIN_MAP[context.get_context().application_id()]+'/callback/facebook/'
    params['client_id'] = FACEBOOK_OAUTH_MAP[context.get_context().application_id()]['id']
    params['client_secret'] = FACEBOOK_OAUTH_MAP[context.get_context().application_id()]['secret']
    url = 'https://graph.facebook.com/oauth/access_token?' + urllib.urlencode(params)
    response = cgi.parse_qs(urllib2.urlopen(url).read())
    access_token = response["access_token"][-1]
    profile = json.load(urllib2.urlopen(
                "https://graph.facebook.com/me?" +
                urllib.urlencode(dict(access_token=access_token,fields='id,name,picture,link'))))
    fchannel = FAccount.get_by_key_name(FAccount.keyName(profile['id']), ChannelParent.get_or_insert_parent())
    if fchannel is None or fchannel.deleted:
        c_params = {'name':profile['name'],'chid':profile['id'],'type':channel_const.CHANNEL_TYPE_FACEBOOK_ACCOUNT,'parent':ChannelParent.get_or_insert_parent(),
                'oauthAccessToken':access_token,'profileUrl':profile["link"],'avatarUrl':profile["picture"]}
        fchannel = iapi(api_const.API_M_FCHANNEL).create(c_params)
    fchannel.managePages = True
    fchannel.put()
    return HttpResponseRedirect("/#/chan/facebook/" )
    
def fb_account_confirm(request):
    channelView=ChannelView()
    if not request.REQUEST.has_key('tweet'):        
        left_length = consts.FACEBOOK_MSG_LENGTH_LIMIT - len(channel_const.FACEBOOK_CALLBACK_TWEET)
        return render_to_response('sns/chan/facebook/post_callbackform.html' , 
                                  {'view':channelView, 'id':request.GET.get('id'), 'login':request.GET.get('login'), 'profileUrl':request.GET.get('profileUrl'), 'avatarUrl':request.GET.get('avatarUrl'), 'left_length':left_length, 'tweet_msg':channel_const.FACEBOOK_CALLBACK_TWEET},
                                  context_instance=RequestContext(request,{"path":request.path}))    
    else :
        try:
            tweet=request.POST.get('tweet')
            fchannel=db.get(request.POST.get('id'))

            if tweet!='':
                graph = GraphAPI(fchannel.oauthAccessToken)
                graph.put_object('me', 'feed',message=tweet)
        except Exception,ex:
            logging.error(str(ex))
            logging.error("Failded to post for facebook account:%s." % request.POST.get('id'))
        return HttpResponseRedirect("/chan/facebook/")
    
def facebook_sync(request):
    fchannel = db.get(request.GET.get('id'))
    access_token = fchannel.oauthAccessToken
    profile = json.load(urllib2.urlopen(
                "https://graph.facebook.com/me?" +
                urllib.urlencode(dict(access_token=access_token,fields='id,name,picture,link'))))
    fchannel.name = profile['name']
    fchannel.avatarUrl = profile["picture"]
    fchannel.profileUrl = profile["link"]
    fchannel.put()
    params={}
    params['name']=profile['name']
    params['avatarUrl']=profile['picture']
    params['link']=profile["link"]
    data = json.dumps(params, indent=4)
    return HttpResponse(data, mimetype='application/javascript')  
        
def fbpage_sync(request):
    page = db.get(request.GET.get('id'))
    params = {}
    fchannel = FAccount.get_by_key_name(FAccount.keyName(page.chid), page.parent())
    params['access_token'] = fchannel.oauthAccessToken
    query = 'SELECT page_id,name, pic_square,page_url  FROM page WHERE page_id = %s'%str(page.pageid)
    params['query'] =query
    params['format'] = 'json'
    url = 'https://api.facebook.com/method/fql.query?' +urllib.urlencode(params)
    data = urllib2.urlopen(url)
    content = data.read()
    info = json.loads(content)[0]
    page.name = info['name']
    page.avatarUrl = info['pic_square']
    page.url = info['page_url']
    db.put(page)
    params={}
    params['name']=page.name
    params['avatarUrl']=page.avatarUrl
    params['link']=page.url
    data = json.dumps(params, indent=4)
    return HttpResponse(data, mimetype='application/javascript')

def groupmember_sync(request):
    group = db.get(request.GET.get('id'))
    fchannel = FAccount.get_by_key_name(FAccount.keyName(group.chid), group.parent())
    qparams = {}
    qparams['access_token'] = fchannel.oauthAccessToken
    query = 'SELECT gid,pic,name FROM group WHERE gid = %s'%str(group.groupid)
    qparams['query'] =query
    qparams['format'] = 'json'
    url = 'https://api.facebook.com/method/fql.query?' +urllib.urlencode(qparams)
    data = urllib2.urlopen(url)
    content = data.read()
    info = json.loads(content)[0]
    group.name = info['name']
    group.avatarUrl = info['pic']
    db.put(group)
    params={}
    params['name']=group.name
    params['avatarUrl']=group.avatarUrl
    params['link']=group.url
    data = json.dumps(params, indent=4)
    return HttpResponse(data, mimetype='application/javascript')

def fbpage_login(request):
    fchannels = iapi(api_const.API_M_FCHANNEL).query_base().fetch(limit=1000)
    manage_channels = []
    no_manage_channels = []
    no_manage = False
    no_manage_info = ''
    for c in fchannels:
        if c.managePages:
            manage_channels.append(c)
        else:
            no_manage_channels.append(c)
    title = 'Add Facebook Pages'
    if len(fchannels) == 0:
        return render_to_response('sns/chan/fbpage/account.html', {'title':title},
                                  context_instance=RequestContext(request,{"path":request.path}))
    elif len(manage_channels) == 0:
        return render_to_response('sns/chan/fbpage/manage.html', {'title':title},
                                  context_instance=RequestContext(request,{"path":request.path}))
    else:
        form = FchannelPageForm(manage_channels)
        url = 'chan/fbpage/add'
        if len(no_manage_channels) > 0:
            no_manage = True
            no_manage_info = no_manage_channels
        return render_to_response('sns/chan/fbpage/account_list.html',{'form':form,'url':url,'accounts':manage_channels,'type':'fan page','title':title,
                                                    'imgSrc':manage_channels[0].avatarUrl,'no_manage_info':no_manage_info,'no_manage':no_manage},context_instance=RequestContext(request,{"path":request.path}))

def fbpage_add(request):        
    channelView=ChannelView()
    if not request.REQUEST.has_key('tweet'): 
        id = request.GET.get('id')
        fchannel = db.get(id)
        graph = GraphAPI(access_token=fchannel.oauthAccessToken)
        pages = graph.get_connections('me', 'accounts')
        pdata=[]
        pids = []
        adata=[]
        aids = []
        for page in pages['data']:
            if page['category'] == 'Application':
                adata.append(page)
                aids.append(page['id'])
            else:
                pdata.append(page)
                pids.append(page['id'])
                
        page_list = []
        if len(pids) > 0:
            params = {}
            params['access_token'] = fchannel.oauthAccessToken
            idstr = '(' + ','.join(pids)+')'
            query = 'SELECT page_id,name, pic_square,page_url  FROM page WHERE page_id in %s'%idstr
            params['query'] =query
            params['format'] = 'json'
            url = 'https://api.facebook.com/method/fql.query?' +urllib.urlencode(params)
            data = urllib2.urlopen(url)
            content = data.read()
            pinfos = json.loads(content)
            for i in range(0,len(pdata)):
                data = pdata[i]
                info = pinfos[i]
                if data['id'] != str(info['page_id']):
                    logging.error('Sth is wrong with fql')
                else:
                    params = {}
                    params['pageid'] = data['id']
                    params['chid'] = fchannel.chid
                    params['name'] = data['name']
                    params['oauthAccessToken'] = data['access_token']
                    params['avatarUrl']= info['pic_square']
                    params['url']= info['page_url']
                    params['type'] = channel_const.CHANNEL_TYPE_FACEBOOK_PAGE
                    params['category'] = data['category']
                    params['parent']=ChannelParent.get_or_insert_parent()
                    page_list.append(params)
        if len(aids) > 0:
            params = {}
            params['access_token'] = fchannel.oauthAccessToken
            idstr = '(' + ','.join(aids)+')'
            query = 'SELECT app_id ,display_name, icon_url FROM application WHERE app_id in %s'%idstr
            params['query'] =query
            params['format'] = 'json'
            url = 'https://api.facebook.com/method/fql.query?' +urllib.urlencode(params)
            data = urllib2.urlopen(url)
            content = data.read()
            ainfos = json.loads(content)
            for i in range(0,len(adata)):
                data = adata[i]
                info = ainfos[i]
                if data['id'] != str(info['app_id']):
                    logging.error('Sth is wrong with fql')
                else:
                    params = {}
                    params['pageid'] = data['id']
                    params['chid'] = fchannel.chid
                    params['name'] = info['display_name']
                    params['oauthAccessToken'] = data['access_token']
                    params['avatarUrl']= info['icon_url']
                    params['url']= 'http://www.facebook.com/apps/application.php?id='+data['id']
                    params['type'] = channel_const.CHANNEL_TYPE_FACEBOOK_PAGE
                    params['category'] = data['category']
                    params['parent']=ChannelParent.get_or_insert_parent()
                    page_list.append(params)
        display_pages=[]
        number=0
        max_pages_limit=0
        other_ids=''
        page_list=sorted(page_list,key=lambda d:d['name'])
        for page in page_list:
            pchannel = FAdminPage.get_by_key_name(FAdminPage.keyName(page['pageid']),  ChannelParent.get_or_insert_parent())
            if pchannel is None or pchannel.deleted:
                pchannel = iapi(api_const.API_M_FBPAGE).create(page)
                if number==20:
                    max_pages_limit+=1    
                    other_ids=(other_ids+'SubstitutePChannel'+pchannel.id if other_ids!='' else pchannel.id)                
                else:
                    if (number+1)%2==0:
                        even=1
                    else:
                        even=0
                    display_pages.append((pchannel,number,even))                    
                    number+=1
        length_display_pages=len(display_pages)
        if length_display_pages==0:
            return render_to_response('sns/chan/fbpage/post_callback_blank.html', 
                                  dict(view=channelView,account=fchannel.name,profileUrl=fchannel.profileUrl),
                                   context_instance=RequestContext(request,{"path":request.path}))
        left_length = consts.FACEBOOK_MSG_LENGTH_LIMIT - len(channel_const.FACEBOOK_CALLBACK_TWEET)
        return render_to_response('sns/chan/fbpage/post_callback_form.html', 
                                  dict(view=channelView,other_ids=other_ids,page_list=display_pages,account=fchannel.name,profileUrl=fchannel.profileUrl,max_pages_limit=max_pages_limit,left_length=left_length, tweet_msg=channel_const.FACEBOOK_CALLBACK_TWEET, last_number=length_display_pages-1),
                                   context_instance=RequestContext(request,{"path":request.path}))
    else:
        try:
            tweet=request.POST.get('tweet')
            ids=request.POST.get('post_fb_ids')

            if tweet!='':
                ids_list=ids.split('SubstitutePChannel')
                for id in ids_list:
                    if id!=u'':
                        fchannel=db.get(id)
                        graph=GraphAPI(fchannel.oauthAccessToken)
                        graph.put_object('me','feed',message=tweet)
        except Exception:
            logging.exception("Failded to post for facebook pages!")
        return HttpResponseRedirect("/chan/fbpage/")                

def getUserPageGroup(access_token):
    graph = GraphAPI(access_token)
    pages_data = graph.get_connections('me','likes')['data'][:50]
    groups_data = graph.get_connections('me','groups')['data'][:50]
    return pages_data,groups_data

def getFullUserPageGroup(access_token):
    graph = GraphAPI(access_token)
    pages_data = graph.get_connections('me','likes')['data'][:50]
    groups_data = graph.get_connections('me','groups')['data'][:50]
    pages=[]
    groups=[]
    for page in pages_data:
        try:
            name = page.get('name','')
            pages.append(urllib.quote(name.encode('utf-8','ignore'))+':'+page['id'])
        except Exception, e:
            logging.error('Unexpected error when add facebook page %s : %s'%(name,str(e)))
    for group in groups_data:
        try:
            name = group.get('name','')
            groups.append(urllib.quote(name.encode('utf-8','ignore'))+':'+group['id'])
        except Exception, e:
            logging.error('Unexpected error when add facebook group %s : %s'%(name,str(e)))
    return pages,groups
   
def fanpage_list(request):
    view=ChannelView()    
    channel_list=iapi(api_const.API_M_FCHANNEL).query_base().order('nameLower')
    if len(channel_list)==0:
        return render_to_response("sns/chan/f_error.html",dict(view=view,title='Likes and Interests of Your Facebook Accounts'),context_instance=RequestContext(request))       
     
    id = request.GET.get('id',None)
    showInfo = request.GET.get('show','no')
    if showInfo == 'yes':
        show = True
    else:
        show = False
    if id is None:    
        channel=channel_list[0]
    else:
        channel = db.get(id)
    submenu=''    
    for acc in channel_list:
        login=acc.name
        if login!=channel.name:
            submenu=submenu+'<a class="accountNameList" href="javascript:void(0);" onclick="fanPageChangeAcc(\''+acc.id+'\');"><img src="'+acc.avatarUrl+'" class="iconMedium"/>&nbsp; '+acc.name+'</a>'
    params = {}
    params['view']=view
    params['avatarUrl']=channel.avatarUrl
    params['id']=channel.id
    params['login']=channel.name
    params['submenu'] = submenu
    
    if show:
        objects = FPage.all().filter('chid', channel.chid).order('nameLower').ancestor(ChannelParent.get_or_insert_parent())
    else:
        objects = FPage.all().filter('chid', channel.chid).filter('excluded', False).order('nameLower').ancestor(ChannelParent.get_or_insert_parent())
        
                
    title = "Likes and Interests of " + channel.name
    params['title']= title
    params['chid']=channel.chid
    params['post_path'] = request.path + '?id='+channel.id+'&show='+showInfo
    form = FanPageForm(initial={'showHidden':show})
    params['form'] = form
    if len(channel.pages) == 0:
        params['button'] = 'Add'
    else:
        params['button'] = 'Refresh'
    return object_list(request, 
                           objects,
                           extra_context = params,
                           paginate_by=view_const.DEFAULT_INITIAL_PAGE_SIZE, 
                           template_name='sns/chan/fbpage/fan_page_list.html' 
                           )
    
def fanpage_refresh(request):
    key_str = request.GET.get('id')
    fchannel = db.get(key_str)
    graph = GraphAPI(fchannel.oauthAccessToken)
    try:
        pages = graph.get_connections('me','likes')
        objects = pages['data']
    except Exception,ex:
        logging.error('Error when fetch fan pages for %s : %s'%(fchannel.name,str(ex))) 
        objects = []
    
    page_list = fchannel.pages
    ids = []
    excludes = fchannel.getStripExcludedPage()
    includes = fchannel.getStripPage()
    pages = objects
    for page in pages:
        if len(ids) >= 30:
            break
        if not page['id'] in includes and not page['id'] in excludes:
            ids.append(page['id'])
            name = page.get('name','')
            name = urllib.quote(name.encode('utf-8','ignore'))+':'+page['id']
            page_list.append(name)
    fchannel.pages = page_list
            
    qparams = {}
    qparams['access_token'] = fchannel.oauthAccessToken
    idstr = '(' + ','.join(ids)+')'
    query = 'SELECT  page_id,name,pic_square,page_url  FROM page WHERE page_id in %s'%idstr
    qparams['query'] =query
    qparams['format'] = 'json'
    url = 'https://api.facebook.com/method/fql.query?' +urllib.urlencode(qparams)
    data = urllib2.urlopen(url)
    content = data.read()
    infos = json.loads(content)
    
    put_objs = [fchannel]
    for info in infos:
        page_params = {}
        if info['name'] is None:
            info['name'] = ''
        page_params['name'] = info['name']
        page_params['nameLower'] = info['name'].lower()
        page_params['pageid'] = str(info['page_id'])
        page_params['key_name'] = FPage.keyName(fchannel.chid+':'+str(info['page_id']))
        page_params['chid']=fchannel.chid
        page_params['avatarUrl']= info['pic_square']
        page_params['url']= info['page_url']
        page_params['parent']= ChannelParent.get_or_insert_parent()
        fanPage = FPage(**page_params)
        put_objs.append(fanPage)
    txn_put(put_objs)
    url = '/chan/fanpage/?id=' + key_str
    return HttpResponseRedirect(url)
        

def groupmember_list(request):
    view=ChannelView()    
    list=iapi(api_const.API_M_FCHANNEL).query_base().order('nameLower')
    if len(list)==0:
        return render_to_response("sns/chan/f_error.html",dict(view=view,title='Facebook Groups of Your Facebook Accounts'),context_instance=RequestContext(request))       
     
    id = request.GET.get('id',None)
    showInfo = request.GET.get('show','no')
    if showInfo == 'yes':
        show = True
    else:
        show = False
    if id is None:    
        channel=list[0]
    else:
        channel = db.get(id)
    submenu=''    
    for acc in list:
        login=acc.name
        if login!=channel.name:
            submenu=submenu+'<a class="accountNameList" href="javascript:void(0);" onclick="MemberGroupChangeAcc(\''+acc.id+'\');"><img src="'+acc.avatarUrl+'" class="iconMedium"/>&nbsp; '+acc.name+'</a>'
    params = {}
    params['view']=view
    params['avatarUrl']=channel.avatarUrl
    params['id']=channel.id
    params['login']=channel.name
    params['submenu'] = submenu
    
    if show:
        objects = FGroup.all().filter('chid', channel.chid).order('nameLower').ancestor(ChannelParent.get_or_insert_parent())
    else:
        objects = FGroup.all().filter('chid', channel.chid).filter('excluded', False).order('nameLower').ancestor(ChannelParent.get_or_insert_parent())
    
                
    title = 'Facebook Groups of '+channel.name
    params['title']= title
    params['chid']=channel.chid
    params['post_path'] = request.path + '?id='+channel.id+'&show='+showInfo
    form = MemberGroupForm(initial={'showHidden':show})
    params['form'] = form
    if len(channel.groups) == 0:
        params['button'] = 'Add'
    else:
        params['button'] = 'Refresh'
    return object_list(request, 
                           objects,
                           extra_context = params,
                           paginate_by=view_const.DEFAULT_INITIAL_PAGE_SIZE, 
                           template_name='sns/chan/fbpage/member_group_list.html' 
                           )
    
def groupmember_refresh(request):
    id = request.GET.get('id')
    channel = db.get(id)
    graph = GraphAPI(channel.oauthAccessToken)
    try:
        groups = graph.get_connections('me','groups')
        objects = groups['data']
    except Exception,ex:
        logging.error('Error when fetch groups for %s : %s'%(channel.name,str(ex))) 
        objects = []
    
    group_list = channel.groups
    ids = []
    excludes = channel.getStripExcludedGroup()
    includes = channel.getStripGroup()
    groups = objects
    for group in groups:
        if len(ids) >= 30:
            break
        if not group['id'] in includes and not group['id'] in excludes:
            ids.append(group['id'])
            name = group.get('name','')
            name = urllib.quote(name.encode('utf-8','ignore'))+':'+group['id']
            group_list.append(name)
    channel.groups = group_list
            
    qparams = {}
    qparams['access_token'] = channel.oauthAccessToken
    idstr = '(' + ','.join(ids)+')'
    query = 'SELECT gid,pic,name FROM group WHERE gid in %s'%idstr
    qparams['query'] =query
    qparams['format'] = 'json'
    url = 'https://api.facebook.com/method/fql.query?' +urllib.urlencode(qparams)
    data = urllib2.urlopen(url)
    content = data.read()
    infos = json.loads(content)
    
    put_objs = [channel]
    for info in infos:
        group_params = {}
        group_params['name'] = info['name']
        group_params['nameLower'] = info['name'].lower()
        group_params['groupid'] = str(info['gid'])
        group_params['key_name'] = FGroup.keyName(channel.chid+':'+str(info['gid']))
        group_params['chid']=channel.chid
        group_params['avatarUrl']= info['pic']
        group_params['url']= 'http://www.facebook.com/group.php?gid='+str(info['gid'])
        group_params['parent']= ChannelParent.get_or_insert_parent()
        memberGroup = FGroup(**group_params)
        put_objs.append(memberGroup)
    txn_put(put_objs)
    url = '/chan/groupmember/?id='+id
    return HttpResponseRedirect(url)
    

def twitter_export(request):
    mid =request.GET.get('id')
    user = db.get(mid)
    uid = user.uid
    response = HttpResponse(mimetype='text/csv')
    response['Content-Disposition'] = "attachment; filename=%s.csv" % user.mail
    writer = csv.writer(response)
    writer.writerow(['Handle', 'Name', 'URL', 'Location', 'Bio','Background', 'Avatar'])
    channels = TAccount.all().filter('deleted =',False).ancestor(ChannelParent.get_or_insert_parent(uid)).order('nameLower').fetch(limit=1000)
    for channel in channels:
        channel_info = [channel.login(), channel.accountName, channel.accountUrl, channel.location,
                        channel.description, channel.backGround, channel.avatarUrl]
        writer.writerow(channel_info)
    return response


class TwitterSuspendedRestoredView(ChannelControllerView):
    def __init__(self):
        ChannelControllerView.__init__(self)
        self.sort_by = 'modifiedTime'
        self.order = 'desc'
        self.keyword = None
        self.paginate_by = view_const.DEFAULT_INITIAL_PAGE_SIZE   

    def status(self):
        pass

    def set_paginate_by(self, paginate_by):
        try:
            self.paginate_by = int(paginate_by)
        except:
            pass
        
    def real_sort_by(self):
        if self.sort_by == 'modifiedTime':
            return self.default_real_sort_by()
        else:
            return self.sort_by
    
    def default_real_sort_by(self):
        pass
    
    def query(self):
        if self.keyword:
            return self.query_keyword()
        else:
            return self.query_no_keyword()

    def query_keyword(self):
        return iapi(api_const.API_M_CHANNEL).getModel().searchIndex.search(self.keyword, filters=('state =', self.status()))

    def query_no_keyword(self):
        pass 

    def query_cutoff_time(self):
        return datetime.datetime.utcnow() - datetime.timedelta(days=1000)

    def path(self):
        pass
    

class TwitterSuspendedView(TwitterSuspendedRestoredView):
    def __init__(self):
        TwitterSuspendedRestoredView.__init__(self)
        self.viewName = 'Suspended by Twitter'

    def status(self):
        return channel_const.CHANNEL_STATE_SUSPENDED
    
    def default_real_sort_by(self):
        return 'suspendedTime'
    
    def query_no_keyword(self):
        return iapi(api_const.API_M_CHANNEL).getModel().all().filter('deleted', False).filter('isContent', True).filter('state = ', self.status()).filter('suspendedTime > ', self.query_cutoff_time()).order('-suspendedTime')    
    
    def path(self):
        return 'suspended'
                

class TwitterRestoredView(TwitterSuspendedRestoredView):
    def __init__(self):
        TwitterSuspendedRestoredView.__init__(self)
        self.viewName = 'Restored by Twitter'

    def status(self):
        return channel_const.CHANNEL_STATE_NORMAL
    
    def default_real_sort_by(self):
        return 'restoredTime'
    
    def query_no_keyword(self):
        return iapi(api_const.API_M_CHANNEL).getModel().all().filter('deleted', False).filter('isContent', True).filter('state = ', self.status()).filter('isRestored = ',True).filter('restoredTime > ', self.query_cutoff_time()).order('-restoredTime')    
            
    def path(self):
        return 'restored'


def twitter_suspended_list(request):
    return __twitter_suspended_restored_list(request, TwitterSuspendedView())


def twitter_restored_list(request):
    return __twitter_suspended_restored_list(request, TwitterRestoredView())
    

def __twitter_suspended_restored_list(request, view):
    num = len(iapi(api_const.API_M_CHANNEL).query_base().fetch(limit=view_const.SHOW_SEARCH_NUMBER))
    show_search= (num==view_const.SHOW_SEARCH_NUMBER)
    view.sort_by = req_util.get(request, 'sortby', 'modifiedTime')
    view.sort = req_util.get(request, 'directType', 'desc')
    view.keyword = req_util.get(request, 'query', '')
    view.set_paginate_by(request.GET.get('paginate_by', view_const.DEFAULT_INITIAL_PAGE_SIZE))
    objects = view.query()
    i=1
    for obj in objects:
        obj.batch=i
        i+=1
        if i>view.paginate_by:
            i=1
    page = request.GET.get('page', '1')
    total_number = len(objects)
    total_pages = total_number / view.paginate_by + 1
    if total_pages < int(page):
        page = total_pages
    show_list_info = 'True'
    if total_number < 5:
        show_list_info = 'False' 
    params = dict(view=view, form=SuspendedTwitterSortByForm(), title=view.viewName, 
                  sortBy=view.sort_by, directType=view.sort, show_list_info=show_list_info, show_search=show_search,
                  keyword=view.keyword, current_page=str(page), paginate_by=view.paginate_by, 
                  post_path="/chan/twitter/%s?sortby=%s&query=%s&paginate_by=%s" % (view.path(), view.sort_by, view.keyword, str(view.paginate_by)),
                  )
    return object_list( request, 
                        objects,
                        paginate_by=view.paginate_by,
                        page=page,
                        extra_context = params,
                        template_name='sns/chan/twitter_suspended_restored_list.html' 
                       )


def twitter_suspended_export(self):
    from sns.log.models import CmpTwitterAcctStats
    usp_now = ctz_util.uspacificnow() - datetime.timedelta(days=1)
    file_name = "SNS Analytics Suspended Acct Stats - %s.csv" % datetime.datetime.strftime(usp_now, "%Y-%m-%d")
    response = HttpResponse(mimetype='text/csv')
    response['Content-Disposition'] = "attachment; filename=%s" % file_name
    writer = csv.writer(response)
    writer.writerow(['Twitter Handle', 'Twitter ID', 'User ID', 'Suspended Time', 'Restored Time', 'Follower Count', 'Clicks - 30D', 
                     ])
    try:
        limit = 1000
        query = iapi(api_const.API_M_CHANNEL).getModel().all().filter('isContent', True).filter('state = ', channel_const.CHANNEL_STATE_SUSPENDED).order('-suspendedTime')    
        suspended_list = query.fetch(limit=limit, offset=0)
        suspended_list.extend(query.fetch(limit=limit, offset=limit))
        count = len(suspended_list)
        for channel in suspended_list:
            chid_str = channel.chid_str()
            stats = CmpTwitterAcctStats.get_by_chid(chid_str)
            row_data = [channel.name, 
                        chid_str, 
                        channel.parent().uid, 
                        time_to_usp_str(channel.suspendedTime),
                        time_to_usp_str(channel.restoredTime),
                        stats.latelyFollower if stats else 0,
                        stats.totalClick if stats else 0,
                        ]
            writer.writerow(row_data)
        logging.info("Queried total %d suspended channels." % count)
    except Exception:
        logging.exception("Unexpected error when exporting suspended channel stats!")
        return -1
    finally:
        logging.info("Completed exporting %d suspended channel stats." % count)
    return response
    

def time_to_usp_str(utc_time):
    try:
        usp_time = ctz_util.to_uspacific(utc_time)
        return datetime.datetime.strftime(usp_time, "%Y-%m-%d %H:%M:%S")
    except:
        return None
