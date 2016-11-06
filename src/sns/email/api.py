import logging
import re
import datetime
from sets import ImmutableSet
from exceptions import Exception

from google.appengine.api import mail
from google.appengine.ext import db

import context, deploysns
from common.utils import string as str_util
from common.utils import datetimeparser
from common.utils import url as url_util
from sns.serverutils import event_const
from sns.serverutils import deferred
from sns.serverutils import memcache, url as server_url_util
from sns.core.core import User, EmailCampaignParent, get_user_idMap, UserClickParent, ChannelParent
from sns.api import consts as api_const
from sns.api.base import createModelObject
from sns.api.base import BaseProcessor, deleteModelObject
from sns.camp.api import CampaignProcessor, ExecutionProcessor, SCHEDULE_EXPEDITE_FACTOR
from sns.camp import consts as camp_const
from sns.email import consts as mail_const
from sns.url.models import ShortUrlReserve, SuperLongUrlMapping
from sns.url.api import ShortUrlProcessor
from sns.usr.models import UserClickCounter, UserPostCounter, UserFailureCounter
from sns.chan.models import TAccount, ChannelClickCounter, FAccount, FAdminPage
from models import MPost, EmailList, EmailContact, EmailTemplate, MailExecution, EmailListClickCounter,\
                    EmailContactClickCounter, MailCampaign, EmailContactSubscribleState, Report, CounterPrototype, TimeOutException, TestSystemEmailList


MAIL_HANDLE_INIT = False
DB_PUT_RETRY_TIMES = 3   

def getType(type):
    
    if type == mail_const.MAIL_TEMPLATE_TYPE_GENERAL:
        return 'subSystemNotification'
    elif type == mail_const.MAIL_TEMPLATE_TYPE_NEWSLETTER:
        return 'subNewsletter'
    elif type == mail_const.MAIL_TEMPLATE_TYPE_REPORT:
        return 'subWeeklyReport'
    else:
        return None
    
    
class ListGenerator():
        
    def __init__(self, toLists, toBlackLists, cursor=mail_const.EXEC_CURSOR_START):
        self.toLists = toLists
        self.toBlackLists = toBlackLists
        self.cursor = cursor 
        self.empty_flag = False
    
    def fetch_list(self, cursor = None, limit=mail_const.EXEC_MAIL_LIST_LIMIT, type=None):
        
        if not cursor == None:
            self.cursor = cursor
        
        if self.cursor == mail_const.EXEC_CURSOR_END:
            self.empty_flag = True
            return []
        
        temp_to = {}
        logging.debug("cursor = %s" %self.cursor)
        for toId in self.toLists:
            if toId == None:
                continue
            toId = db.Key(unicode(toId))
            #to = EmailList.get(toId)
            to = db.get(toId)
            logging.debug('Executing Campaigns:to list: %s' % to)    
            if to == None:
                continue
            temp_clist = to.fetch_list(cursor=self.cursor ,limit=mail_const.EXEC_MAIL_LIST_LIMIT, type=type)
            clist = [] if temp_clist == None else temp_clist
            for c in clist:
                temp_to[c.email] = c
        
        logging.debug('Executing Campaigns:temp_to: %s' % temp_to)            
        if len(temp_to) == 0:
            self.empty_flag = True
        
        black_hashtable = {}
        for blackId in self.toBlackLists:
            blacklist = EmailList.get(blackId)
            clist = EmailContact.all().ancestor(blacklist).order('email')
            for c in clist:
                black_hashtable[c.email] = c
        logging.debug("the black list is: %s" % ",".join(black_hashtable.keys()))
                
        emails = temp_to.keys()
        emails.sort()
        return_list = emails[:limit]
            
        if len(return_list) > 0:
            self.cursor = return_list[-1]
        else:
            self.cursor = mail_const.EXEC_CURSOR_END
            self.empty_flag = True
        
        returnContactList = []
        for i in return_list[:]:
            found = False    
            if black_hashtable.has_key(i):
                logging.info('Removed duplicated email address: %s' % i)
                found = True
            if found == False:
                returnContactList.append(temp_to.get(i))
        
        logging.debug('Executing Campaigns:contact list: %s' % returnContactList)    
        return returnContactList
    
    def getCursor(self):
        return self.cursor
        
    def isEmpty(self):
        """ True if underlying list is empty. """
        return self.empty_flag 
 

class EmailContactProcessor(BaseProcessor):
    
    @classmethod
    def supportedOperations(cls):
        """"
          Supported public API operations of this processor
        """
        return ImmutableSet([
                           # api_const.API_O_CREATE, 
                           api_const.API_O_GET, 
                           api_const.API_O_UPDATE, 
                           api_const.API_O_DELETE, 
                           api_const.API_O_QUERY, 
                           api_const.API_O_APPROVE, 
                           api_const.API_O_UPGRADE, 
                           api_const.API_O_DEGRADE,
                           api_const.API_O_GETALLSTATS,
                           api_const.API_O_QUERY_ALL,
                           api_const.API_O_REFRESH,
                           api_const.API_O_IMPORT,
                           api_const.API_O_CHANGE_USER])
    
    def getModel(self):
        return EmailContact
    
    def query_base(self, **kwargs):
        q_base = BaseProcessor.query_base(self).filter('deleted', False)
        return q_base
        
    def create(self, params):
        paramsCopy = params.copy()
        key_name = EmailContact.keyName(paramsCopy['email'])
        parent = db.get(paramsCopy['parent'])
        contact = EmailContact.get_by_key_name(key_name,parent)
        if contact is not None:
            return contact                
        paramsCopy['key_name'] = key_name
        return BaseProcessor.create(self, paramsCopy)
    
    def _trans_create(self, params):
        obj = createModelObject(self.getModel(), params)
        email = params['email']
        MCSSKN = EmailContactSubscribleState.keyName(email)
        MCSS = EmailContactSubscribleState.get_by_key_name(MCSSKN, EmailCampaignParent.get_or_insert_parent())
        if not MCSS == None and MCSS.unsub == True:
            obj.unsub = True
        obj.put()
        maillist = obj.parent()
        maillist.count += 1
        maillist.put()
        return obj
    
    def import_obj(self, params):
        return db.run_in_transaction(self._trans_refresh,params)
        
    def _trans_refresh(self, params):
        id = params.get('id', None)
        if id == None:
            return 'import error, no parent!'
        parent = EmailList.get(id)
        list = params.get('contacts',[])
        contacts = []
        
        create_counte = 0
        update_counte = 0
        
        for c in list:
            email = c.get('email', None)
            firstName = c.get('firstName', None)
            lastName = c.get('lastName', None)
            fullName = c.get('fullName', None)
        
            if email:
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
                contacts.append(contact)
                if isCreate:
                    parent.count += 1
                    parent.put()
                    create_counte += 1
                else:
                    update_counte += 1
        try:
            db.put(contacts)
        except:
            logging.exception("Refreshing mail contacts exception!")
        return dict(state='success',create=create_counte,update=update_counte)
        
    def delete(self, params):
        """
        Borrowing the get() API to authenticate model type.
        Support soft delete.
        """
        if hasattr(self.getModel(), 'deleted') :
            obj = self.get(params)
            if obj is not None :
                obj.deleted = True
                obj.put()
        else :
            obj = self.get(params) 
            maillist = obj.parent()   
            temp = deleteModelObject(obj)
            maillist.count -= 1
            maillist.put()
            return temp
        
        
class EmailListProcessor(BaseProcessor):    
    def getModel(self):
        return EmailList
    
    @classmethod
    def supportedOperations(cls):
        """"
          Supported public API operations of this processor
        """
        return ImmutableSet([
                           # api_const.API_O_CREATE, 
                           api_const.API_O_GET, 
                           api_const.API_O_UPDATE, 
                           api_const.API_O_DELETE, 
                           api_const.API_O_QUERY, 
                           api_const.API_O_APPROVE, 
                           api_const.API_O_UPGRADE, 
                           api_const.API_O_DEGRADE,
                           api_const.API_O_GETALLSTATS,
                           api_const.API_O_QUERY_ALL,
                           api_const.API_O_REFRESH,
                           api_const.API_O_IMPORT,
                           api_const.API_O_CHANGE_USER])
    
    def query_base(self, **kwargs):
        q_base = BaseProcessor.query_base(self).filter('deleted', False)
        return q_base
    
    def create(self, params):
        params['parent'] =  EmailCampaignParent.get_or_insert_parent()            
        return BaseProcessor.create(self, params)
        
    def refresh(self, params):
        return db.run_in_transaction(self._trans_refresh,params)
    
    def _trans_refresh(self, params):
        lists = params.get('lists', None)
        if lists == None:
            return 'import error, no parent!'
        for list in lists:
            if not list == None:
                maillist = EmailList.get(list)
                count = 0
                start=None
                go_on = True
                while go_on:
                    contacts = EmailContact.all().filter('email >', start).ancestor(maillist).order('email').fetch(1000)
                    temp = len(contacts)
                    count += temp
                    if temp == 1000:
                        go_on = True
                        start = contacts[-1].email
                    else:
                        go_on = False
                maillist.count = count
                maillist.put()
        return 'refresh maillist success!'


class EmailTemplateProcessorError(Exception):
    pass


class EmailTemplateProcessor(BaseProcessor):
    def __init__(self):
        BaseProcessor.__init__(self)
        
    def getModel(self):
        return EmailTemplate
    
    def query_base(self, **kwargs):
        q_base = BaseProcessor.query_base(self).filter('deleted', False)
        return q_base
        
    def create(self, params):
        params['parent'] =  EmailCampaignParent.get_or_insert_parent()            
        return BaseProcessor.create(self, params)
        
    def preSendEmail(self, template, execution, include=None, exclude=None, actualRecipient=mail_const.NONE_MAIL_ACTUAL_RECIPIENT, *args, **kwargs):
        rule = execution.campaign
        rule.param = template.id
        if not include == None:
            temp = []
            for to in include:
                temp.append(db.Key(to))
            rule.toLists = temp
        if not exclude == None:
            etemp = []
            for to in exclude:
                etemp.append(db.Key(to))
            rule.toBlacklists = etemp
            
        rule.actualRecipient = actualRecipient
        
        rule.put()        
        
        self.setEmailSendParam(template, execution)
        
        OnSendEmailsCommandHandler().execute(execution, isCampaign=False)
        
    
    def setEmailSendParam(self, template, execution):
        self._execution = execution
        self._template = template
        self.success_counter = execution.success
        self.failed_counter = execution.failed
            
    def getEmailBody(self, body, *args, **kwargs):
        for i in range(0,DB_PUT_RETRY_TIMES):       
            try :
                templateBody = self._execution.templateBody
                if templateBody == None:
                    logging.info("Generating mail template body for execution id: %s " % (self._execution.id,))
                    templateBody=self._generateEmailBody(body, *args, **kwargs)
                return templateBody
            except Exception, e :
                logging.exception("Generating mail template body exception")
                if i==DB_PUT_RETRY_TIMES-1:
                    raise e
    
    def _generateEmailBody(self, body, *args, **kwargs):
        for key in kwargs.keys():
            message_box = kwargs.get(key)
            if not message_box == None:
                p = re.compile('{'+key+'}')
                body = p.sub(message_box, body)
                 
                 
        links = server_url_util.extractUrlsFromText(body)        
        urlHash_count = len(links)
        
        ruleParent = self._execution.campaign.parent()        
        shortUrlResv = ShortUrlReserve.get_by_key_name(ruleParent.key().name(),parent=ruleParent)
        if shortUrlResv is None:
            shortUrlResv = ShortUrlReserve(key_name=ruleParent.key().name(),firstCharacter=ShortUrlProcessor.randomFirstCharacter(),parent=ruleParent)
            shortUrlResv.put()
                    
        _urlMappingIdBlocks = ShortUrlProcessor.consumeShortUrlReserve(shortUrlResv.id, (mail_const.LIMIT_EMAIL_CAMPAIGN_PER_RULE if mail_const.LIMIT_EMAIL_CAMPAIGN_PER_RULE>=urlHash_count else urlHash_count))
        
        linkMappings = []
        
        for link in links:
            patern = link
            short_domain = context.get_context().short_domain()
            short_domain_with_backslash = short_domain + '/'
            if link[-len(short_domain):] == short_domain:
                patern = link + "(?!\/\w)"
            elif link[-len(short_domain_with_backslash):] == short_domain_with_backslash:
                patern = link + "(?!\w)"
            elif link.find('?') > 0:
                patern = unicode(link).replace('?', '\?')
            url = re.compile(patern)
            urlHash = shortUrlResv.firstCharacter + ShortUrlProcessor.extractShortUrlFromResv(_urlMappingIdBlocks) 
            shortURL = ''
            if not urlHash == None:
                shortURL = '%s'%server_url_util.short_url(urlHash)
            link = SuperLongUrlMapping.filterSuperLongUrl(link)
            linkMappings.append(dict(url=link, urlHash=urlHash))
            body = url.sub(shortURL, body, 1)
                    
        putPosts = []        
        for linkMapping in linkMappings:
            urlHash = linkMapping.pop('urlHash')
            url = linkMapping.pop('url')
            url = url_util.strip_url(url)
            if url is not None :
                urlHash = urlHash                
                linkMapping.update(dict(key_name=MPost.keyName(urlHash),parent=ruleParent,execution=self._execution,campaign=self._execution.campaign,urlHash=urlHash,url=url,uid=self._execution.campaign.uid))
            linkMapping.update(dict(parent=ruleParent,execution=self._execution))
            post_obj=MPost(**linkMapping)
            putPosts.append(post_obj)

        def _txn(putPosts):
            db.put(putPosts)
        db.run_in_transaction(_txn, putPosts)
        return body
        
        
    def sendEmails(self, sender, subject, body, toList, actualRecipient=mail_const.NONE_MAIL_ACTUAL_RECIPIENT):
        """
        The base sending mails method:
            - a simple expansion of 'Resume broken sending' expanding
            - add contact replacement
            - append parameters and identifiers to URLs
        """
        start = mail_const.EXEC_CURSOR_END
        if toList == None:
            toList = []
        for contact in toList:
            try:
                if self.isTimeout(timeout=10):
                    logging.info('time is out')
                    return {
                    'cursor'      :      start,
                    'errorMsg'    :     'timeout'
                    }   
                
                textBody = self.replaceContact(body, contact)
                
                textBodyReport = ''
                
                try:
                    email = contact.email
        
                    idMap = get_user_idMap(email)
                    user_id=(idMap.uid if idMap else None)
                    report=None
                    if not user_id == None:
                        report = self.generateReport(email, user_id)
                    
                    '''notifyEmail----to be changed'''    
                    email = contact.email        
                    user,notifyEmail=self.userNotifyEmail(email)
                    if notifyEmail:
                        contact.email=user.notifyEmail
                    '''end'''     
                    
                    textBodyReport = self.replaceReport(textBody, contact, report=report)
                except TimeOutException, (err_msg) :
                    logging.info('time is out')
                    return {
                    'cursor'      :      start,
                    'errorMsg'    :     'timeout'
                    }
                
                
                if actualRecipient == mail_const.NONE_MAIL_ACTUAL_RECIPIENT:
                    user,notifyEmail=self.userNotifyEmail(contact.email)
                    if notifyEmail:
                        mail.send_mail(sender=sender, to=user.notifyEmail, subject=subject, body=textBodyReport)
                    else:
                        mail.send_mail(sender=sender, to=contact.email, subject=subject, body=textBodyReport)
                else:
                    mail.send_mail(sender=sender, to=actualRecipient, subject=subject+"["+contact.email+"]", body=textBodyReport)
                
                start = contact.email
                self.success_counter += 1
            except Exception, (err_msg) :
                logging.exception("Send mail exception!")
                self.failed_counter += 1
                return {
                        'cursor'      :     start,
                        'errorMsg'    :     str(err_msg)
                        }
        return {
                'cursor'     :      start,
                'errorMsg'    :     'success'
            }   
    
    def executeSendCommand(self, sender, subject, body, listGenerator=None, actualRecipient=mail_const.NONE_MAIL_ACTUAL_RECIPIENT, *args, **kwargs):
        err_msg = ''
        
        if listGenerator == None:
            return {
                        'cursor'      :     None,
                        'errorMsg'    :     err_msg
                        } 
        
        cursor = listGenerator.getCursor()
        
        while not listGenerator.isEmpty():
            try:
                if self.isTimeout():
                    logging.info('--- time is out')
                    return {
                    'cursor'      :      cursor,
                    'errorMsg'    :     'timeout'
                    }
                    
                toList = listGenerator.fetch_list(cursor, type=getType(self._template.type)) 
                
                if toList == None:
                    toList = []
                
                dump = self.sendEmails(sender, subject, body, toList, actualRecipient)
                if dump == None:
                    break
                elif dump.get('errorMsg') == 'timeout':
                    if not dump.get('cursor') == mail_const.EXEC_CURSOR_END:
                        cursor = dump.get('cursor')
                    err_msg = dump.get('errorMsg')
                    break
                elif dump.get('errorMsg').find('required more quota')!= -1:
                    err_msg = dump.get('errorMsg')
                    break
                else:
                    cursor = dump.get('cursor')
                    err_msg = dump.get('errorMsg')
                
            except Exception, (err_msg) :
                logging.exception("sendEmails() exception!")
                return {
                        'cursor'      :     cursor,
                        'errorMsg'    :     err_msg
                        }   
        return {
                        'cursor'      :     cursor,
                        'errorMsg'    :     err_msg
                        }    
    
    def generateReport(self, email, user_id):
        modelUser = User.get_by_id(user_id)
        click_parent=UserClickParent.get_or_insert_parent(uid=user_id)
        report = memcache.get(email +':'+str(self._execution.key().id_or_name()))
        c_name = memcache.get(email +':'+str(self._execution.key().id_or_name())+':'+'channel')
        c_nameLower = str_util.lower_strip(c_name)
        f_name = memcache.get(email +':'+str(self._execution.key().id_or_name())+':'+'f_channel')
        f_nameLower = str_util.lower_strip(f_name)
        p_name = memcache.get(email +':'+str(self._execution.key().id_or_name())+':'+'page_channel')
        p_nameLower = str_util.lower_strip(p_name)
        if report == None:
            report = Report()
        else:
            memcache.delete(email +':'+str(self._execution.key().id_or_name()))
            memcache.delete(email +':'+str(self._execution.key().id_or_name())+':'+'channel')
            memcache.delete(email +':'+str(self._execution.key().id_or_name())+':'+'f_channel') 
        report.user = CounterPrototype(UserClickCounter.get_or_insert(UserClickCounter.keyName(user_id),parent=click_parent))
        userPostCounter = UserPostCounter.get_by_key_name(UserPostCounter.keyName(user_id),modelUser)
        userPostCounter.update(modelUser)
        report.tweets = CounterPrototype(userPostCounter)  
        report.failures = CounterPrototype(UserFailureCounter.get_by_key_name(UserFailureCounter.keyName(user_id), modelUser))
        
        channels = TAccount.all().ancestor(ChannelParent.get_or_insert_parent(uid=user_id)).filter('deleted =', False).filter('nameLower >', c_nameLower).order('nameLower').fetch(1000)
        for channel in channels:
            cname = channel.keyNameStrip()
            logging.debug('getting channel %s info !!!' %cname)
            
            #time.sleep(5)
            try:
                CKN = channel.key().name()
                channelClickCounter = ChannelClickCounter.get_or_insert(CKN, parent=click_parent)
                report.twitterAccounts.append(CounterPrototype(channelClickCounter, name=channel.name))
            except Exception, (err_msg) :
                logging.error('getting channel %s info error!!!' %cname)
            
            if self.isTimeout(timeout=10):
                logging.info('getting channel %s info time out' %cname)
                memcache.set(email +':'+str(self._execution.key().id_or_name())+':'+'channel', cname)
                memcache.set(email +':'+str(self._execution.key().id_or_name()), report)
                raise TimeOutException('getting channel %s info time out' %cname)
            
        f_channels = FAccount.all().ancestor(ChannelParent.get_or_insert_parent(uid=user_id)).filter('deleted =', False).filter('nameLower >', f_nameLower).order('nameLower').fetch(1000)
        
        for f_channel in f_channels:
            fname = f_channel.keyNameStrip()
            logging.debug('getting f_channel %s info !!!' %fname)
            
            #time.sleep(5)
            try:
                FCKN = f_channel.key().name()
                f_channelClickCounter = ChannelClickCounter.get_or_insert(FCKN, parent=click_parent)
                report.facebookAccounts.append(CounterPrototype(f_channelClickCounter, name=f_channel.name))
            except Exception, (err_msg) :
                logging.error('getting f_channel %s info error!!!' %fname)
            
            if self.isTimeout(timeout=10):
                logging.debug('getting f_channel %s info time out' %fname)
                memcache.set(email +':'+str(self._execution.key().id_or_name())+':'+'f_channel', fname)
                memcache.set(email +':'+str(self._execution.key().id_or_name()), report)
                raise TimeOutException('getting f_channel %s info time out' %fname)
        
        page_channels = FAdminPage.all().ancestor(ChannelParent.get_or_insert_parent(uid=user_id)).filter('deleted =', False).filter('nameLower >', p_nameLower).order('nameLower').fetch(1000)
        
        for page_channel in page_channels:
            pname = page_channel.keyNameStrip()
            logging.debug('getting p_channel %s info !!!' %pname)
            
            #time.sleep(5)
            try:
                PCKN = page_channel.key().name()
                page_channelClickCounter = ChannelClickCounter.get_or_insert(PCKN, parent=click_parent)
                report.facebookPages.append(CounterPrototype(page_channelClickCounter, name=page_channel.name))
            except Exception, (err_msg) :
                logging.error("getting page_channel error:%s" % str(err_msg)) 
            
            if self.isTimeout(timeout=10):
                logging.debug('getting page_channel %s info time out' %pname)
                memcache.set(email +':'+str(self._execution.key().id_or_name())+':'+'page_channel', pname)
                memcache.set(email +':'+str(self._execution.key().id_or_name()), report)
                raise TimeOutException('getting page_channel %s info time out' %pname)
                
        return report        
        
    def replaceReport(self, body, contact, report=None, obj=None):      
        seprater = '{'
        temp = body[:]
        while True:
            index_seprater = temp.find(seprater)
            if index_seprater > 0:
                temp = temp[index_seprater+len(seprater):]
                
                index_end = temp.find('}')
                
                if index_end > 0:
                    expression = temp[:index_end]
                    
                    if unicode(expression).strip().startswith('for:'):
                        expression = expression[expression.find('for:') + 4:]
                        endfor = temp.find('{endfor}')
                        patern = '{' + temp[:endfor+8]
                        
                        new = ""
                        list = []
                        try:
                            list = eval(expression)
                        except:
                            logging.info('Parsing Expression Error')
                            pass
                        if len(list)==0:
                            if expression.find('twitterAccounts')!=-1:
                                new = 'You have not added any Twitter account on SNS Analytics.' 
                            elif  expression.find('facebookAccounts')!=-1:
                                new = 'You have not added any Facebook account on SNS Analytics.'
                            elif  expression.find('facebookPages')!=-1:
                                new = 'You have not added any Facebook Page on SNS Analytics.'
                        for obj in list:
                            doc = temp[index_end+1:endfor]
                            new = new + self.replaceReport(doc, contact, obj=obj)
                        pi = body.find(patern)
                        body = body[:pi] + new.strip() + body[pi+len(patern):]   
                        temp = temp[endfor+8:]
                    else:
                        value = None
                        try:
                            value = eval(expression)
                        except:
                            pass
                        expression = expression.replace('(', '\(')
                        expression = expression.replace(')', '\)')
                        expression = expression.replace('.', '\.')
                        pattern = unicode(seprater + expression + '}')
                        t = re.compile(pattern)
                        body = t.sub(unicode(value), body, 1)
                        temp = temp[index_end+1:]
                else:
                    break
            else:
                break
        return body
            
    def addUnSub(self, body, contact):        
        '''notifyEmail----to be changed'''    
        email = contact.email        
        user,notifyEmail=self.userNotifyEmail(email)

        if notifyEmail:
            cid = url_util.encode_base64(user.notifyEmail)
            contact_email=user.notifyEmail
        else:
            contact_email=contact.email
            cid = url_util.encode_base64(contact.email)
        '''end'''               
        
        uid = url_util.encode_base64(self._template.parent().key().id_or_name())
        rid = url_util.encode_base64(self._execution.parent().key().id_or_name())
        tid = url_util.encode_base64(self._template.key().id_or_name())
        tail = '''
        
        

======================================================================        
This message was intended for ''' + contact_email + '''. If you do not wish to receive this type of email from SNS Analytics in the future, please click on the link below to unsubscribe.
http://'''
        tail = tail + context.get_context().short_domain() + '/email/unsub/?type=' + self._template.type+'&cid='+cid+'&uid='+uid+'&rid='+rid+'&tid='+tid+'''
SNS Analytics, Inc is located at 1463 Jamestown Drive, Cupertino, CA 95014.        
'''
        return body + tail
    
    def replaceContact(self,return_body,contact):
        '''
        add contact information at the back of the urls
        '''
        try:
            body=""
            body = body + return_body
            
            links = server_url_util.extractUrlsFromText(body)
            
            '''notifyEmail----to be changed'''    
            email = contact.email    
            user,notifyEmail=self.userNotifyEmail(email)

            if notifyEmail:
                cid = url_util.encode_base64(user.notifyEmail)
            else:
                cid = url_util.encode_base64(contact.email)
       
            
            mid = url_util.encode_base64(contact.parent().key().id_or_name())
            
            for link in links:
                patern = link
                if link.find('?') > 0:
                    patern = unicode(link).replace('?', '\?')
                url = re.compile(patern)
                
                
                if link.find('?') > 0:
                    body = url.sub(link+'&cid='+cid+'&mid='+mid, body,1)
                else :
                    body = url.sub(link+'?cid='+cid+'&mid='+mid, body,1)
        
            maillist = contact.parent()
            campaign = self._execution.parent()
            
            maillistCCKN = EmailListClickCounter.keyName(unicode(maillist.key().id_or_name()))
            EmailListClickCounter.get_or_insert(key_name=maillistCCKN, parent=campaign.parent())
            
            mailContactCCKN = EmailContactClickCounter.keyName(contact.email, unicode(maillist.key().id_or_name()), unicode(campaign.key().id_or_name()))
            EmailContactClickCounter.get_or_insert(key_name=mailContactCCKN, parent=campaign.parent(), email=contact.email, list=maillist, campaign=campaign)
                
        except Exception, (err_msg) :
            logging.info(err_msg)
            
        body = self.addUnSub(body, contact)
            
        return body
    
    def userNotifyEmail(self,email):  
        UKN = User.keyNameByEmail(email)
        user = User.get_by_key_name(UKN)
        return user,(user is not None and user.notifyEmail is not None and user.notifyEmail!='')
    

class OnSendEmailsCommandHandler(): 
       
    def execute(self, execution=None, isCampaign=True, *arg, **kwargs):
        logging.info("Executing Campaigns: OnSendEmailsCommandHandler.execute")
        if execution == None:
            return 
        
        rule = execution.campaign
        if rule == None or rule.deleted == True:
            execution.state = camp_const.EXECUTION_STATE_FAILED
            execution.put()
            logging.warning('The related rule has been deleted!')
            return 
        id = rule.param
        template = EmailTemplate.get(id)
        dump = None
        
        try:
            mailTemplateProcessor = EmailTemplateProcessor()
            mailTemplateProcessor.setEmailSendParam(template, execution)
            body = mailTemplateProcessor.getEmailBody(template.textBody)
            listGenerator = ListGenerator(rule.toLists, rule.toBlacklists, execution.dump)
            dump = mailTemplateProcessor.executeSendCommand(rule.sender, template.subject, body, listGenerator=listGenerator, actualRecipient=rule.actualRecipient)
            execution.errorMsg = dump.get('errorMsg')
            execution.success = mailTemplateProcessor.success_counter 
            execution.failed = mailTemplateProcessor.failed_counter 
            execution.templateBody = body 
            if execution.errorMsg == 'success':
                execution.dump = None
                execution.state = camp_const.EXECUTION_STATE_FINISH
                
                if not rule.getScheduleType() == camp_const.SCHEDULE_TYPE_RECURRING:
                    rule.state = camp_const.CAMPAIGN_STATE_EXPIRED
                else:
                    rule.state = camp_const.CAMPAIGN_STATE_ACTIVATED
                    if rule.scheduleEnd is not None and rule.scheduleNext > rule.scheduleEnd :
                        rule.state = camp_const.CAMPAIGN_STATE_EXPIRED
                        
            elif execution.errorMsg == 'timeout':
                execution.dump = dump.get('cursor')
                execution.state = camp_const.EXECUTION_STATE_SUSPEND
                rule.state = camp_const.CAMPAIGN_STATE_EXECUTING
                logging.info('time is out ----------')
            else:
                execution.dump = dump.get('cursor')
                execution.state = camp_const.EXECUTION_STATE_FAILED
                
                if not rule.getScheduleType() == camp_const.SCHEDULE_TYPE_RECURRING:
                    rule.state = camp_const.CAMPAIGN_STATE_ERROR
                else:
                    rule.state = camp_const.CAMPAIGN_STATE_ACTIVATED
                    if rule.scheduleEnd is not None and rule.scheduleNext > rule.scheduleEnd :
                        rule.state = camp_const.CAMPAIGN_STATE_EXPIRED
                
        except:
            logging.exception('Unknown exception!')
            
            execution.state = camp_const.EXECUTION_STATE_FAILED
            if not rule.getScheduleType() == camp_const.SCHEDULE_TYPE_RECURRING:
                rule.state = camp_const.CAMPAIGN_STATE_ERROR
            else:
                rule.state = camp_const.CAMPAIGN_STATE_ACTIVATED
                if rule.scheduleEnd is not None and rule.scheduleNext > rule.scheduleEnd :
                    rule.state = camp_const.CAMPAIGN_STATE_EXPIRED    
            
        rule.put()
        execution.put()
 
def _deferredExecuteOneHandler(processorClass, ruleId):
    context.set_deferred_context(deploy=deploysns)
    return processorClass()._executeOneHandler(ruleId)  
        
class EmailCampaignProcessor(CampaignProcessor):    
    def getModel(self):
        return MailCampaign
    
    def query_base(self, **kwargs):
        q_base = self.getModel().all().filter('deleted', False)
        return q_base
    
    def create(self, params):
        params['parent']=EmailCampaignParent.get_or_insert_parent()            
        return BaseProcessor.create(self, params)    
        
    @classmethod
    def getDefaultCampagin(cls, user, type):    
        TSMLKN = TestSystemEmailList.keyName('testSystemMailList')
        TestSystemEmailList.get_or_insert(key_name=TSMLKN, parent=EmailCampaignParent.get_or_insert_parent(), name='testSystemEmailList',nameLower='testSystemEmailList'.lower(), type=mail_const.MAIL_LIST_TYPE_SYSTEMLIST)
        
        sender = user.name+'<'+unicode(user.mail)+'>'
        
        key_name = event_const._CAMPAIGN_MAP.get(type).keyName("defaultMailCampaign")
        campaign = event_const._CAMPAIGN_MAP.get(type).get_or_insert(key_name=key_name, parent=EmailCampaignParent.get_or_insert_parent(), name=unicode('defaultMailCampaign'),nameLower=unicode('defaultMailCampaign').lower(),event=type ,isDefault=True, sender = sender, scheduleNext=datetime.datetime.utcnow(), state=camp_const.CAMPAIGN_STATE_EXPIRED)
            
        return campaign
    
    @classmethod
    def getExecution(cls, user, type):        
        rule = cls.getDefaultCampagin(user, type)
        execution = event_const._EXECUTION_MAP.get(type)(parent=rule, campaign=rule, event=rule.event, state=camp_const.EXECUTION_STATE_INIT)
        execution.put()
        return execution    
    
    @classmethod
    def supportedOperations(cls):
        return ImmutableSet([ 
                           api_const.API_O_CRON_EXECUTE, 
                           ]).union(BaseProcessor.supportedOperations())
                           
    def cron_execute(self, params):
        return self.execute(params)
    
    def _re_execute(self, params):        
        logging.debug("Re-execute suspend email campaign executions.")
        executions = MailExecution.all().filter('state >=', camp_const.EXECUTION_STATE_EXECUTING)
        exeCount = executions.count(1000)
        if exeCount>0 :
            logging.info("There are %s due suspend email campaign executions at this moment." % exeCount)
        deferredCount = 0
        for execution in executions:
            if self.isTimeout():
                return deferredCount
            if execution.state == camp_const.EXECUTION_STATE_EXECUTING: 
                if execution.executionTime > datetime.datetime.utcnow() - datetime.timedelta(minutes=5):
                    continue
            else :
                execution.state = camp_const.EXECUTION_STATE_EXECUTING
                execution.put()
            deferred.defer(self._deferredEmailSendHandler, execution)
            deferredCount += 1
        return deferredCount
                                                      
    def execute(self, params):
        """
        Query all new active rules at the moment. If the rule is executing 
        """
        self._re_execute(params)
        utcnow = datetime.datetime.utcnow()
        ruleQuery = self.query_base().filter('state', camp_const.CAMPAIGN_STATE_ACTIVATED).filter('scheduleNext <= ', utcnow).order('scheduleNext')
        ruleCount = ruleQuery.count(1000)
        logging.debug("There are %s due active email campaigns at this moment." % ruleCount)
        if ruleCount==0 :
            return 0
        activeRules = ruleQuery.fetch(ruleCount)
        rules=[]
        for rule in activeRules:
            rules.append(rule)
        logging.debug("Finish ranking for all the rules.")
        deferredCount = 0
        for rule in rules:
            if self.isTimeout():
                break
            if rule.state == camp_const.CAMPAIGN_STATE_ACTIVATED:
                rule.state = camp_const.CAMPAIGN_STATE_EXECUTING
                rule.put()
                deferred.defer(_deferredExecuteOneHandler, processorClass=self.__class__, ruleId=rule.id)
                deferredCount+=1        
        logging.info("Kicked off deferred execution for %s active email campaigns." % deferredCount)
        return deferredCount
    

    def _executeOneHandler(self, id):
        """
        Execute the one rule, keep deferring until it is fully finished execution.
        Return true if the rule is finished, else False (Timeout).
        """
        rule = None        
        try :
            rule=db.get(id)
            logging.info('Current time start:%s'%datetime.datetime.utcnow())
            if self._execute(rule) :
#                update_objs = []
#                db.put(update_objs)
                logging.info("Finished processing rule '%s'." % (rule.name))
                logging.info('Current time end:%s'%datetime.datetime.utcnow())
                return True
            else :
                logging.info("Executing Campaigns not run!")
                pass
        except Exception:
            if rule is not None:
                logging.exception("Unexpected error when executing campaign '%s'" % rule.name)
                if rule.scheduleInterval is not None:
                    rule.state = camp_const.CAMPAIGN_STATE_ACTIVATED
                    rule.scheduleNext = datetime.datetime.utcnow() + datetime.timedelta(minutes=30)
                    db.put(rule)
            else :
                logging.exception("Unexpected error! Campaign is none.")
    
    def _execute(self, rule):
        """
        Return True if the rule is finished processing normally. 
        """ 
        self._currentRule = rule
            
        try :                        
            immediate = True
            self._trans_execute(immediate)
            return True
        except :
            logging.exception("Executing Campaigns Exception!")
            if rule.scheduleInterval is not None:
                rule.state = camp_const.CAMPAIGN_STATE_ACTIVATED
                rule.scheduleNext = datetime.datetime.utcnow() + datetime.timedelta(minutes=30)
                db.put(rule)
            return False
            
    def _trans_execute(self, immediate):
        """
        Execute a post action of the rule. Raise error if the rule is not activated. 
        After post, set state to expired based on posting schedule.
        """
        rule = self._currentRule
        
        scheduleType = rule.getScheduleType()
        if scheduleType == camp_const.SCHEDULE_TYPE_NOW :
            self._execute_now(immediate)
        if scheduleType == camp_const.SCHEDULE_TYPE_ONE_TIME :
            self._execute_oneTime(immediate)
        if scheduleType == camp_const.SCHEDULE_TYPE_RECURRING :
            self._execute_recurring(immediate)
        
        logging.info('next before put ---> %s' % rule.scheduleNext)
        logging.info('name before put ---> %s' % rule.name) 
        rule.put()
        
        logging.info('next ---> %s' % rule.scheduleNext)
        logging.info('state---> %s' % rule.state)
        logging.debug('Finished post for rule: %s' % rule.name)
        return rule
    
    def _execute_now(self, immediate):
        """
        Sanity checks are already done. just go to perform the action.
        """
        self._execute_method(immediate)
    
    def _execute_oneTime(self, immediate):
        """
        Sanity checks are already done. just go to perform the action.
        """
        rule = self._currentRule
        logging.info('one time now ---> %s' % datetime.datetime.utcnow())
        logging.info('one time next---> %s' %rule.scheduleNext)
        if rule.scheduleNext > datetime.datetime.utcnow() :
            rule.state = camp_const.CAMPAIGN_STATE_ACTIVATED
            return
        self._execute_method(immediate=False)
        
    def _execute_recurring(self, immediate):
        """
        Sanity checks are already done. just go to perform the action.
        """
        rule = self._currentRule
        now = datetime.datetime.utcnow()
        logging.info('recurring now ---> %s' % now)
        logging.info('recurring next---> %s' % rule.scheduleNext)
        
        logging.info("Do executing the giving rule: '%s' " % rule.name)
        executions = MailExecution.all().ancestor(rule).filter('state >=', camp_const.EXECUTION_STATE_EXECUTING)
        exeCount = executions.count(1000)
        
        if exeCount == 0 :
            if rule.scheduleStart > now or rule.scheduleNext > now :
                rule.state = camp_const.CAMPAIGN_STATE_ACTIVATED
                return
            execution = self.getExecutionModel(rule.event)(parent=rule, campaign=rule, event=rule.event)
            execution.state = camp_const.EXECUTION_STATE_EXECUTING
            execution.put()
            rule.scheduleNext += datetimeparser.parseInterval(rule.scheduleInterval, memcache.get(SCHEDULE_EXPEDITE_FACTOR))
            rule.put()
            deferred.defer(self._deferredEmailSendHandler, execution)
                                               
    def _execute_method(self, immediate):        
        """
        Sanity checks are already done. just go to perform the action.
        """
        rule = self._currentRule
        logging.debug("Do executing the giving rule: '%s' " % rule.name)
        executions = MailExecution.all().ancestor(rule).filter('state >=', camp_const.EXECUTION_STATE_EXECUTING)
        exeCount = executions.count(1000)
        logging.info("There are %s due suspend executions at this moment." % exeCount)
        if exeCount == 0 :
            execution = self.getExecutionModel(rule.event)(parent=rule, campaign=rule, event=rule.event, state=camp_const.EXECUTION_STATE_INIT)
            execution.state = camp_const.EXECUTION_STATE_EXECUTING
            execution.put()
            logging.info('Executing Campaigns == execution:%s' % execution.id)
            deferred.defer(self._deferredEmailSendHandler, execution)  
    
    @classmethod
    def _deferredEmailSendHandler(cls,execution):
        context.set_deferred_context(deploy=deploysns)
        try:
            logging.info("Executing Campaigns:func _dispatch_event execution:%s" % execution)
            if not execution == None:
                rule = execution.campaign
                try:
                    logging.info("Executing Campaigns:func _dispatch_event")
                    if rule == None or rule.deleted == True:
                        execution.state = camp_const.EXECUTION_STATE_FAILED
                        execution.put()
                        logging.info('The related rule has been deleted!')
                    else:                        
                        OnSendEmailsCommandHandler().execute(execution=execution)
                except Exception, (err_msg) :
                    rule.state = camp_const.CAMPAIGN_STATE_ERROR
                    rule.put()
                    logging.info('processing executions error : %s' %err_msg)
        except Exception, (err_msg) :
            logging.info('defering error : %s' %err_msg)
        return
    
class EmailExecutionProcessor(ExecutionProcessor):
    def getModel(self):
        return MailExecution

        