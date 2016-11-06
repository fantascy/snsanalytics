"""
Base test case classes for API test cases
"""
import unittest

import datetime

import json

from sns.api import consts as api_const
from sns.api import errors as api_error

from client import apiclient
from client.base import api as api_cbase
import testdata


class ApiTest(api_cbase.ApiBase, unittest.TestCase):
    def createWithUniqueNameSuffix(self):
        return True
    
    def activate(self, params=None, format='json'):
        serv_resp_body = self.call('activate', params, format)
#        print 'activate api output started'
#        print serv_resp_body
#        result = json.loads(serv_resp_body)
#        self.assertTrue(type(result)==dict)
#        return result

    def deactivate(self, params=None, format='json'):
        serv_resp_body = self.call('deactivate', params, format)
        result = json.loads(serv_resp_body)
        self.assertTrue(type(result)==dict)
        return result

    def _replaceNamesWithIds(self, dic, key, unique_suffix=None):
        names = dic[key]
        ids = []
        for name in names :
            obj = testdata.getObject(name)
            if unique_suffix == None :
                self._setUniqueName(obj)
            else :
                self._setUniqueName(obj, unique_suffix)

            objId = self.create(obj)['id']
            ids.append(objId)
        dic[key] = ids

    def _setUniqueName(self, objDict, unique_suffix=None):
        if unique_suffix == None :
            objDict['name'] = objDict['name'] + ' ' + unicode(datetime.datetime.utcnow())
        else :
            objDict['name'] = objDict['name'] + ' ' + unique_suffix
        return objDict
        
    def testCreate(self, format='json', obj=None):
        if self.getModule() is None : return
        if obj is None :
            obj = testdata.getObject(self.getModule())
        if self.createWithUniqueNameSuffix() :
            unique_suffix = str(datetime.datetime.utcnow())
            self._setUniqueName(obj, unique_suffix)
        return self.create(self.getModule(), obj, format=format)

    def testCreateReqPlain(self):
        if self.getModule() is None : return
        self.testCreate('plain')

    def testCreates(self):
        if self.getModule() is None : return
        objs = testdata.getObjects(self.getModule())
        for obj in objs :
            self.testCreate(obj=obj)

    def testGet(self):
        if self.getModule() is None : return
        id = self.testCreate()['id']
        self.get(self.getModule(), {'id':id})

    def testUpdate(self):
        if self.getModule() is None : return
        id = self.testCreate()['id']
        self.update(self.getModule(), {'id':id, 'descr':'updated ' + str(datetime.datetime.utcnow())})

    def testDelete(self):
        if self.getModule() is None : return
        id = self.testCreate()['id']
        self.delete(self.getModule(), {'id':id})



class UserApiTest(unittest.TestCase):
    def getModule(self):
        return api_const.API_M_USER
    


class PostApiTest(ApiTest):
    def getModule(self):
        return api_const.API_M_POSTING_POST
    

class PostingCampaignApiTest(ApiTest):
    def getContentModule(self):
        pass
    
    def testCreate(self, format='json', obj=None):
        if self.getModule() is None : return
        if obj is None :
            obj = testdata.getObject(self.getModule())
        unique_suffix = str(datetime.datetime.utcnow())
        self._setUniqueName(obj, unique_suffix)
        self._replaceNamesWithIds(obj, 'contents', self.getContentModule(), unique_suffix)
        self._replaceNamesWithIds(obj, 'channels', api_const.API_M_CHANNEL, unique_suffix)
        return self.create(self.getModule(), obj, format=format)

    def testActivate(self, name=None):
        if self.getModule() is None : return
        obj = testdata.getObject(self.getModule(), name)
        id = self.testCreate(obj=obj)['id']
        self.activate(self.getModule(), {'id':id})

    def testActivates(self):
        if self.getModule() is None : return
        for rule in testdata.getObjects(self.getModule()) :
            self.testActivate(rule['name'])            

    def testDeactivate(self, name=None):
        if self.getModule() is None : return
        obj = testdata.getObject(self.getModule(), name)
        id = self.testCreate(obj=obj)['id']
        self.activate(self.getModule(), {'id':id})
        self.deactivate(self.getModule(), {'id':id})

    def batch10Activates(self):
        for i in range(1,10) :
            self.testActivates()

    def batch100Activates(self):
        for i in range(1,100) :
            self.testActivates()

    def _batchOperation(self, batch_op, params=None):
        module = self.getModule()
        if module is None :
            module = api_const.API_M_POSTING_RULE
        resp_body = self._callApi(module, batch_op, params)
        if apiclient.IS_ADMIN :
            try :
                if batch_op=='batch_post' and module==api_const.API_M_POSTING_RULE :
                    result = json.loads(resp_body)
                    self.assertTrue(type(result)==dict and result.has_key('error_code') and result['error_code']==api_error.API_ERROR_UNSUPPORTED_OPERATION)
                    return
                count = int(resp_body)
            except :
                self.fail("Operation '%s' should return an integer" % batch_op)
        else :
            result = json.loads(resp_body)
            self.assertTrue(type(result)==dict and result.has_key('error_code') and result['error_code']==api_error.API_ERROR_ADMIN_OPERATION)

    def expedite(self):
        self._batchOperation('expedite')
    
