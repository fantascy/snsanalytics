import logging
import csv
import codecs
import string

from google.appengine.ext import db
from google.appengine.api import users

from django.shortcuts import render_to_response
from django.template import RequestContext
from django.http import HttpResponseRedirect, HttpResponse
from django.views.generic.list_detail import object_list

from sns.view.controllerview import ControllerView
from common.utils import url as sa_urllib
from sns.serverutils.event_const import SEND_MAILS
from sns.api import errors as api_error
from sns.api import consts as api_const
from sns.api.errors import ApiError, API_ERROR_ADMIN_PAGE
from sns.view.baseview import BaseView
from sns.view import consts as view_const
from sns.core.core import get_user, User, EmailCampaignParent, get_user_id_by_mail

from sns.dashboard.views import DashBoardControllerView
from sns.email import consts as mail_const
from sns.email.models import EmailList, EmailContact, EmailTemplate, MailCampaign, MailExecution, EmailContactSubscribleState
from sns.email.forms import EmailListCreateForm, EmailListUpdateForm, EmailTemplateCreateForm, EmailTemplateUpdateForm, EmailTemplateSendForm ,EmailContactCreateForm, EmailContactUpdateForm, EmailListUploadForm, EmailCampaignCreateForm, EmailCampaignUpdateForm,\
                            EmailCampaignSortByForm, EmailListSortByForm, EmailContactSortByForm, EmailTemplateSortByForm
from sns.email.api import EmailTemplateProcessor, EmailCampaignProcessor
from sns.camp import consts as camp_const


class EmailListView(BaseView):
    def __init__(self):
        BaseView.__init__(self, api_const.API_M_MAIL_LIST, create_form_class=EmailListCreateForm, update_form_class=EmailListUpdateForm)
        return
    
    def titleList(self):
        return "Email Lists" 
    
    def titleCreate(self):
        return "Add a Email List"
    
    def titleUpdate(self):
        return "Modify a Email List"
    
    def titleDetail(self):
        return "Email List Details"
      
      
class EmailContactView(BaseView):    
    def __init__(self):
        BaseView.__init__(self, api_const.API_M_MAIL_CONTACT, create_form_class=EmailContactCreateForm, update_form_class=EmailContactUpdateForm)
        return    
    
    def custom_form2api(self,form_params):
        form_params = BaseView.custom_form2api(self, form_params)
        return form_params.copy()    
    
    def create(self, request, view, template_name="form.html",ret_url = None):
        r"""
        temlate
            template path
        """
        if request.method=="GET":
            form=self.initiate_create_form(request) # An unbound form
        elif request.method=='POST':
            form=self.create_form_class(request.POST)
            if form.is_valid():
                params=form.cleaned_data.copy()
                if params.has_key('ret_url'):
                    ret_url=params['ret_url']
                self.create_object(form)
                id=params['parent']
                if ret_url is None :
                    return HttpResponseRedirect('/'+self.api_module_name+'/?id='+id) # Redirect after POST
                else:
                    if not ret_url.startswith('/'):
                        ret_url = "/" + ret_url
                    return HttpResponseRedirect(ret_url) # Redirect after POST

        return render_to_response('sns/' +self.api_module_name+'/'+template_name, 
                                   {'form': form, 'view' : view, 'title' : self.titleCreate()},
                                   context_instance=RequestContext(request,{"path":request.path}))
        
    def update(self, request, view, template_name="form.html", ret_url = None):
        if request.method=="GET":
            form=self.read_object(request)
        elif request.method=='POST':
            form=self.update_form_class(request.POST)      
            if form.is_valid():
                params=form.cleaned_data.copy()
                if params.has_key('ret_url'):
                    ret_url=params['ret_url']
                self.update_object(form)
                id=params['parent']                
                if ret_url is None :
                    return HttpResponseRedirect('/'+self.api_module_name+'/?id='+id) # Redirect after POST
                else :
                    return HttpResponseRedirect('/'+ret_url) # Redirect after POST

        return render_to_response('sns/' +self.api_module_name+'/' + template_name, 
                                  {'form': form, 'view' : view, 'title' : self.titleUpdate() },
                                  context_instance=RequestContext(request,{"path":request.path}))
    

class EmailTemplateView(BaseView, ControllerView):
    
    def __init__(self):
        BaseView.__init__(self, api_const.API_M_MAIL_TEMPLATE, create_form_class=EmailTemplateCreateForm, update_form_class=EmailTemplateUpdateForm)
        ControllerView.__init__(self, "Admin")
        return
    
    def titleList(self):
        return "Email Template" 
    
    def titleCreate(self):
        return "Add Email Template"
    
    def titleUpdate(self):
        return "Modify Email Template"
    
    def titleDetail(self):
        return "Email Template Details"
    
    def send(self, request):
        if not users.is_current_user_admin():  
            raise ApiError(API_ERROR_ADMIN_PAGE)
        if request.method=="GET":
            form = EmailTemplateSendForm(request.GET)
        elif request.method=='POST':
            form=EmailTemplateSendForm(request.POST)
            api_param = form.data.copy()
            include = api_param.getlist('include')
            exclude = api_param.getlist('exclude')
            id = api_param.get('id')
            actualRecipient = api_param.get('actualRecipient')
            #logging.info("--------%s" %exclude)
            try:
                if id:
                    template = EmailTemplate.get(id)
                    EmailTemplateProcessor().preSendEmail(template, EmailCampaignProcessor.getExecution(get_user(), SEND_MAILS), include=include, exclude=exclude, actualRecipient=actualRecipient)
            except Exception, (err_msg):
                logging.info(err_msg)
            return HttpResponseRedirect('/'+api_const.API_M_MAIL_TEMPLATE) # Redirect after POST
                
    
    
        return render_to_response('sns/' +api_const.API_M_MAIL_TEMPLATE+'/sendform.html', 
                                   {'form': form},
                                   context_instance=RequestContext(request, {"path":request.path}))


def list(request,extra_params=dict(sortByType='type')):
#    if not users.is_current_user_admin():  
#        raise ApiError(API_ERROR_ADMIN_PAGE)
#    mailListView=EmailListView()
#    extra_params = dict(form=EmailListSortByForm(), sortByType=extra_params.get('sortByType'), model_name='EmailList')  
#    return mailListView.list(request, mailListView, extra_params=extra_params)

    if not users.is_current_user_admin():  
        raise ApiError(API_ERROR_ADMIN_PAGE)
    
    sortBy = request.GET.get('sortby', extra_params.get('sortByType'))
    directType = request.GET.get('directType', 'asc')
    paginate_by = request.GET.get('paginate_by', view_const.DEFAULT_INITIAL_PAGE_SIZE)
    try:
        paginate_by = int(paginate_by)
    except:
        paginate_by = view_const.DEFAULT_INITIAL_PAGE_SIZE
        
    keyword=request.GET.get('query','')
        
    if not keyword or keyword == '':
        objects = EmailList.all().filter('deleted =',False).filter('type <', mail_const.MAIL_LIST_TYPE_SYSTEMLIST).ancestor(EmailCampaignParent.get_or_insert_parent()).order(('-' if directType == 'desc' else '')+sortBy).fetch(1000)
    else:
        objects = EmailList.searchIndex.search(keyword, filters=('deleted =',False,'type <', mail_const.MAIL_LIST_TYPE_SYSTEMLIST)).ancestor(EmailCampaignParent.get_or_insert_parent())

    page=request.GET.get('page','1')
    paginate_by=paginate_by
    total_number=len(objects)
    total_pages=total_number/paginate_by+1
    if total_pages<int(page):
        page=total_pages
    show_list_info='True'
    if total_number<5:
        show_list_info='False'
    ret_url = api_const.API_M_MAIL_LIST +'/list?query='+keyword+'&sortby='+sortBy+'&directType='+directType+'&paginate_by='+str(paginate_by)+'&page='+str(page)
    ret_url = string.replace(ret_url,'&','replaceCut')
    params=dict(view=ControllerView(),form=EmailListSortByForm(), title='Email Lists',show_list_info=show_list_info,ret_url=ret_url, current_page=str(page),sortBy=sortBy, directType=directType, paginate_by= paginate_by,post_path='/email/list?sortby='+sortBy+'&directType='+directType+'&paginate_by='+str(paginate_by), keyword=keyword)
    params.update(extra_params)

    return object_list( request, 
                            objects,
                            paginate_by=paginate_by,
                            page=page,
                            extra_context = params,
                            template_name='sns/' +api_const.API_M_MAIL_LIST +"/list.html"
                           )    
    
def create(request):
    mailListView=EmailListView()
    return mailListView.create(request, mailListView)

def update(request):
    mailListView=EmailListView()
    return mailListView.update(request, mailListView)

def delete(request):
    try:
        mailListView=EmailListView()
        response = mailListView.delete(request)
        return response
    except Exception,ex:
        logging.error('Delete mail list error:%s' % str(ex))
        return HttpResponse("Exception:"+str(ex))

def export(request):
    mailListId = request.GET.get('id',None)
    keyword=request.GET.get('query','')
    ret_url=api_const.API_M_MAIL_LIST +'/list?query='+keyword
    if not mailListId == None:
        mailList = EmailList.get(mailListId)
        contactList = EmailContact.all().ancestor(mailList).order('email')
        response = HttpResponse(mimetype='text/csv')
        response.write('\xEF\xBB\xBF')
        response['Content-Disposition'] = 'attachment; filename='+mailList.name+'.csv'
        writer = csv.writer(response)
        writer.writerow(['email', 'firstName', 'lastName', 'fullName'])
        for contact in contactList:
            email = unicode(contact.email if contact.email != None else '').encode('utf-8')
            fn = unicode(contact.firstName if contact.firstName != None else '').encode('utf-8')
            ln = unicode(contact.lastName if contact.lastName != None else '').encode('utf-8')
            fullName = unicode(contact.fullName if contact.fullName != None else '').encode('utf-8')
            writer.writerow([email, fn, ln, fullName])
        return response
    
    return HttpResponseRedirect('/'+ret_url)   

def importFromCSV(request):
    
    if request.method == 'POST':
        id = request.POST.get('list',None) 
        file = request.FILES['file']
        
        parent = EmailList.get(id)
        
        header_row = None
        index_email = None
        index_fullName = None
        index_firstName = None
        index_lastName = None
        
        
        rows = file.readlines()
        for row in rows:
            
            if row[:3] == codecs.BOM_UTF8:
                row = row[3:]
            row = row.replace('\r\n','')
            row = row.split(',')
            if row==None or row==['']:
                continue
            if not header_row:
                
                header_row = row
                logging.info('%s' %header_row)
                try:
                    index_email = header_row.index('email')
                    index_fullName  = header_row.index('fullName')
                except Exception, (err_msg) :
                    logging.info("header data error%s" %err_msg)
                
                try:
                    index_firstName = header_row.index('firstName')
                    index_lastName  = header_row.index('lastName')
                except:
                    pass
                
                continue
            email = row[index_email]
            firstName = row[index_firstName] if index_firstName != None else ''
            lastName  = row[index_lastName]  if index_lastName  != None else ''
            fullName  = row[index_fullName]
            
            def inx(email, fullName, firstName, lastName, parent):
                
                MCKN = EmailContact.keyName(email)
                contact = EmailContact.get_by_key_name(MCKN, parent)
                isCreate = False
                if contact == None:
                    isCreate = True
                    contact = EmailContact(key_name=MCKN, parent=parent,email=unicode(email),firstName=unicode(firstName),lastName=unicode(lastName),fullName=unicode(fullName))
                
                MCSSKN = EmailContactSubscribleState.keyName(email)
                MCSS = EmailContactSubscribleState.get_by_key_name(MCSSKN, EmailCampaignParent.get_or_insert_parent())
                if not MCSS == None and MCSS.unsub == True:
                    contact.unsub = True
                contact.put()
                if isCreate:
                    parent.count += 1
                    parent.put()
                logging.info('finish import contact for %s%s' %(email,parent.name))
                
            try:
                db.run_in_transaction(inx, email, fullName, firstName, lastName, parent)
            except Exception, (err_msg) :
                logging.info("import data error%s" %err_msg)
                return HttpResponse('error') 
            
        return HttpResponse('success')  
    else:  
        #id = request.GET.get('list',None)
        uploadFrom = EmailListUploadForm()  
        ret_url = request.GET.get('ret_url',None)
        ret_url = string.replace(ret_url,'replaceCut','&')
    return render_to_response('sns/' +api_const.API_M_MAIL_CONTACT+'/CSVUploadForm.html', {'form':uploadFrom, 'view':ControllerView(), 'title':'Import From A CSV File', 'ret_url':ret_url}, context_instance=RequestContext(request,{"path":request.path}))

def contact_list(request,extra_params=dict(sortByType='email')):  
#    emailContactView=EmailContactView()
#    extra_params = dict(form=EmailContactSortByForm(), sortByType=extra_params.get('sortByType'), model_name='EmailContact')  
#    return emailContactView.list(request, emailContactView, extra_params=extra_params)  
    if not users.is_current_user_admin():  
        raise api_error.ApiError(api_error.API_ERROR_ADMIN_PAGE)

    parent_id = request.GET.get('id','')
    parent = EmailList.get(parent_id)
    
    sortBy = request.GET.get('sortby', extra_params.get('sortByType'))

    directType = request.GET.get('directType', 'asc')
    paginate_by = request.GET.get('paginate_by', view_const.DEFAULT_INITIAL_PAGE_SIZE)
    try:
        paginate_by = int(paginate_by)
    except:
        paginate_by = view_const.DEFAULT_INITIAL_PAGE_SIZE
        
    keyword=request.GET.get('query','')
        
    if not keyword or keyword == '':
        objects = EmailContact.all().ancestor(parent).order(('-' if directType == 'desc' else '')+sortBy).fetch(1000)
    else:
        objects = EmailContact.searchIndex.search(keyword).ancestor(parent)

    page=request.GET.get('page','1')
    paginate_by=paginate_by
    total_number=len(objects)
    total_pages=total_number/paginate_by+1
    if total_pages<int(page):
        page=total_pages
    show_list_info='True'
    if total_number<5:
        show_list_info='False'
    ret_url = api_const.API_M_MAIL_CONTACT +'/?id='+parent_id+'&query='+keyword+'&sortby='+sortBy+'&directType='+directType+'&paginate_by='+str(paginate_by)+'&page='+str(page)
    #ret_url = string.replace(ret_url,'&','replaceCut')
    params=dict(view=ControllerView(),form=EmailContactSortByForm(), title='Email Contact ' + parent.name, show_list_info=show_list_info, ret_url=ret_url, current_page=str(page),sortBy=sortBy, directType=directType, paginate_by= paginate_by,post_path='/email/contact/?id='+parent_id+'&sortby='+sortBy+'&directType='+directType+'&paginate_by='+str(paginate_by), keyword=keyword)
    params.update(extra_params)

    logging.info(len(objects))
    return object_list( request, 
                            objects,
                            paginate_by=paginate_by,
                            page=page,
                            extra_context = params,
                            template_name='sns/' +api_const.API_M_MAIL_CONTACT +"/list.html"
                           )
    
def contact_create(request):
    contactView=EmailContactView()
    return contactView.create(request, EmailContactView)

def contact_update(request):
    contactView=EmailContactView()
    return contactView.update(request, EmailContactView)

def contact_delete(request):
    try:
        contactView=EmailContactView()
        response = contactView.delete(request)
        return response
    except Exception,ex:
        logging.error('Delete mail contact error:%s' % str(ex))
        return HttpResponse("Exception:"+str(ex))

def template_list(request,extra_params=dict(sortByType='nameLower')):
    if not users.is_current_user_admin():  
        raise ApiError(API_ERROR_ADMIN_PAGE)
    emailTemplateView=EmailTemplateView()
    extra_params = dict(form=EmailTemplateSortByForm(), sortByType=extra_params.get('sortByType'), model_name='EmailTemplate')  
    return emailTemplateView.list(request, emailTemplateView, extra_params=extra_params)  

def template_create(request):
    templateView=EmailTemplateView()
    return templateView.create(request, templateView)

def template_update(request):
    templateView=EmailTemplateView()
    return templateView.update(request, templateView)

def template_delete(request):
    try:
        templateView=EmailTemplateView()
        response = templateView.delete(request)
        return response
    except Exception,ex:
        logging.error('Delete mail template error:%s' % str(ex))
        return HttpResponse("Exception:"+str(ex))

def template_send(request):
    templateView=EmailTemplateView()
    return templateView.send(request)


class EmailCampaignView(BaseView, ControllerView):

    def __init__(self):
        BaseView.__init__(self, api_const.API_M_MAIL_CAMPAIGN, create_form_class=EmailCampaignCreateForm, update_form_class=EmailCampaignUpdateForm)
        ControllerView.__init__(self, "Admin")
        return
    
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
        params['gaMedium']='email'
        params['gaUseCampaignName']=True
        params['gaOn'] = True
        return params
    
    def custom_api2form(self,api_params):
        params = BaseView.custom_api2form(self,api_params)
        if params['gaSource'] is None or params['gaSource']=='':
            params['gaSource']=camp_const.CAMPAIGN_ANALYTICS_SOURCE_DEFAULT
        if params['gaMedium'] is None or params['gaMedium']=='':
            params['gaMedium']='email'
        return params      
    
    def titleList(self):
        return "Email Campaigns" 
    
    def titleCreate(self):
        return "Add a Email Campaign"
    
    def titleUpdate(self):
        return "Modify a Email Campaign"
    
    def titleDetail(self):
        return "Email Campaign Details"
    

def campaign_list(request):
    view = EmailCampaignView()
    return view.list(request, view, extra_params={'form':EmailCampaignSortByForm(),'sortByType':'nameLower'})
    
def campaign_create(request):
    mailCampaignView = EmailCampaignView()
    return mailCampaignView.create(request, mailCampaignView)

def campaign_update(request):
    mailCampaignView = EmailCampaignView()
    return mailCampaignView.update(request, mailCampaignView)

def campaign_delete(request):
    try:
        mailCampaignView=EmailCampaignView()
        response = mailCampaignView.delete(request)
        return response
    except Exception,ex:
        logging.error('Delete mail campaign error:%s' % str(ex))
        return HttpResponse("Exception:"+str(ex))

def campaign_detail(request, id):
    mailCampaignView = EmailCampaignView()
    return mailCampaignView.detail(request, id, mailCampaignView)

def activate(request):
    mailCampaignView = EmailCampaignView()
    return mailCampaignView.activate(request)

def deactivate(request):
    mailCampaignView = EmailCampaignView()
    return mailCampaignView.deactivate(request)
    
def record(request):
    ruleid = request.GET.get('id','')
    if ruleid:
        rule=MailCampaign.get(ruleid)
        result=MailExecution.all().order('-executingTime').ancestor(rule)
    else:
        result=MailExecution.all().order('-executingTime')
    return object_list(request, 
                       result,paginate_by=view_const.DEFAULT_INITIAL_PAGE_SIZE, 
                       template_name='sns/' +api_const.API_M_MAIL_EXECUTION + '/list.html', 
                       extra_context={"ruleid":ruleid, 'view':EmailCampaignView(), 'title':'Campaign Execution Records'})
    
def unsubscribe(request):
    try:
        type = request.GET.get('type', None)
        cid = request.GET.get('cid', None)
        uid = request.GET.get('uid', None)
        rid = request.GET.get('rid', None)
        tid = request.GET.get('tid', None)
        
        try:
            cid = sa_urllib.decode_base64(str(cid))
            uid = sa_urllib.decode_base64(str(uid))
            rid = sa_urllib.decode_base64(str(rid))
            tid = sa_urllib.decode_base64(str(tid))
        except Exception:
            logging.error("Email unsub decode error!")

        user_id=get_user_id_by_mail(cid)
        user = User.get_by_id(user_id)
        
        if not user == None:
            return HttpResponseRedirect('/usr/settings')
        else:
            parent = EmailCampaignParent.get_by_key_name(uid)
            MCSSKN = EmailContactSubscribleState.keyName(cid)
            mailContactSubscribleState = EmailContactSubscribleState.get_or_insert(key_name=MCSSKN, parent=parent, email=cid, unsubTemplateid=tid, unsubCampaignId=rid)
            if mailContactSubscribleState.unsub == True:
                return render_to_response('sns/unsub.html', dict(view=DashBoardControllerView(), message1="You've already unsubscribed "+cid+" from SNS Analytics general marketing mail list."), context_instance=RequestContext(request,{"path":request.path}))
            mailContactSubscribleState.unsub = True
            mailContactSubscribleState.put()
            
            maillists = EmailList.all().ancestor(parent).filter('type = ', mail_const.MAIL_LIST_TYPE_NORMAL)
            for maillist in maillists:
                MCKN = EmailContact.keyName(cid)
                contact = EmailContact.get_by_key_name(MCKN, maillist)
                if not contact == None:
                    contact.unsub = True
                    contact.put()
                
                #return HttpResponseRedirect('/sns/unsub.html')
                
                return render_to_response('sns/unsub.html', dict(view=DashBoardControllerView(), message1="You've successfully unsubscribed "+cid+" from SNS Analytics general marketing mail list."), context_instance=RequestContext(request,{"path":request.path}))
    except:
        logging.exception("Email unsub exception!")
        return render_to_response('sns/unsub.html', dict(view=DashBoardControllerView(), message1="Unsub Failure",message2="You've failed to unsubscribe SNS Analytics general marketing mail list. Please make sure you have typed in the full unsub URL.", message3="If you can't resolve your problem, please send email to ", email="support@snsanalytics.com"), context_instance=RequestContext(request,{"path":request.path}))
    
def test(request):
    from sns.camp.api import CampaignProcessor
    CampaignProcessor().cron_execute('')
    
    return campaign_list(request)

    
    