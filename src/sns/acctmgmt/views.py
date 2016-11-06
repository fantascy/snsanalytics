import StringIO

from django.template import RequestContext
from django.http import HttpResponse
from django.shortcuts import render_to_response

from common import consts as common_const
from sns.serverutils import deferred
import context
from sns.api import consts as api_const
from sns.acctmgmt.api import CmpAccountProcessor
from sns.view.controllerview import ControllerView
from sns.view.baseview import BaseView
from sns.acctmgmt.forms import  CmpAccountUploadForm, CmpAccountPwduploadForm, YahooCreateForm, YahooUpdateForm, YahooSortByForm


class CmpAccountUploadView(BaseView, ControllerView):
    def __init__(self):
        BaseView.__init__(self,api_const.API_M_ACCTMGMT_CMP)
        ControllerView.__init__(self)
    
    def title(self):
        return 'Upload All CMP Channels from CSV File'
        

def cmp_upload(request):
    if context.is_frontend():
        return HttpResponse(common_const.BACKEND_REQUIRED_MSG)
    if request.method == 'POST':
        data = StringIO.StringIO(request.FILES['file'].read())
        return HttpResponse(deferred.defer(CmpAccountProcessor.upload, data))
    else:
        view = CmpAccountUploadView()
        form = CmpAccountUploadForm()
        return render_to_response('sns/acctmgmt/cmp/upload.html', dict(form=form, view=view, title=view.title()), context_instance=RequestContext(request, {"path":request.path}))
    

class CmpAccountPwduploadView(BaseView, ControllerView):
    def __init__(self):
        BaseView.__init__(self, api_const.API_M_ACCTMGMT_CMP)
        ControllerView.__init__(self)
    
    def title(self):
        return "Upload Twitter Credentials"
        

def cmp_pwdupload(request):
    if context.is_frontend():
        return HttpResponse(common_const.BACKEND_REQUIRED_MSG)
    if request.method == 'POST':
        data = StringIO.StringIO(request.FILES['file'].read())
        return HttpResponse(deferred.defer(CmpAccountProcessor.pwdupload, data))
    else:
        view = CmpAccountPwduploadView()
        form = CmpAccountPwduploadForm()
        return render_to_response('sns/acctmgmt/cmp/pwdupload.html', dict(form=form, view=view, title=view.title()), context_instance=RequestContext(request, {"path":request.path}))
    

class YahooControllerView(ControllerView):
    def __init__(self):
        ControllerView.__init__(self, "Yahoo account")
        

class YahooView(BaseView, YahooControllerView):
    def __init__(self):
        BaseView.__init__(self, api_const.API_M_ACCTMGMT_YAHOO, YahooCreateForm, YahooUpdateForm)
        YahooControllerView.__init__(self)

    def titleList(self):
        return "Yahoo Accounts"
    
    def titleCreate(self):
        return "Add Yahoo Account"
    
    def titleUpdate(self):
        return "Update Yahoo Account"
    
    def titleDetail(self):
        return "Twitter Account Details"
         

def yahoo_list(request):
    view = YahooView()
    extra_params = dict(form=YahooSortByForm(),sortByType='nameLower')
    return view.list(request, view, extra_params=extra_params)

def yahoo_delete(request):
    view = YahooView()
    response = view.delete(request)
    return response

def yahoo_create(request):
    view = YahooView()
    return view.create(request, view)

def yahoo_update(request):
    view = YahooView()
    return view.update(request, view)

def yahoo_detail(request):
    view = YahooView()
    return view.detail(request, view)

