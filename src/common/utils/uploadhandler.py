'''
Created on 2010-4-8

@author: sona
'''

try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.files.uploadedfile import TemporaryUploadedFile, InMemoryUploadedFile
from django.utils import importlib
from django.core.files.uploadhandler import FileUploadHandler, StopFutureHandlers, MemoryFileUploadHandler
from sns.email.models import EmailList, EmailContact, EmailContactSubscribleState
from google.appengine.ext import db
from sns.core.core import get_user,EmailCampaignParent
from django.core.cache import cache
import logging
import codecs
import string
import time

from time import sleep



class CSVMemoryFileUploadHandler(FileUploadHandler):
    
    chunk_size = 64 * 16
    
    left = ''
    
    header_row = None
    """
    File upload handler to stream uploads into memory (used for small files).
    """
    def __init__(self, request=None):
        super(CSVMemoryFileUploadHandler, self).__init__(request)
        
        self.formhash = self.request.GET.get('formhash',None)  
        cache.add(self.formhash, {})  
        self.activated =True 
        
        if request.method == 'POST':
              
            self.activated =True  
            
            id = request.GET.get('list',None)
            logging.info('---------------%s'%unicode(id))
            self.parent = EmailList.get(id)
            
    def handle_raw_input(self, input_data, META, content_length, boundary, encoding=None):
        """
        Use the content_length to signal whether or not this handler should be in use.
        """
        # Check the content-length header to see if we should
        # If the the post is too large, we cannot use the Memory handler.
        logging.info('-------------start to receive date----------------')
        self.contentLength = content_length
        self.activated = True  
          
    def new_file(self, *args, **kwargs):
        super(CSVMemoryFileUploadHandler, self).new_file(*args, **kwargs)
        if self.activated:  
            fields = cache.get(self.formhash)  
            fields[self.field_name] = 0  
            cache.set(self.formhash, fields) 
              
          
    def receive_data_chunk(self, raw_data, start):  
#        time.sleep(5) for local test, it slow down the upload speed
        logging.info('------------%s-------------'%start)
        if self.activated:
            
            fields = cache.get(self.formhash)  
            fields[self.field_name] = start  
            cache.set(self.formhash, fields)
            
            csv = self.left + str(raw_data)
            rows = csv.split('\r\n')
            
            if not rows == None and len(rows) > 0:
                temp_rows = rows[:]
                if start < self.contentLength:
                    temp_rows = rows[:-1]
                    
                for row in temp_rows:
                    if row[:3] == codecs.BOM_UTF8:
                        row = row[3:]
                    row = row.split(',')
                    if row==None or row==['']:
                        break
                    if not self.header_row:
                        
                        self.header_row = row
                        logging.info('%s' %self.header_row)
                        try:
                            self.index_email = self.header_row.index('email')
                            self.index_fullName  = self.header_row.index('fullName')
                        except Exception, (err_msg) :
                            logging.info("header data error%s" %err_msg)
                            return raw_data
                        
                        try:
                            self.index_firstName = self.header_row.index('firstName')
                            self.index_lastName  = self.header_row.index('lastName')
                        except:
                            pass
                        
                        continue
                    email = row[self.index_email]
                    firstName = row[self.index_firstName] if self.index_firstName != None else ''
                    lastName  = row[self.index_lastName]  if self.index_lastName  != None else ''
                    fullName  = row[self.index_fullName]
                    
                    def inx(email, fullName, firstName,lastName):
                        MCKN = EmailContact.keyName(email)
                        MCSSKN = EmailContactSubscribleState.keyName(email)
                        MCSS = EmailContactSubscribleState.get_by_key_name(MCSSKN, EmailCampaignParent.get_or_insert_parent())
                        if not MCSS == None and MCSS.unsub == True:
                            MCSS.unsub = True
                        contact = EmailContact.get_by_key_name(MCKN, self.parent)
                        if contact == None:
                            contact = EmailContact(key_name=MCKN, parent=self.parent,email=unicode(email.decode('utf-8')),firstName=unicode(firstName.decode('utf-8')),lastName=unicode(lastName.decode('utf-8')),fullName=unicode(fullName).decode('utf-8')) 
                        contact.unsub = True
                        contact.put()
                        logging.info('import contact--------->%s' %email)
                    try:
                        db.run_in_transaction(inx, email, fullName, firstName,lastName)
                    except Exception, (err_msg) :
                        logging.info("import data error%s" %err_msg)
                
                self.left = rows[-1]
                    
            else:
                return raw_data
        else:
            return raw_data 
      
    def file_complete(self, file_size):
        """
        Return a file object if we're activated.
        """
        if not self.activated:
            return

        return InMemoryUploadedFile(
            file = None,
            field_name = self.field_name,
            name = self.file_name,
            content_type = self.content_type,
            size = self.contentLength,
            charset = self.charset
        )
        
    def upload_complete(self):  
        if self.activated:  
            fields = cache.get(self.formhash)  
            fields[self.formhash] = -1  
            cache.set(self.formhash, fields)
          
class LogFileUploadHandler(FileUploadHandler):
    
    chunk_size = 64 * 16
      
    def __init__(self, request=None):  
        super(LogFileUploadHandler, self).__init__(request)  
        if 'formhash' in self.request.GET:  
            self.formhash = self.request.GET['formhash']  
            cache.add(self.formhash, {})  
            self.activated =True  
        else:  
            self.activated = False  
          
    def new_file(self, *args, **kwargs):  
        super(LogFileUploadHandler, self).new_file(*args, **kwargs)  
        if self.activated:  
            fields = cache.get(self.formhash)  
            fields[self.field_name] = 0  
            cache.set(self.formhash, fields)  
              
          
    def receive_data_chunk(self, raw_data, start):  
#        time.sleep(5) for local test, it slow down the upload speed
        time.sleep(1)
        logging.info('receive data from -------------> %s'%start)  
        if self.activated:  
            fields = cache.get(self.formhash)  
            fields[self.field_name] = start  
            cache.set(self.formhash, fields)  
        return raw_data  
      
    def file_complete(self, file_size):  
        if self.activated:  
            fields = cache.get(self.formhash)  
            fields[self.field_name] = -1  
            cache.set(self.formhash, fields)  
          
    def upload_complete(self):  
        if self.activated:  
            fields = cache.get(self.formhash)  
            fields[self.formhash] = -1  
            cache.set(self.formhash, fields)
            


class UploadProgressCachedHandler(MemoryFileUploadHandler):
    """
    Tracks progress for file uploads.
    The http post request must contain a query parameter, 'X-Progress-ID',
    which should contain a unique string to identify the upload to be tracked.
    """

    def __init__(self, request=None):
        super(UploadProgressCachedHandler, self).__init__(request)
        self.progress_id = None
        self.cache_key = None

    def handle_raw_input(self, input_data, META, content_length, boundary, encoding=None):
        logger = logging.getLogger('uploaddemo.upload_handlers.UploadProgressCachedHandler.handle_raw_input')
        self.content_length = content_length
        if 'X-Progress-ID' in self.request.GET:
            self.progress_id = self.request.GET['X-Progress-ID']
        if self.progress_id:
            self.cache_key = "%s_%s" % (self.request.META['REMOTE_ADDR'], self.progress_id )
            cache.set(self.cache_key, {
                'state': 'uploading',
                'size': self.content_length,
                'received': 0
            })
            if settings.DEBUG:
                logger.debug('Initialized cache with %s' % cache.get(self.cache_key))
        else:
            logging.getLogger('UploadProgressCachedHandler').error("No progress ID.")

    def new_file(self, field_name, file_name, content_type, content_length, charset=None):
        pass

    def receive_data_chunk(self, raw_data, start):
        logger = logging.getLogger('uploaddemo.upload_handlers.UploadProgressCachedHandler.receive_data_chunk')
        if self.cache_key:
            data = cache.get(self.cache_key)
            if data:
                data['received'] += self.chunk_size
                cache.set(self.cache_key, data)
                if settings.DEBUG:
                    logger.debug('Updated cache with %s' % data)
        return raw_data

    def file_complete(self, file_size):
        pass

    def upload_complete(self):
        logger = logging.getLogger('uploaddemo.upload_handlers.UploadProgressCachedHandler.upload_complete')
        if settings.DEBUG:
            logger.debug('Upload complete for %s' % self.cache_key)
        if self.cache_key:
            cache.delete(self.cache_key)      

