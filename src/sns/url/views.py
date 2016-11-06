import logging
import urllib
import deploycake
import csv
import datetime

from google.appengine.ext import db

from django.views.generic.list_detail import object_list
from django.shortcuts import render_to_response
from django.http import HttpResponseRedirect
from django.template import RequestContext
from django.http import HttpResponse

import context, deploysns
from common.utils import url as url_util, string as str_util
from common.utils import iplocation
from sns.serverutils import deferred, memcache
from sns.core.core import User, get_user, EmailCampaignParent, StandardCampaignParent, SoupCampaignParent, KeyName
from sns.api import consts as api_const
from sns.chan.models import TAccount, FAccount, FAdminPage
from sns.cont import consts as cont_const
from sns.cont import api as cont_api
from sns.log import consts as log_const
from sns.log import api as log_api
from sns.post.models import SPost
from sns.email.models import MPost
from sns.dm.models import HashDMMapping, DMCampaignClickCounter, DMCampaignParent  
from sns.ads import api as ads_api
from sns.url import consts as url_const
from sns.url import api as url_api
from sns.url.models import ShortUrlReserve, GlobalUrlCounter, GlobalUrl, GlobalShortUrl, SoupPost, WEBSITE_PARAMS_KEY, Website, SuperLongUrlMapping
from sns.view.controllerview import ControllerView
from sns.view.baseview import BaseView
from sns.url.forms import RedirectForm, EmailRedirectForm, WebSiteCreateForm, WebSiteUpdateForm, WebSiteUploadForm

 
GA_PARAM_MAP = {
    'utm_campaign':'gaCampaign',
    'utm_source':'gaSource',
    'utm_medium':'gaMedium',
    'utm_term':'gaTerm',
    'utm_content':'gaContent',
    }

CUSTOM_CHANNEL_NAME = 'customchannel'

class UrlShortenerControllerView(ControllerView):
    def __init__(self):
        context.get_context().set_login_required(False)
        ControllerView.__init__(self, "Report")
        

def _getRedirectResp(url):
    objRes = HttpResponse( status=301 )
    objRes["Location"] = url
    return objRes


def enable_ga_params(url):
    ga_blacklist = log_api.getPatternValue(log_const.PATTERN_GA_LIST)
    enable_ga = True
    url = url[url.find("//"):]
    host,url = urllib.splithost(url)
    striped_url = host.lower()
    for url_refused in ga_blacklist:
        if striped_url.endswith(url_refused):
            enable_ga = False
            break
    return enable_ga


def forbidden_dos_url(request):
    agent=context.get_context().http_user_agent().lower()
    dos_blacklist = log_api.getPatternValue(log_const.PATTERN_DOS_LIST)
    dos_forbidden=False
    for keyword_refused in dos_blacklist:
        if agent.find(keyword_refused)!=-1:
            dos_forbidden=True
            break
    return dos_forbidden


class TrackIframeView(ControllerView):
    def __init__(self):
        ControllerView.__init__(self)
        
    def ga_tracking_code(self):
        return self.ctx().surl_ga_tracking_code()


def redirect(request, urlHash):
    try:
        return _execute_redirect(request, urlHash)
    except db.ReferencePropertyResolveError, ex_ref:
        if str(ex_ref).find('camp_campaignpoly') != -1:
            logging.info("Old short URL using camp_campaignpoly, returning 404.")
            return HttpResponse(status=404)
        raise ex_ref
    

def _execute_redirect(request, urlHash):
    context.get_context().set_login_required(False)
    if request.GET.get('type') == "track_iframe":
        return render_to_response("sns/log/iframe_track_redirect.html", dict(view=TrackIframeView()), context_instance=RequestContext(request));
    if request.POST.has_key('url') and request.POST.has_key('username'):
        url = request.POST.get("url")
        urlHash = request.POST.get("urlHash")
        username = request.POST.get("username")
        country = request.POST.get("country")
        referrer = request.POST.get("referrer")
        postType = int(request.POST.get("type"))
        if postType == url_const.URLHASH_TYPE_MAIL:
            pass
        elif postType == url_const.URLHASH_TYPE_CUSTOM:
            pass
        elif postType == url_const.URLHASH_TYPE_DM:
            deferred.defer(_deferDmCounter,urlHash,username, referrer, country)
        else:  
            uid = username.split(':')[0]
            redirects = log_api.getPatternValue(log_const.PATTERN_REDIRECT_USER)
            if context.get_context().cake_toolbar_enabled() or uid in redirects:
                globalUrlCounter = GlobalUrlCounter.get_or_insert_by_surl(urlHash)
                if globalUrlCounter is not None and len(globalUrlCounter.topics)>0 and url_api.is_browser_cake_compatible():
                    url = globalUrlCounter.keyNameStrip()
                    if not log_api.on_iframe_blacklist(url):
                        titleKey = globalUrlCounter.globalUrl().titleKey
                        url = "http://%s/r/%s" % (context.get_context().long_domain(app_deploy=deploycake), titleKey.encode("utf-8"))
                        return HttpResponseRedirect(url)
            url_api.raw_click_for_spost(urlHash, username, referrer, country)
        return HttpResponseRedirect(str_util.encode_utf8_if_ok(url))
    else:
        ip = request.META.get("REMOTE_ADDR","")
            
        if forbidden_dos_url(request):
            return render_to_response("sns/403_forbidden.html",context_instance=RequestContext(request));        
        
        country_info = iplocation.get_country_info_by_qqlib(ip, context.get_context().treat_localhost_ip_as_cn())
        country = country_info[0]
        logging.debug("Remote IP info: %s %s" % (ip, ("%s %s %s %s %s") % country_info))
        if context.is_dev_mode():
            country=iplocation.get_random_country_code()
            logging.debug("Dev mode random country code is set to '%s'" % country)
    
        globalShortUrl = GlobalShortUrl.get_by_surl(urlHash)
        if globalShortUrl is None :
            return HttpResponse(status=404)
        
        referrer = context.get_context().http_user_referrer()
        redirect_mgr_clazz = REDIRECT_MGR_MAP.get(globalShortUrl.campaignParent.kind(), RedirectMgr)
        redirect_mgr = redirect_mgr_clazz(urlHash, globalShortUrl, country, referrer, request)
        if isinstance(redirect_mgr, PostRedirectMgr) and redirect_mgr.cskey in cont_const.CS_PROMOTED:
            redirect_mgr = PromotedTweetRedirectMgr(urlHash, globalShortUrl, country, referrer, request)
        return redirect_mgr.redirect()


class RedirectMgr:
    def __init__(self, urlHash, globalShortUrl, country, referrer, request):
        self.urlHash = urlHash
        self.globalShortUrl = globalShortUrl
        self.country = country
        self.referrer = referrer
        self.request = request
        self.username = KeyName.key_name_strip(globalShortUrl.campaignParent)
        self.post = self.the_post()
        self.url = SuperLongUrlMapping.getSuperLongUrl(self.orig_url(), self.globalShortUrl.campaignParent)
        self.cskey = cont_api.Domain2CSProcessor().get_cskey_by_url(self.url, context_sensitive=True)
        self.curated = False
        if self.cskey in cont_const.TROVE_CS_KEYS:
            global_url = GlobalUrl.get_by_url(self.url)
            if global_url:
                if self.cskey == cont_const.CS_TROVE_UNHOSTED and global_url.is_trove_unhosted_and_curated():
                    self.curated = True

    def redirect(self):
        return HttpResponse(status=404)
    
    def the_post(self):
        pass

    def the_post_mention_type(self):
        the_post = self.the_post()
        if the_post and the_post.troveMentionType:
            return the_post.troveMentionType
        else:
            return None
        
    def orig_url(self):
        return self.post.url if self.post else None

    def use_trove_url(self):
        if self.cskey == cont_const.CS_TROVE_HOSTED:
            return True
        if self.the_post_mention_type():
            return True
        else:
            return False
    
    def ga_params_sns(self):  
        return {
                 'utm_campaign': str_util.encode_utf8_if_ok(self.utm_campaign_sns()),
                 'utm_source': str_util.encode_utf8_if_ok(self.utm_source_sns()),
                 'utm_medium': str_util.encode_utf8_if_ok(self.utm_medium_sns()),
                 'utm_content': str_util.encode_utf8_if_ok(self.utm_content_sns()),
                 }

    def utm_campaign_sns(self):  
        pass

    def utm_source_sns(self):  
        return url_util.root_domain(self.orig_url())
    
    def utm_medium_sns(self):  
        pass

    def utm_content_sns(self):
        user = self.globalShortUrl.campaignParent.user
        return user.name if user else None


class PostRedirectMgr(RedirectMgr):
    def __init__(self, urlHash, globalShortUrl, country, referrer, request):
        RedirectMgr.__init__(self, urlHash, globalShortUrl, country, referrer, request)
        self.channel = self.post.get_channel() if self.post else None
        try:
            self.rule = self.post.campaign if self.post else None
        except:
            logging.warn("No feed campaign for urlHash %s!" % urlHash)
            self.rule = None

    def the_post(self):
        return SPost.get_by_key_name(SPost.keyName(self.urlHash), self.globalShortUrl.campaignParent)
        
    def redirect_url(self):
        if self.use_trove_url():
            trove_mention_type = self.the_post_mention_type()
            trove_ads_mgr = ads_api.AdsProcessor.get_ads_mgr(self.url, self.channel, cskey=self.cskey, context_sensitive=True)
            if trove_ads_mgr:
                redirect_url = trove_ads_mgr.get_advertised_url(self.url, mention_type=trove_mention_type)
            else:
                logging.error("URL should be trove ingested but not! %s" % self.url)
                redirect_url = self.url
        elif enable_ga_params(self.url):
            cskey = cont_api.Domain2CSProcessor().get_cskey_by_url(self.url, skip_trove=True)
            redirect_url = ads_api.AdsProcessor.add_analytics_params_advertiser(self.url, self.channel, cskey=cskey, context_sensitive=True)
        else:
            redirect_url = self.url
        return redirect_url

    def redirect(self):
        if not self.post:
            self.handle_error()
            return HttpResponse(status=404)
        redirect_url = self.redirect_url()
        REDIRECT_BOTS = ['googlebot', 'twitterbot']
        agent = context.get_context().http_user_agent()
        agent = str_util.lower_strip(agent)
        redirect_bot = None
        if agent:
            for bot in REDIRECT_BOTS:
                if agent.find(bot) != -1:
                    redirect_bot = bot
                    break
        if redirect_bot:
            redirect_url = redirect_url.encode('utf-8')
            logging.info("Redirected to bot - %s - %s" % (redirect_bot, redirect_url))
            return HttpResponseRedirect(redirect_url)
        ga_url = "/%s?type=track_iframe&%s" % (self.urlHash, urllib.urlencode(self.ga_params_sns()))
        form_params = dict(url=redirect_url, 
                           urlHash=self.urlHash, 
                           username=self.username,
                           country=self.country,
                           referrer=self.referrer,
                           type=url_const.URLHASH_TYPE_POST)
        form = RedirectForm(initial=form_params)
        return render_to_response("sns/log/track_redirect.html", dict(form=form, ga_url=ga_url), context_instance=RequestContext(self.request))

    def utm_campaign_sns(self):
        if self.rule and self.rule.gaOn:
            return self.rule.name if self.rule.gaUseCampaignName else self.rule.gaCampaign
        if not isinstance(self.channel, TAccount) or not self.channel.topics:
            return self.rule.name if self.rule else None
        utm_campaign = self.cskey
        if self.use_trove_url() and self.curated: 
            utm_campaign = "%s %s" % (utm_campaign, 'curated')
        ads_mgr = ads_api.AdsProcessor.get_ads_mgr(self.url, channel=self.channel, cskey=self.cskey, context_sensitive=True, fallback=True)
        return "%s %s" % (utm_campaign, ads_mgr.l1_topic_key_advertiser())
    
    def utm_medium_sns(self):
        if isinstance(self.channel, TAccount):
            return self.channel.chid_handle_str()
        elif isinstance(self.channel, FAccount):
            return "Facebook/%s/%s" % (self.channel.name, self.channel.chid)
        elif isinstance(self.channel, FAdminPage):
            return "FacebookPage/%s/%s" % (self.channel.name, self.channel.chid)
        else:
            return None
    
    def handle_error(self):
        allNumOrLow = True
        for char in self.urlHash:
            if not GlobalShortUrl.is_number_or_lower(char):
                allNumOrLow = False
        if allNumOrLow:
            logging.warning("The post for short URL %s of user '%d' is not found!" % (self.urlHash, self.globalShortUrl.campaignParent.uid))
            return
        else:
            posts = SPost.all().filter('urlHash', self.urlHash).fetch(limit=1)
            if len(posts) > 0:
                logging.error("Error getting post %s!" % self.urlHash)
                post = posts[0]
                postParent = post.parent()
                shortUrlResv = ShortUrlReserve.get_by_key_name(postParent.key().name(), parent=postParent)
                if shortUrlResv is not None and shortUrlResv.firstCharacter == self.urlHash[0]:
                    db.delete(shortUrlResv)
                    logging.error("Cleaned up short URL reserve error data for %s!" % postParent.keyNameStrip())
            else:
                logging.error("The post for short URL %s of user '%d' is not found!" % (self.urlHash, self.globalShortUrl.campaignParent.uid))
                return
        return
        

class PromotedTweetRedirectMgr(PostRedirectMgr):
    def __init__(self, urlHash, globalShortUrl, country, referrer, request):
        PostRedirectMgr.__init__(self, urlHash, globalShortUrl, country, referrer, request)

    def redirect_url(self):
        ads_mgr = ads_api.AdsProcessor.get_ads_mgr(self.url, self.channel, cskey=self.cskey, context_sensitive=True)
        if ads_mgr:
            redirect_url = ads_mgr.get_advertised_url(self.url)
        else:
            logging.error("No ads manager found for URL! %s" % self.url)
            redirect_url = self.url
        return redirect_url
    
    def utm_campaign_sns(self):
        return ads_api.JollyAdsMgr.utm_campaign_sns()
    

class DMRedirectMgr(RedirectMgr):
    def __init__(self, urlHash, globalShortUrl, country, referrer, request):
        RedirectMgr.__init__(self, urlHash, globalShortUrl, country, referrer, request)
        self.rule = self.post.parent() if self.post else None

    def the_post(self):
        try:
            hashDMMapping = HashDMMapping.get_by_key_name(HashDMMapping.keyName(self.urlHash), self.globalShortUrl.campaignParent)
            return hashDMMapping.mapping
        except:
            logging.error("DM Redirect mapping info for urlHash %s is missing!" % self.urlHash)
            return None
        
    def redirect(self):
        if not self.post:
            return HttpResponse(status=404)
        if enable_ga_params(self.url):
            self.url = add_analytics_params_from_campaign(self.url, self.rule)
        ga_url = "/%s?type=track_iframe&%s" % (self.urlHash, urllib.urlencode(self.ga_params_sns()))
        form_params = dict(url=self.url,
                           urlHash=self.urlHash,
                           country=self.country,
                           referrer=self.referrer,
                           username=self.username,
                           type=url_const.URLHASH_TYPE_DM)
        form = RedirectForm(initial=form_params)
        return render_to_response("sns/log/track_redirect.html", dict(form=form, ga_url=ga_url), context_instance=RequestContext(self.request))


class EmailRedirectMgr(RedirectMgr):
    def __init__(self, urlHash, globalShortUrl, country, referrer, request):
        RedirectMgr.__init__(self, urlHash, globalShortUrl, country, referrer, request)
        self.cid = self.request.GET.get('cid', '')
        self.mid = self.request.GET.get('mid', '')
        try:
            self.cid = url_util.decode_base64(str(self.cid))
            self.mid = url_util.decode_base64(str(self.mid))
        except:
            logging.exception("Error when base64 decoding mail campaign link info:")
        self.rule = self.post.execution.parent() if self.post else None

    def the_post(self):
        post = MPost.get_by_key_name(MPost.keyName(self.urlHash), parent=self.globalShortUrl.campaignParent)
        if post is None:
            logging.error("The post for short URL %s of user '%d' is not found!" % (self.urlHash, self.globalShortUrl.campaignParent.uid))
        return post
        
    def redirect(self):
        if not self.cid or not self.mid or not self.post:
            return HttpResponse(status=404)
        if enable_ga_params(self.url):
            self.url = add_analytics_params_from_campaign(self.url, self.rule)
        ga_url = "/%s?type=track_iframe&%s" % (self.urlHash, urllib.urlencode(self.ga_params_sns()))
        form_params = dict(url=self.url,
                           urlHash=self.urlHash,
                           cid=self.cid,
                           mid=self.mid,
                           username=self.username,
                           country=self.country,
                           referrer=self.referrer,
                           type=url_const.URLHASH_TYPE_MAIL)
        form = EmailRedirectForm(initial=form_params)
        return render_to_response("sns/log/track_redirect.html", dict(form=form, ga_url=ga_url), context_instance=RequestContext(self.request))
                               
    def utm_medium_sns(self):
        return "email/%s" + self.cid
    

class SoupRedirectMgr(RedirectMgr):
    def __init__(self, urlHash, globalShortUrl, country, referrer, request):
        RedirectMgr.__init__(self, urlHash, globalShortUrl, country, referrer, request)
        self.post = SoupPost.get_by_key_name(urlHash, globalShortUrl.campaignParent)

    def the_post(self):
        return SoupPost.get_by_key_name(self.urlHash, self.globalShortUrl.campaignParent)
        
    def redirect(self):  
        return HttpResponseRedirect(self.url)


REDIRECT_MGR_MAP = {
    StandardCampaignParent.kind(): PostRedirectMgr,
    EmailCampaignParent.kind(): EmailRedirectMgr,
    DMCampaignParent.kind(): DMRedirectMgr,
    SoupCampaignParent.kind(): SoupRedirectMgr,
                    }


def add_analytics_params_from_campaign(url, rule):
    if not rule: return url
    modelUser = get_user(rule.uid) 
    if modelUser.isContent:
        return url 
    if rule.gaOn:
        index = url.find('?')
        if index==-1:
            analytics_params={}
            for ga_param, rule_param in GA_PARAM_MAP.items():
                val=getattr(rule,rule_param)
                if val is not None and val!='':
                    analytics_params[ga_param]=val 
            if rule.gaUseCampaignName:
                analytics_params['utm_campaign']=rule.name    
            params=urllib.urlencode(url_util.normalize_params(analytics_params))        
            url=url+'?'+params
        else:
            query = url[index+1:]
            path = url[:index]
            values=query.split('&')
            params={}
            for value in values:
                key,item=urllib.splitvalue(value)
                params[key]=item
            if rule.gaUseCampaignName:
                params['utm_campaign']=rule.name
            for ga_param, rule_param in GA_PARAM_MAP.items():
                val=getattr(rule,rule_param)
                if val is not None and val!='':
                    params[ga_param]=getattr(rule,rule_param).encode('utf-8')
            temp = []
            for k,v in params.items():
                if k is not None and v is not None:
                    temp.append(k+'='+v)
            params = '&'.join(temp)
            url=path+'?'+params 
    return url


def _txn_mail_increment(surl, linkMapping, cid, mid, modelUser, referrer, country):
    pass   
    

def normalizeUrl(url):
    index = url.find('?')
    if index==-1:
        return url
    else:
        query = url[index+1:]
        path = url[:index]
        values=query.split('&')
        params={}
        for value in values:
            key,item=urllib.splitvalue(value)
            try:
                params[key]=urllib.quote(item,safe='%')
            except:
                params[key]=item
        temp = []
        for k,v in params.items():
            if k is not None and v is not None:
                temp.append(k+'='+v)
        params = '&'.join(temp)
        url=path+'?'+params 
        return url
 

class WebSiteView(BaseView,ControllerView):
    def __init__(self):
        BaseView.__init__(self,api_const.API_M_WEBSITE,WebSiteCreateForm,WebSiteUpdateForm)
        ControllerView.__init__(self)


def website_list(request):
    objects = Website.all()
    post_path = '/url/website/list/?paginate_by=20'
    params = {'post_path':post_path}
    return object_list( request, 
                        objects,
                        paginate_by=20,
                        extra_context = params,
                        template_name='sns/website/website_list.html'
                       )
    

def website_create(request):
    view = WebSiteView()
    return view.create(request, view, template_name="website_form.html")


def website_update(request):
    view = WebSiteView()
    return view.update(request, view, template_name="website_form.html")


def website_delete(request):
    view = WebSiteView()
    return view.delete(request)


def website_upload(request):
    if request.method == 'POST':
        rows = request.FILES['file'].readlines()
        rows.pop(0)
        deferred.defer(_deferredWebsiteInitial,rows)
        memcache.delete(WEBSITE_PARAMS_KEY)
        return HttpResponse('success')   
    else:
        form = WebSiteUploadForm()
    return render_to_response('sns/website/website_upload.html', {'form':form, 'view':ControllerView(), 'title':'Import From A CSV File'}, context_instance=RequestContext(request,{"path":request.path}))


CSV_MAP = {0:'domain',
           5:'includedKeys',
           6:'excludedKeys',
}


def _deferDmCounter(urlHash,username, referrer, country):
    globalShortUrl = GlobalShortUrl.get_by_surl(urlHash)
    hashDMMapping = HashDMMapping.get_by_key_name(HashDMMapping.keyName(urlHash), globalShortUrl.campaignParent)
    mapping = hashDMMapping.mapping
    rule = mapping.parent()
    if rule.scheduleNext > datetime.datetime.utcnow()+ datetime.timedelta(days=1) and rule.runTurn > 1:
        turn = rule.runTurn-1
    else:
        turn = rule.runTurn
    dmRuleClickCounter = DMCampaignClickCounter.get_or_insert(DMCampaignClickCounter.keyName(rule.id+'_'+str(turn)), parent=rule.parent())   
    user = User.get_by_id(rule.uid)
    dmRuleClickCounter.incrementByReferrerAndCountry(user,referrer,country)
    dmRuleClickCounter.put()
    if rule.advancedCampaign is not None:
        rule = db.get(rule.advancedCampaign)
        dmRuleClickCounter = DMCampaignClickCounter.get_or_insert(DMCampaignClickCounter.keyName(rule.id+'_'+str(rule.runTurn)), parent=rule.parent()) 
        dmRuleClickCounter.incrementByReferrerAndCountry(user,referrer,country)
        dmRuleClickCounter.put()
    
    
def _deferredWebsiteInitial(rows):
    context.set_deferred_context(deploy=deploysns)
    number = 1
    for row in rows:
        number += 1
        try:
            data = str_util.split_strip(row,',')
            for i in range(0,len(data)):
                data[i] = data[i].decode('utf-8')
            params = {}
            for i in [0,5,6]:
                try:
                    params[CSV_MAP[i]] = data[i]
                except:
                    pass
            url_api.WebsiteProcessor().create(params)
        except Exception, ex:
            logging.error('Error when initial line %d: %s'%(number,str(ex)))
            

def website_export(request):
    response = HttpResponse(mimetype='text/csv')
    response['Content-Disposition'] = 'attachment; filename=website.csv'
    writer = csv.writer(response)
    writer.writerow(['Sources ', 'Effective Params', 'Excluded Params'])
    webs = Website.all().fetch(limit=1000)
    for web in webs:
        try:
            domain = web.keyNameStrip()
            include = web.includedKeys
            exclude = web.excludedKeys
            writer.writerow([domain, include, exclude])
        except Exception,ex:
            logging.error('Error when write topic %s'%str(ex))
    return response


def global_url_get(request, url):
    globalUrl = GlobalUrl.get_by_key_name(GlobalUrl.keyName(url))
    if globalUrl is None:
        text = 'None'
    else:
        attrs = {}
        for key in globalUrl.properties().keys():
            attrs[key] = getattr(globalUrl,key)
        text = str(attrs)
    return HttpResponse(text)
        

def global_url_counter_get(request, url):
    globalUrlCounter = GlobalUrlCounter.get_by_key_name(GlobalUrlCounter.keyName(url))
    if globalUrlCounter is None:
        text = 'None'
    else:
        attrs = {}
        for key in globalUrlCounter.properties().keys():
            attrs[key] = getattr(globalUrlCounter,key)
        text = str(attrs)
    return HttpResponse(text)

