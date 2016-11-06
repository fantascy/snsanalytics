import logging
import datetime

from google.appengine.ext import db

import context, deploysns
from models import Campaign, Execution, CampaignPolySmall
from sns.camp import consts as camp_const
from sns.core import core as db_core
from sns.api.base import BaseProcessor
from sns.api import errors as api_error
from common.utils import datetimeparser
from sns.core.base import parseDatetime
from sns.core.core import get_user_id
from sns.serverutils import deferred, memcache
from sns.serverutils.event_const import _COMMAND_HANDLER_MAP, _EXECUTION_MAP

"""
Configure the size of a batch, so that total during of the batch process is less than 30 seconds 
"""
SCHEDULE_EXPEDITE_FACTOR = 'SCHEDULE_EXPEDITE_FACTOR'

"""
Retrieving text for url is time consuming. So we will cache the text of an URL in memcache for some duration.
"""
DEFAULT_URL_TEXT_CACHE_TIME = 600

def _deferredExecuteOneHandler(processorClass, ruleId):
    context.set_deferred_context(deploy=deploysns)
    return processorClass()._executeOneHandler(ruleId)


def _deferredDispatchEvent(execution):
    context.set_deferred_context(deploy=deploysns)
    try:
        logging.debug("Executing Campaigns:func _dispatch_event execution:%s" % execution)
        if not execution == None:
            rule = execution.campaign
            try:
                logging.debug("Executing Campaigns:func _dispatch_event")
                if rule == None or rule.deleted == True:
                    execution.state = camp_const.EXECUTION_STATE_FAILED
                    execution.put()
                    logging.info('The related rule has been deleted!')
                else:
                    handler = _COMMAND_HANDLER_MAP.get(rule.event)
                    if handler == None:
                        logging.info('no handler for this event: %s' %rule.event)
                    logging.debug("Executing Campaigns:execute")
                    handler().execute(execution=execution)
            except Exception, (err_msg) :
                rule.state = camp_const.CAMPAIGN_STATE_ERROR
                rule.put()
                logging.info('processing executions error : %s' %err_msg)
    except Exception, (err_msg) :
        logging.info('defering error : %s' %err_msg)
    return

class CampaignProcessor(BaseProcessor):
    def __init__(self, timeout=BaseProcessor.TIMEOUT_FRONTEND):
        BaseProcessor.__init__(self, timeout=timeout)
    
    def getModel(self):
        return Campaign
                
    def getSmallModel(self):
        return CampaignPolySmall
    
    def getExecutionModel(self, type):
        return _EXECUTION_MAP.get(type)
        
    def query_base(self,showSmall=False, **kwargs):
        if showSmall:
            model = self.getSmallModel()
        else:
            model = self.getModel()
        uid = kwargs.get('uid', get_user_id())
        q_base = model.all().filter('uid', uid).filter('deleted', False)
        return q_base
        
    def activate(self, params):
        """
        Activate the rule only, not trigger a posting action immediately.
        """
        rule = db_core.normalize_2_model(params)
        if rule.state == camp_const.CAMPAIGN_STATE_ACTIVATED :
            raise api_error.ApiError(api_error.API_ERROR_POSTING_RULE_OP_NOT_SUPPORTED_IN_STATE, 'activate', rule.name, rule.state)
        self._update_schedule_next(rule)
        rule.state = camp_const.CAMPAIGN_STATE_ACTIVATED
        rule.put()
        return rule
    
    def deactivate(self, params):
        """
        De-activate the rule. A rule can only be de-activated from active state.
        """
        rule = db_core.normalize_2_model(params)
        if rule.state != camp_const.CAMPAIGN_STATE_ACTIVATED :
            raise api_error.ApiError(api_error.API_ERROR_POSTING_RULE_OP_NOT_SUPPORTED_IN_STATE, 'deactivate', rule.name, rule.state)
        rule.state = camp_const.CAMPAIGN_STATE_INIT
        rule.put()
        logging.warn("Deactivated a feed campaign! %s" % rule.name)
        return rule

    def _update_schedule_next(self, rule):
        utcnow = datetime.datetime.utcnow()
        halfMinuteLater = utcnow + datetime.timedelta(seconds=0)
        if rule.scheduleNext is None or rule.scheduleNext<halfMinuteLater :
            rule.scheduleNext = halfMinuteLater
        if rule.scheduleStart is not None and rule.scheduleNext<rule.scheduleStart :
            rule.scheduleNext = rule.scheduleStart

    def _trans_create(self, params):
        """
        params - name, descr, keywords, channels, subchannels, contents, scheduleType, scheduleNext, scheduleStart, scheduleEnd, scheduleInterval
        """
        paramsCopy = params.copy()
        paramsCopy['uid'] = paramsCopy['parent'].uid
        paramsCopy = self._preprocess_create(paramsCopy)
        rule= BaseProcessor._trans_create(self, paramsCopy)
        self._update_schedule_next(rule)
        campSmall = self.getSmallModel()(name=rule.name, model=rule, uid=rule.uid, parent=rule.parent(), deleted=rule.deleted)
        campSmall.put()
        rule.smallModel = campSmall
        rule.put()
        return rule
        
    def _trans_update(self, params):
        paramsCopy = params.copy()
        paramsCopy = self._preprocess_update(paramsCopy)
        rule = BaseProcessor._trans_update(self, paramsCopy)
        self._update_schedule_next(rule)
        return rule
    
    def _preprocess_create(self, paramsCopy):
        if paramsCopy.has_key('scheduleType') :
            scheduleType = int(paramsCopy.get('scheduleType'))
        else :
            scheduleType = self.getDefaultScheduleType()
        
        utcnow = datetime.datetime.utcnow()
        if scheduleType in (camp_const.SCHEDULE_TYPE_ONE_TIME, camp_const.SCHEDULE_TYPE_RECURRING) :
            startTimeStr = paramsCopy.pop('scheduleStart', None)
            start = parseDatetime(startTimeStr, utcnow)
            if start is None or start < utcnow :
                start = utcnow 
            paramsCopy['scheduleStart'] = start
            paramsCopy['scheduleNext'] = start
        else :
            paramsCopy['scheduleNext'] = utcnow
        return paramsCopy

    
    def _preprocess_update(self, paramsCopy):
        """
        prepare some derived fields: scheduleNext
        """
        if paramsCopy.has_key('scheduleType') :
            scheduleType = int(paramsCopy.get('scheduleType'))
        else :
            scheduleType = self.getDefaultScheduleType()
        
        rule = self.get(paramsCopy)
        utcnow = datetime.datetime.utcnow()
        if scheduleType in (camp_const.SCHEDULE_TYPE_ONE_TIME, camp_const.SCHEDULE_TYPE_RECURRING) :
            startTimeStr = paramsCopy.pop('scheduleStart', None)
            start = parseDatetime(startTimeStr, utcnow)
            adjust = True
            if rule.scheduleStart is not None:
                oldStart = rule.scheduleStart
                oldStart = datetime.datetime(year=oldStart.year,month=oldStart.month,day=oldStart.day,hour=oldStart.hour,minute=oldStart.minute,second=oldStart.second)
                if oldStart == start:
                    adjust = False
            if adjust:
                if start is None or start < utcnow :
                    start = utcnow 
            paramsCopy['scheduleStart'] = start
        return paramsCopy
        
    def getDefaultScheduleType(self):
        return camp_const.SCHEDULE_TYPE_RECURRING     
            
    def cron_execute(self, params):
        return self.execute(params)

    
    def _re_execute(self, params):
        logging.debug("Re-execute suspend executions.")
        executions = Execution.all().filter('state >=', camp_const.EXECUTION_STATE_EXECUTING)
        exeCount = executions.count(1000)
        logging.debug("There are %s due suspend executions at this moment." % exeCount)
        deferredCount = 0
        for execution in executions:
            if self.isTimeout():
                return deferredCount
            
            if execution.state == camp_const.EXECUTION_STATE_EXECUTING: 
                if execution.modifiedTime > datetime.datetime.utcnow() - datetime.timedelta(minutes=5):
                    continue
            else :
                execution.state = camp_const.EXECUTION_STATE_EXECUTING
                execution.put()
            
            deferred.defer(_deferredDispatchEvent, execution)
            deferredCount += 1
        if deferredCount > 0 :
            logging.info("Kicked off deferred execution for %s executing campaigns." % deferredCount)
        return deferredCount

                                                      
    def execute(self, params):
        """
        Query all new active rules at the moment. If the rule is executing 
        """
        self._re_execute(params)
        utcnow = datetime.datetime.utcnow()
        ruleQuery = self.query_base().filter('state', camp_const.CAMPAIGN_STATE_ACTIVATED).filter('scheduleNext <= ', utcnow).order('scheduleNext')
        ruleCount = ruleQuery.count(1000)
        logging.debug("There are %s due active campaigns at this moment." % ruleCount)
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
        if deferredCount > 0 :
            logging.info("Kicked off deferred execution for %s active campaigns." % deferredCount)
        return deferredCount
    
    def _executeOneHandler(self, id):
        """
        Execute the one rule, keep deferring until it is fully finished execution.
        Return true if the rule is finished, else False (Timeout).
        """
        rule = None        
        try :
            rule=db.get(id)
            logging.debug('Current time start:%s'%datetime.datetime.utcnow())
            if self._execute(rule) :
                logging.debug("Finished processing rule '%s'." % (rule.name))
                logging.debug('Current time end:%s'%datetime.datetime.utcnow())
                return True
            else :
                logging.info("Campaign '%d' not finished!" % rule.name)
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
        rule.put()
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
        logging.debug("Executing campaign '%s' " % rule.name)
        executions = Execution.all().ancestor(rule).filter('state >=', camp_const.EXECUTION_STATE_EXECUTING)
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
            deferred.defer(_deferredDispatchEvent, execution)
                                               
    def _execute_method(self, immediate):
        """
        Sanity checks are already done. just go to perform the action.
        """
        rule = self._currentRule
        logging.debug("Do executing the giving rule: '%s' " % rule.name)
        executions = Execution.all().ancestor(rule).filter('state >=', camp_const.EXECUTION_STATE_EXECUTING)
        exeCount = executions.count(1000)
        if exeCount>0 :
            logging.info("There are %s due suspend executions at this moment." % exeCount)
        if exeCount == 0 :
            execution = self.getExecutionModel(rule.event)(parent=rule, campaign=rule, event=rule.event, state=camp_const.EXECUTION_STATE_INIT)
            execution.state = camp_const.EXECUTION_STATE_EXECUTING
            execution.put()
            logging.debug('Despatch campaign execution id: %s' % execution.id)
            deferred.defer(_deferredDispatchEvent, execution)        

                
class ExecutionProcessor(BaseProcessor):
    def getModel(self):
        return Execution
