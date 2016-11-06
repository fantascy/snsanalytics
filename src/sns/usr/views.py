import datetime
import csv
import json

from google.appengine.ext import db
from google.appengine.api import users
from django.shortcuts import render_to_response
from django.views.generic.list_detail import object_list
from django.views.generic.simple import direct_to_template
from django.template import RequestContext
from django.http import HttpResponseRedirect, HttpResponse

from common.utils import string as str_util
import context
from sns import limits as limit_const
from sns.core import consts as core_const
from sns.core.core import User, get_user, get_user_id
from sns.usr.models import GlobalUserCounter, UserClickCounter
from sns.api import consts as api_const
from sns.api import errors as api_error
from sns.api.facade import iapi
from sns.usr.api import UserProcessor
from common.view import utils as view_util
from sns.view import consts as view_const
from sns.view.baseview import BaseView
from sns.view.controllerview import ControllerView
from sns.report.views import getCounterChart
from sns.usr.forms import UserCountForm, UserDateForm, UserForm, UserTagForm


class UserControllerView(ControllerView):
    def __init__(self):
        ControllerView.__init__(self, "Home")
        

class UserView(BaseView, UserControllerView):
    def __init__(self, dailyPostLimit=None):
        BaseView.__init__(self,api_const.API_M_USER,UserForm,UserForm)
        UserControllerView.__init__(self)
        self.dailyPostLimit = dailyPostLimit
        
    def titleList(self):
        return "Users"
    
    def titleCreate(self):
        return "Create User"
    
    def titleUpdate(self):
        return "Account Settings"
    
    def titleDetail(self):
        return "User Details"
    
    def update(self, request, view, template_name="form.html", ret_url = None, extra_params={}):
        if request.method=="GET":
            form=self.read_object(request)
        elif request.method=='POST':
            form=self.update_form_class(request.POST)
            if form.is_valid():
                params=form.cleaned_data.copy()
                if params['acceptedTerms'] == None or params['acceptedTerms'] == False:
                    return HttpResponseRedirect('/usr/initset')
                self.update_object(form)
                return HttpResponse(json.dumps({'result':'success','settings_name':params['name']}), 'text/html')
        user = get_user()
        acceptedTerms = 1 if user.acceptedTerms else 0        
        params = {'form': form, 'view' : view, 'title' : self.titleUpdate(), 'type':acceptedTerms, 'ret_url':'home' }
        params.update(extra_params)
        return render_to_response('sns/' +self.api_module_name+'/' + template_name, 
                                  params,
                                  context_instance=RequestContext(request,{"path":request.path}))
        
    
def list_default(request):   
    if not users.is_current_user_admin():  
        raise api_error.ApiError(api_error.API_ERROR_ADMIN_PAGE)
    
    keyword=request.GET.get('query','')
    user_type = int(request.GET.get('type',0))
    template = "sns/usr/list.html"
    
    ret_url='usr/?query='+keyword
    paginate_by=view_const.DEFAULT_INITIAL_PAGE_SIZE
    
    objects = User.searchIndex.search(keyword) if keyword else User.all() 
    if user_type == 2:
        objects = User.searchIndex.search(keyword).filter('isContent', True)
    objects = objects.order('mail')
    try:
        uid = int(keyword)
        user = User.get_by_id(uid)
        if user is not None:
            objects = [user]
    except:
        pass
    page=request.GET.get('page','1')
    total_number=len(objects)
    total_pages=total_number/paginate_by+1
    if total_pages<int(page):
        page=total_pages
        
    useProxy = (get_user_id(check_proxy=True) != get_user_id(check_proxy=False))
            
    params=dict(view=ControllerView(), title='Users', keyword=keyword, ret_url=ret_url, \
                post_path='/usr/?paginate_by='+str(paginate_by)+'&query='+keyword+'&type='+str(user_type), \
                type=user_type, useProxy=useProxy)
    
    return object_list( request, 
                            objects,
                            page=page,
                            paginate_by=paginate_by,
                            extra_context = params,
                            template_name=template,
                            
                           )  
    
def list_container_by_date(request):
    if not users.is_current_user_admin():  
        raise api_error.ApiError(api_error.API_ERROR_ADMIN_PAGE)
    
    params=dict(view=ControllerView(),title='Users by Dates',form= UserDateForm())
    return render_to_response("sns/usr/list_container_by_date.html", params, context_instance=RequestContext(request)); 
          

def list_body_by_date(request):
    if not users.is_current_user_admin():  
        raise api_error.ApiError(api_error.API_ERROR_ADMIN_PAGE)
    datetype = request.GET.get('type')
    if datetype == 'first':
        objects = User.all().order('-firstVisit')
    elif datetype == 'last':
        objects = User.all().order('-lastVisit')
    return object_list( request, 
                            objects,
                            paginate_by=view_const.DEFAULT_INITIAL_PAGE_SIZE,
                            template_name="sns/usr/list_body_by_date.html"
                           )  


def list_container_by_click(request):
    if not users.is_current_user_admin():  
        raise api_error.ApiError(api_error.API_ERROR_ADMIN_PAGE)
    
    params=dict(view=ControllerView(),title='Users by Clicks',form= UserCountForm())
    return render_to_response("sns/usr/list_container_by_click.html", params, context_instance=RequestContext(request)); 
    

def list_body_by_click(request):
    if not users.is_current_user_admin():  
        raise api_error.ApiError(api_error.API_ERROR_ADMIN_PAGE)
    objects = UserClickCounter.all().order('-%s' % request.GET.get('type'))
    return object_list( request, 
                            objects,
                            paginate_by=view_const.DEFAULT_INITIAL_PAGE_SIZE,
                            template_name="sns/usr/list_body_by_click.html"
                           )  
      

def initset(request):
    user = get_user()
    initial_params = {'acceptedTerms':True}
    form = UserForm(initial=initial_params)
    dailyPostLimit = iapi(api_const.API_M_USER).getUserDailyPostLimit(dict(user=user))
    userView=UserView(dailyPostLimit=dailyPostLimit)
    user_type = 1 if (user.acceptedTerms == True) else 0
    return render_to_response("sns/usr/form.html", dict(form=form, user=user, type=user_type, view=userView, title=userView.titleUpdate(), ret_url='/home/'), context_instance=RequestContext(request));

def settings(request):
    usr = users.get_current_user()
    if usr is None:
        context.get_context().set_login_required(False)
        return direct_to_template(request, 'sns/index.html', dict(view = ControllerView(viewName='Home')))
    
    user=get_user()
    params = UserProcessor().convertFormat(user, "python")
    form = UserForm(params)
    dailyPostLimit = iapi(api_const.API_M_USER).getUserDailyPostLimit(dict(user=user))
    userView=UserView(dailyPostLimit=dailyPostLimit)
    user_type = 1 if (user.acceptedTerms == True) else 0
    return render_to_response("sns/usr/form.html", dict(form=form, user=user, type=user_type, view=userView, title=userView.titleUpdate(), ret_url='/home/'), context_instance=RequestContext(request));


def update(request):
    user=get_user()
    dailyPostLimit = iapi(api_const.API_M_USER).getUserDailyPostLimit(dict(user=user))
    userView=UserView(dailyPostLimit=dailyPostLimit)
    return userView.update(request, userView, ret_url='dashbord/')

def limit(request):
    name=request.GET.get('name','')
    number=request.GET.get('number',1000)
    return render_to_response("sns/usr/limit.html", dict(name=name,number=number), context_instance=RequestContext(request));

def detail(request):
    limit = limit_const.LIMIT_POST_DAILY_ADMIN
    return render_to_response("sns/usr/detail.html", dict(limit=limit), context_instance=RequestContext(request));


def export_all(request):
    userList = User.all().order('user')
    response = view_util.get_csv_response_base("SNS Analytics User List - All")
    writer = csv.writer(response)
    writer.writerow(['Email', 'Name', 'First Visit', 'Last Visit', 'Time Zone'])
    for user in userList:
        email = unicode(user.mail if user.mail != None else '').encode('utf-8')
        fullName = unicode(user.name if user.name != None else '').encode('utf-8')
        firstVisit = unicode(user.firstVisit if user.firstVisit != None else '').encode('utf-8')
        lastVisit  = unicode(user.lastVisit if user.lastVisit != None else '').encode('utf-8')
        timeZone   = unicode(user.timeZone if user.timeZone != None else '').encode('utf-8') 
        writer.writerow([email, fullName, firstVisit, lastVisit, timeZone])
    return response
       

def export_cmp(request):
    cmp_users = User.all().filter('isContent', True).fetch(limit=1000)
    response = view_util.get_csv_response_base("SNS Analytics User List - CMP")
    writer = csv.writer(response)
    writer.writerow(['ID', 'Email', 'Name', 'Tags', 'Clicks - Day', 'Clicks - Week', 'Clicks - Month', 'Clicks - Year', ])
    for user in cmp_users:
        uid = user.uid
        click_counter = UserClickCounter.get_or_insert_by_uid_update(uid)
        row_info = [uid, user.mail, user.name, user.tags, 
                    click_counter.day, click_counter.week, click_counter.month, click_counter.year, ]
        writer.writerow(row_info)
    return response
       

def getUserNumberChart(request):
    userType = request.GET.get('type')
    userCounter = GlobalUserCounter.get_or_insert_counter()
    if userType == 'total':
        counters = eval(userCounter.dailyNumber)
    elif userType == 'new':
        counters = eval(userCounter.dailyIncrease)
    timeUnit = core_const.TIME_UNIT_DAY
    units = len(counters)
    endTime = userCounter.lastUpdateTime - datetime.timedelta(days=1)
    startTime = endTime -datetime.timedelta(days=units-1)
    chart = getCounterChart(counters,timeUnit,units,startTime,endTime,title='Total Users')
    return HttpResponse(chart)
    
def userNumberChart(request):
    return render_to_response("sns/usr/user_info.html", dict(view=ControllerView(),type=request.GET.get('type')), context_instance=RequestContext(request))


def isUserLogin(request):
    if users.get_current_user() is None:
        return HttpResponse('0','text/html')
    else:
        return HttpResponse('1','text/html')

    
def tags(request):
    uid = request.REQUEST.get('id')
    if request.method=="GET":
        user = db.get(uid)
        mail = user.mail
        form = UserTagForm(initial={'tags': user.tags})
        return render_to_response("sns/usr/user_tag.html", dict(form=form, id=uid, mail=mail), context_instance=RequestContext(request))
    elif request.method=='POST':
        tags = str_util.lower_strip(request.POST.get('tag'))
        iapi(api_const.API_M_USER).update({'id':uid, 'tags':tags})
        return HttpResponse(tags)


def _csv_write_cell(text):
    return str_util.encode_utf8_if_ok(text) if text else ''


    