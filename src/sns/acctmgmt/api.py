from sets import ImmutableSet
import datetime
import logging
import csv

from google.appengine.ext import db

from common.utils import string as str_util
import deploysns
import context
from sns.serverutils import deferred
from sns.core import core as db_core
from sns.core import base as db_base
from sns.api import consts as api_const
from sns.api import errors as api_error
from sns.api.base import BaseProcessor
from sns.log import consts as log_const
from sns.acctmgmt import consts as acctmgmt_const
from sns.acctmgmt import utils as acctmgmt_util
from sns.log.models import CmpTwitterAcctStats
from sns.acctmgmt.models import CmpAccount, YahooAccount, CmpTwitterPasswd


(PWD_FILE_COL_ID, PWD_FILE_COL_HANDLE, PWD_FILE_COL_PWD) = range(3)
(COL_EMAIL_SERVER, COL_EMAIL_PASSWD, COL_TWITTER_HANDLE, COL_TWITTER_PASSWD, COL_YAHOO_LOGIN, COL_YAHOO_PASSWD, COL_YAHOO_SECQA) = range(7)
    

class CmpAccountProcessor(BaseProcessor):
    def __init__(self):
        if not db_core.User.is_admin():
            raise api_error.ApiError(api_error.API_ERROR_ADMIN_OPERATION, "acctmgmt")
        BaseProcessor.__init__(self)

    def getModel(self):
        return CmpAccount

    @classmethod
    def supportedOperations(cls):
        return ImmutableSet([api_const.API_O_QUERY_ALL,
                             api_const.API_O_ADMIN,
                            ]).union(BaseProcessor.supportedOperations())
    
    def execute_admin(self, params):
        op = params.get('op', None)
        if op == 'lookup':
            return self.twitter_passwd_lookup(params)
        return BaseProcessor.execute_admin(self, params)

    def twitter_passwd_lookup(self, params):
        channel = params.get('twitter', None)
        if not channel: return "Please provide Twitter handle or ID using parameter 'twitter'!"
        logged_in_user_email = db_core.get_logged_in_user_email()
        if logged_in_user_email is None or logged_in_user_email in acctmgmt_const.SHARED_LOGGED_INS:
            return "This operation requires personal admin user privilege!"
        chid = None
        handle = None
        try:
            chid = int(channel)
            cstats = CmpTwitterAcctStats.get_by_chid(chid)
        except:
            handle = channel
            cstats = CmpTwitterAcctStats.get_by_name(handle)
        if cstats: 
            chid = cstats.chid
            handle = cstats.name
        if not chid: return "No information available for Twitter account %s!" % channel
        pwd_obj = CmpTwitterPasswd.get_by_chid(chid)
        pwd = pwd_obj.password if pwd_obj else None
        return chid, handle, pwd

    @classmethod
    def pwdupload(cls, data):
        header = csv.reader(data).next()
        if len(header) != 3:
            return "invalid file format" 
        deferred.defer(cls.deferred_pwdupload, data)
        return "succeeded" 
    
    @classmethod
    def deferred_pwdupload(cls, data):
        context.get_context().set_login_required(False)
        context.set_deferred_context(deploy=deploysns)
        line_number = 1
        total = 0
        new_count = 0
        updated_count = 0
        old_count = 0
        put_list = []
        try:
            rows = csv.reader(data)
            while True:
                row = rows.next()
                line_number += 1
                total += 1
                chid = int(row[PWD_FILE_COL_ID])
                handle = str_util.strip(row[PWD_FILE_COL_HANDLE])
                cstats = CmpTwitterAcctStats.get_by_chid(chid)
                if cstats:
                    if cstats.name != handle:
                        logging.warn("Twitter ID %d has different handles: %s in file vs %s in database." % (chid, handle, cstats.name))
                else:
                    logging.warn("Twitter account %d@%s is not an existing CMP account." % (chid, handle))
                pwd = str_util.strip(row[PWD_FILE_COL_PWD])
                pwd_obj = CmpTwitterPasswd.get_by_chid(chid)
                if pwd_obj:
                    if pwd_obj.password == pwd: 
                        old_count += 1
                        continue
                    pwd_obj.password = pwd
                    updated_count += 1
                else:
                    pwd_obj = CmpTwitterPasswd(key_name=str(chid), password=pwd)
                    new_count += 1
                put_list.append(pwd_obj)
        except StopIteration:
            db_base.put(put_list)
            logging.info("Password file upload succeeded! total=%d, new=%d, updated=%d, old=%d." % (total, new_count, updated_count, old_count))
        except:
            logging.exception("Error uploading password file at line #%d!" % line_number)
            
    @classmethod
    def upload(cls, data):
        header = csv.reader(data).next()
        if len(header) != 7:
            return "invalid file format" 
        deferred.defer(cls.deferred_upload, data)
        return "succeeded" 
    
    @classmethod
    def deferred_upload(cls, data):
        context.get_context().set_login_required(False)
        context.set_deferred_context(deploy=deploysns)
        old = dict([(obj.key().name(), obj) for obj in cls().execute_query_all()])
        new = set([])
        old_total = len(old)
        new_total = 0
        new_count = 0
        update_count = 0
        error_count = 0
        put_list = []
        try:
            rows = csv.reader(data)
            while True:
                row = rows.next()
                new_total += 1
                key_name = str_util.lower_strip(row[COL_TWITTER_HANDLE])
                if key_name in new:
                    logging.error("Acctmgmt: Upload error. Duplicated row for Twitter handle '%s'!" % row[COL_TWITTER_HANDLE])
                    error_count += 1
                    continue
                new.add(key_name)
                email_server = str_util.lower_strip(row[COL_EMAIL_SERVER])
                if email_server and email_server not in log_const.EMAIL_SERVERS:
                    logging.error("Acctmgmt: Upload error. email server '%s' is not valid." % email_server)
                    error_count += 1
                    continue
                obj = CmpAccount(key_name=key_name,
                            twitter_password = row[COL_TWITTER_PASSWD],
                            email_server = email_server,
                            email_password = row[COL_EMAIL_PASSWD],
                            old_email = str_util.lower_strip(row[COL_YAHOO_LOGIN]),
                            old_email_password = row[COL_YAHOO_PASSWD],
                            old_email_secqa = row[COL_YAHOO_SECQA])
                old_obj = old.get(key_name, None)
                if old_obj and old_obj == obj:
                    continue
                if old_obj:
                    update_count += 1
                else:
                    new_count += 1
                put_list.append(obj)
        except StopIteration:
            db_base.put(put_list)
            logging.info("Acctmgmt: Upload succeeded. error=%d, new=%d, updated=%d, old_total=%d, new_total=%d" % (error_count, new_count, update_count, old_total, new_total))
        except:
            logging.exception("Error uploading all CMP account file!")
            

class YahooProcessor(BaseProcessor):
    QUERY_LIMIT = 500
    def __init__(self):
        if not db_core.User.is_admin():
            raise api_error.ApiError(api_error.API_ERROR_ADMIN_OPERATION, "acctmgmt")
        BaseProcessor.__init__(self)

    def getModel(self):
        return YahooAccount

    def defaultOrderProperty(self):
        return "nameLower"  

    def isAddLimited(self):
        return False

    @classmethod
    def supportedOperations(cls):
        return ImmutableSet([api_const.API_O_QUERY_ALL]).union(BaseProcessor.supportedOperations())

    def query_base(self, **kwargs):
        q_base = self.getModel().all().filter('deleted', False)
        return q_base
    
    def query_by_cursor(self, params):
        utcnow = datetime.datetime.utcnow()
        limit = params.get('limit', self.QUERY_LIMIT)
        acctType = params.get('acctType')
        op = params.get('operation', acctmgmt_const.ACCT_MGMT_OP_LOGIN)
        stateProp = YahooAccount.state_property(acctType)
        state = params.get(stateProp, None)
        timeProp = YahooAccount.time_property(acctType, op)
        dayLimit = params.get('days', None)
        cutOffTime = None
        if dayLimit:
            dayLimit = int(dayLimit)
            cutOffTime = utcnow - datetime.timedelta(days=dayLimit)
        numRange = self._query_num_range(params)
        logging.info("AcctMgmt query filter: %s equals %s, %s older than %s days, num range in %s" % (stateProp, state, timeProp, dayLimit, numRange))
        query = self.query_base()
        cursor = params.get('cursor', None)
        if cursor:
            query.with_cursor(cursor)
        if state is not None:
            query.filter(stateProp + ' = ', state)
        if numRange:
            query = query.filter('num >= ', numRange[0]).filter('num <= ', numRange[1]).order('num')
        else:
            if cutOffTime:
                query = query.filter(timeProp + ' < ', cutOffTime).order(timeProp)
            else:
                query = query.order(timeProp)
        queryCount = query.count(100000)
        if queryCount==0:
            return {'cursor': None, 'objs': []}
        logging.info("AcctMgmt: query count is %d. " % queryCount)
        if numRange is not None and cutOffTime is not None:
            accts = []
            while True:
                timeFiltered = self._filter_by_time(query.fetch(limit=limit), timeProp, cutOffTime)
                if len(timeFiltered)==0:
                    break
                accts.extend(timeFiltered)
                if len(accts)>=limit:
                    break
                cursor = query.cursor()
                query.with_cursor(cursor)
        else:
            accts = query.fetch(limit=limit)
        cursor = query.cursor()
        return {'cursor': cursor, 'objs': accts}

    def _filter_by_time(self, accts, timeProp, cutOffTime):    
            timeFiltered = []
            for acct in accts:
                if getattr(acct, timeProp)<cutOffTime:
                    timeFiltered.append(acct)
            return timeFiltered

    def _query_num_range(self, params):
        param = params.get('num', None)
        if param:
            numRange = param.split('-')
            return (int(numRange[0]), int(numRange[1]))
        else:
            return None

    def create(self, params, errorOnExisting=True):
        if params.has_key('id'):
            return self.update(params)
        params['name'] = str_util.lower_strip(params['name'])
        keyName = YahooAccount.keyName(params['name'])
        params['key_name'] = keyName
        params['parent'] = None
        obj = YahooAccount.get_by_key_name(keyName, parent=None)
        if obj is not None:
            params['id'] = obj.id
            return self.update(params)
        self._create_update_massage(params)
        return BaseProcessor.create(self, params)

    def update(self, params):
        self._create_update_massage(params)
        return db.run_in_transaction(self._trans_update, params)

    def _trans_update_massage_post(self, obj, params):
        acctType = params.get('acctType', None)
        action = params.get('action', None)
        if acctType is not None and action is not None:
            if acctType==acctmgmt_const.ACCT_TYPE_YAHOO:
                self._trans_update_massage_post_yahoo(obj, action, params)
            elif acctType==acctmgmt_const.ACCT_TYPE_TWITTER:
                self._trans_update_massage_post_twitter(obj, action, params)
        
    def _trans_update_massage_post_yahoo(self, obj, action, params):
        obj.state = params['state']
        if action==acctmgmt_const.ACTION_YAHOO_LOGIN:
            obj.lastLoginTime = datetime.datetime.utcnow()
        elif action==acctmgmt_const.ACTION_YAHOO_CHANGE_PASSWORD_BEGIN:
            obj.newPassword = params['newPassword']
        elif action==acctmgmt_const.ACTION_YAHOO_CHANGE_PASSWORD_END:
            obj.lastLoginTime = datetime.datetime.utcnow()
            obj.lastPasswdChangeTime = datetime.datetime.utcnow()
            obj.oldPassword = obj.password
            obj.password = obj.newPassword
            obj.newPassword = None
        
    def _trans_update_massage_post_twitter(self, obj, action, params):
        obj.tState = params['tState']
        if action==acctmgmt_const.ACTION_TWITTER_LOGIN:
            obj.tLastLoginTime = datetime.datetime.utcnow()
        elif action==acctmgmt_const.ACTION_TWITTER_CHANGE_PASSWORD_BEGIN:
            obj.tNewPassword = params['tNewPassword']
        elif action==acctmgmt_const.ACTION_TWITTER_CHANGE_PASSWORD_END:
            obj.tLastLoginTime = datetime.datetime.utcnow()
            obj.tLastPasswdChangeTime = datetime.datetime.utcnow()
            obj.tOldPassword = obj.tPassword
            obj.tPassword = obj.tNewPassword
            obj.tNewPassword = None
        
    def _create_update_massage(self, params):
        if params.has_key('isCmp'):
            value = params['isCmp']
            try:
                if 'true'==str_util.lower_strip(str(value)):
                    params['isCmp'] = True
                else:  
                    params['isCmp'] = False
            except:
                params['isCmp'] = False
            
    def _massage_date(self, params, attr):
        if params.has_key(attr):
            value = params[attr]
            if isinstance(value, datetime.datetime):
                return
            if value is None:
                return
            time = acctmgmt_util.str_2_datetime(value)
            if time is None:
                params.pop(attr)
            else:
                params[attr] = time

    def delete(self, params):
        return BaseProcessor.delete(self, params)
    

def main():
    pass    

if __name__ == "__main__":
    main()
