import unittest
import codecs
import json

from client import conf, apiclient


class RefreshTest(unittest.TestCase):
    """
    to import large file to the server, you must do 4 steps below:
    
    1.create a mail list, just like maillist:'Test Large CSV Import List 1'
    
    2.click the button 'view contact list' and then get the mail list id from the url
    
    3.copy the id in the url and repalce the value of key 'id' in pars below
    
    4.replace the csv file path below
    
    5.just run
    
    
    Random Line Upload:
        param:
        start: the start line num
        end:   the end line num, -1 means the end of the file
    
    """
        
    def testUploadEmailContact(self):
        section = 100
        contacts = []
        
        
        jump = 0
        start = 0
        end = -1
        
        create_counte = 0
        update_counte = 0
        error_counte = 0
        
        header_row = None
        for row in file.readlines():
            """ remove the last character '\n' """
            row = row[:-1] 
            if row[:3] == codecs.BOM_UTF8:
                row = row[3:]
            row = row.split(',')
            if row==None or row==['']:
                continue
            if not header_row:
                
                header_row = row
                print '%s' %header_row
                try:
                    self.index_email = header_row.index('email')
                    self.index_fullName  = header_row.index('fullName')
                except Exception, (err_msg) :
                    print "header data error%s" %err_msg
                    return
                
                try:
                    self.index_firstName = header_row.index('firstName')
                    self.index_lastName  = header_row.index('lastName')
                except:
                    pass
                
                continue
            jump += 1
            if jump > start and ((end >= 0 and jump < end) or end < 0):
                email = row[self.index_email]
                firstName = row[self.index_firstName] if self.index_firstName != None else ''
                lastName  = row[self.index_lastName]  if self.index_lastName  != None else ''
                fullName  = row[self.index_fullName]
                
                #here to replce the id param
                contacts.append(dict(email=email,firstName=firstName,lastName=lastName,fullName=fullName))
                
                if len(contacts) >= section:
                    pars = dict(id='agZzbnMtMDJyNgsSB2RiX3VzZXIiFnVzZXI6cWEwNy5zYUBnbWFpbC5jb20MCxINbWFpbF9tYWlsbGlzdBgEDA',contacts=contacts)
                    
                    try:
                        list_json = apiclient.call_api(apiclient.server_api_domain(), 'mail/contact', 'import_obj', pars)
                        result=json.loads(list_json)
                        if not result == None:
                            create_counte += result.get('create', 0)
                            update_counte += result.get('update', 0)
                            
                        contacts = []
                    except Exception, (err_msg) :
                        print 'import data error --------->%s' %err_msg
                        error_counte += section
                        
                    print 'the counter is --------->create: %s update: %s error: %s' %(create_counte, update_counte, error_counte)
                    
                """
                pars = {'id':'agZzYS1xYTlyNgsSB2RiX3VzZXIiFnVzZXI6cWEwNy5zYUBnbWFpbC5jb20MCxINbWFpbF9tYWlsbGlzdBgeDA','email':email,'firstName':firstName,'lastName':lastName,'fullName':fullName}
                try:
                    list_json = client.call_api(apiclient.server_api_domain(), 'mail/contact', 'import_obj', pars)
                    result=json.loads(list_json)
                    if result == 'create':
                        create_counte += 1
                    elif result == 'update':
                        update_counte += 1
                    else:
                        error_counte += 1
                    print 'import mail contact --------->%s %s %s %s' %(email, firstName, lastName, fullName)
                except Exception, (err_msg) :
                    print 'import data error --------->%s' %err_msg
                    error_counte += 1
                    
                print 'the counter is --------->create: %s update: %s error: %s' %(create_counte, update_counte, error_counte)
                """
        #pars = {'list':'','csv':csv}
        #client.call_api(apiclient.server_api_domain(), 'mail', 'import', pars)
        
        
if __name__ == "__main__":
    apiclient.login(apiclient.server_domain(), conf.ADMIN_USER, conf.ADMIN_PASSWD, conf.APPLICATION_ID, conf.IS_DEV_SERVER, True)
    unittest.main()