import datetime
import logging
from sets import ImmutableSet

from google.appengine.ext import db

import context
from common.utils import string as str_util
from sns.serverutils import memcache, deferred
from sns.core.core import SystemStatusMonitor
from sns.api import consts as api_const
from sns.api.base import BaseProcessor
from sns.chan.models import HourlySendList, ChannelHourlyKeyName, ChannelDailyKeyName, DailySendStats, HourlySendStats
from sns.chan.models import TAccount
from sns.cont.api import MessageProcessor
from sns.cont.models import Topic
from sns.deal.api import DealBuilderProcessor
from sns.camp import consts as camp_const
from sns.camp.api import CampaignProcessor
from sns.dm import consts as dm_const
from sns.dm.models import DMCampaign, DMCampaignSmall, DMCampaignParent, BasicDMCampaign, AdvancedDMCampaign, AdvancedDMCampaignChild, get_target_list, get_source_account  


class DMCampaignProcessor(CampaignProcessor):
    @classmethod
    def supportedOperations(cls):
        return ImmutableSet([api_const.API_O_ACTIVATE, 
                           api_const.API_O_DEACTIVATE, 
                           api_const.API_O_EXECUTE, 
                           api_const.API_O_CRON_EXECUTE, 
                           ]).union(BaseProcessor.supportedOperations())
                           
    def __init__(self):
        self.executionApiCount = 0
                           
    def getModel(self):
        return DMCampaign
    
    def getSmallModel(self):
        return DMCampaignSmall
    
    def overExecutionApiLimit(self):
        return self.executionApiCount >= 10
    
    def create(self, params):
        rules = self.query_base().order('-number').fetch(limit=1)
        if len(rules) == 0:
            params['number'] = 0
        else:
            params['number'] = rules[0].number + 1
        batch = params['number']/dm_const.DM_RULE_PER_PATCH
        if params.has_key('uid'):
            parent = DMCampaignParent.get_or_insert_parent(batch,uid=params['uid'])
        else:
            parent = DMCampaignParent.get_or_insert_parent(batch)
        params['parent'] = parent
        params['userHashCode'] = parent.userHashCode
        rule = CampaignProcessor.create(self, params)
        self.activate(rule)
        return rule
    
    def cron_execute(self, params):
        monitor = SystemStatusMonitor.get_system_monitor(dm_const.DM_MONITOR_KEYNAME)
        if not monitor.work:
            logging.info('Stop dm cron : %s'%monitor.info)
            return monitor.info
        return self.execute(params)

    def execute(self, params):
        self._executeDM()
    
    def _executeDM(self):
        utcnow = datetime.datetime.utcnow()
        deferredCount = 0
        kickCount = 0
        ruleQuery = self.getModel().all().filter('deleted',False).filter('state', camp_const.CAMPAIGN_STATE_ACTIVATED).filter('scheduleNext < ', utcnow).order('scheduleNext')
        ruleCount = ruleQuery.count(1000)
        logging.info("Total due active DM rule count is %d at this moment." % ruleCount)
        if ruleCount==0 :
            return deferredCount
        activeRules = ruleQuery.fetch(10)
        for rule in activeRules :
            msg = " deferred execution for DM rule '%s'" % rule.name
            if deferredCount>=dm_const.MAX_EXECUTING_DM_RULE :
                logging.info("There are %s executing DM rules now, stop raising defer jobs." % deferredCount)
                break
            self._updateScheduleNext(rule)
            deferred.defer(self.__class__._deferred_execute_one_dm_campaign, ruleId=rule.id)
            logging.info("Kicked off %s" % msg)
            deferredCount += 1
            kickCount += 1
        logging.info("Kicked off deferred execution for %s active DM rules." % kickCount)
        return deferredCount
        
    def _updateScheduleNext(self, rule, minuteInterval=5):
        rule.scheduleNext = datetime.datetime.utcnow()+datetime.timedelta(minutes=minuteInterval)
        rule.put()

    def _executeOneHandler(self, ruleId):
        rule = None
        try :
            rule = db.get(ruleId)
            if self._executeOne(rule) :
                logging.info("Finished processing rule '%s', unlocked Twitter acct '%s'." % (rule.name, rule.sourceChannel.login()))
                return True
        except Exception,ex:
            ex = str(ex).decode('utf-8','ignore')
            if rule is None :
                logging.exception("Could not resolve the DM rule id '%s' in _executeOneHandler()." % (ruleId,))
                return False
            logging.exception("Most likely timeout, but it could be other exception, when processing rule '%s', unlocked Twitter acct '%s'." % (rule.name, rule.sourceChannel.login()))
            if ex.find('Basic authentication is not supported') != -1 or ex.find('Could not authenticate with OAuth') != -1 :
                monitor = SystemStatusMonitor.get_system_monitor(dm_const.DM_MONITOR_KEYNAME)
                monitor.work = False
                monitor.info = "Channel %s is suspend!" % rule.sourceChannel.login()
                monitor.put()
                memcache.delete(dm_const.DM_MONITOR_KEYNAME)
            if ex.find('Got return status:') != -1:
                rule.state = camp_const.CAMPAIGN_STATE_ACTIVATED
                rule.scheduleNext = max(rule.scheduleNext + datetime.timedelta(hours=1), datetime.datetime.utcnow())
                rule.put()
        return False
                        
    def _executeOne(self, rule):
        """
        Execute the one rule.
        Return true if the rule is finished, else False (Timeout).
        """
        if rule.finished() :
            return True
        return self._sendDM(rule)
    
    def _sendDM(self, rule):
        utcnow = datetime.datetime.utcnow()
        if rule.promoteType is not None:
            rule.contents = []
            if rule.promoteType == dm_const.PROMOTE_TYPE_DEAL:
                for cid in AdvancedDMCampaignProcessor.get_deal_contents(rule):
                    rule.contents.append(db.Key(cid))
            elif rule.promoteType == dm_const.PROMOTE_TYPE_ACCOUNT:
                for cid in AdvancedDMCampaignProcessor.get_account_contents(rule):
                    rule.contents.append(db.Key(cid))
            logging.info('Get %s deals for rule %s'%(len(rule.contents),rule.name))
        tapi = rule.getTwitterApi()
        chid = rule.sourceChannel.keyNameStrip()
        parent = get_source_account(chid)
        text = rule.getMsg()
        if text is None:
            logging.warning('Cant find msg for rule %s,return'%rule.name)
            return True
        hourlyKeyName = ChannelHourlyKeyName.keyName(chid, utcnow)
        dailyKeyName = ChannelDailyKeyName.keyName(chid, utcnow)
        hourlySendList = HourlySendList.get_or_insert(hourlyKeyName, parent=parent, username=chid)
        hourlySendStats = HourlySendStats.get_or_insert(hourlyKeyName,parent=parent,username=chid)
        dailySendStats = DailySendStats.get_or_insert(dailyKeyName,parent=parent,username=chid)
                
        while not rule.finished() :
            targetList = get_target_list(rule)
            if self.overExecutionApiLimit():
                break
            if self.isTimeout(timeout=5) :
                break
            if hourlySendList.overSendLimit or rule.exceedMaxHourlySend(hourlySendStats.sendCount+hourlySendStats.failCount) :
                break
            if len(targetList.ids)==0 :
                succeeded,targetList = rule.loadNextTargetPage(targetList)
                if not succeeded :
                    logging.warning("Failed loading follower list for DM, try again next hour.")
                    break
                if len(targetList.ids)==0 :
                    logging.info("No more followers to DM!")
                    break
            logging.info("Remaining followers count: %s" % len(targetList.ids))
            newTargets = []
            failCount = 0
            while len(targetList.ids)>0 :
                if self.overExecutionApiLimit():
                    logging.info("DM rule is over execution limit of 10.")
                    break
                if rule.exceedMaxHourlySend(hourlySendStats.sendCount+hourlySendStats.failCount+len(newTargets)) :
                    break
                if self.isTimeout(timeout=5) :
                    break
                user_id = targetList.ids[0]
                targetList.ids = targetList.ids[1:]
                try:
                    self.executionApiCount += 1
                    if not context.is_dev_mode():
                        tapi.direct_messages.new(user_id=user_id,text=text)
                    newTargets.append(user_id)
                    logging.info("'%s' sent direct message to %s succeeded: '%s'." % (tapi.username, user_id, text))
                except Exception,ex:
                    failCount += 1
                    ex = str(ex)
                    if ex.find("you can only send so many direct messages per day") != -1:
                        logging.warning("'%s' cannot send more direct messages. Will try again next hour." % tapi.username)
                        hourlySendList.overSendLimit = True
                        hourlySendList.put()
                        break;
                    elif ex.find('ApplicationError') != -1:
                        logging.error('%s when sending direct message.' % ex)
                    elif ex.find('You cannot send messages to users who are not following you') != -1:
                        logging.warning('%s when sending direct message.' % ex)
                    else:
                        hourlySendList.overSendLimit = True
                        hourlySendList.put()
                        logging.error("Error when processing DM rule '%s': '%s' sending direct message to %s: %s" % (rule.name, tapi.username, text, str(ex)))
                        break
                    continue
            update_msg = "'%s' DM execution stats: %s successfully and %s failed." % (tapi.username, len(newTargets), failCount)
            updated_objs = []
            updated_objs.append(targetList)
            if len(newTargets) > 0:
                rule.totalSendCount += len(newTargets)
                if rule.advancedCampaign is not None:
                    adRule = db.get(rule.advancedCampaign)
                    adRule.totalSendCount += len(newTargets)
                    adRule.put()
                if rule.runTurn >= len(rule.sendTurn):
                    rule.sendTurn.append(0)
                rule.sendTurn[rule.runTurn] += len(newTargets)
                hourlySendList.addFriends(newTargets)
            dailySendStats.sendCount += len(newTargets)
            hourlySendStats.sendCount += len(newTargets)
            hourlySendStats.failCount += failCount
            rule.totalFailCount += failCount
            updated_objs.append(hourlySendList)
            updated_objs.append(dailySendStats)
            updated_objs.append(hourlySendStats)
            if len(updated_objs)>0 :
                db.put(updated_objs)
                logging.info("DB save succeeded: %s" % update_msg)
        if hourlySendList.overSendLimit or rule.exceedMaxHourlySend(hourlySendStats.sendCount+hourlySendStats.failCount) :
            logging.info("DM rule %s exceeds hourly limit, will run again next hour." % rule.name)
            totalTime = datetime.datetime.utcnow() - rule.scheduleStart
            interval = 3600
            totalTime = totalTime.days* 24*3600 + totalTime.seconds
            t = totalTime/interval
            rule.scheduleNext = rule.scheduleStart + (t+1)*datetime.timedelta(seconds=interval) 
        rule.syncState()
        rule.put()
        """ End of outer while loop """
        return True

    @classmethod
    def _deferred_execute_one_dm_campaign(cls, ruleId):
        return cls()._executeOneHandler(ruleId)
                

class BasicDMCampaignProcessor(DMCampaignProcessor):
    def getModel(self):
        return BasicDMCampaign
            

class AdvancedDMCampaignChildProcessor(DMCampaignProcessor):
    def getModel(self):
        return AdvancedDMCampaignChild
            

class AdvancedDMCampaignProcessor(DMCampaignProcessor):
    def getModel(self):
        return AdvancedDMCampaign
            
    def _updateScheduleNext(self, rule, minuteInterval=5):
        DMCampaignProcessor._updateScheduleNext(self, rule, minuteInterval=60)

    def _executeOneHandler(self, ruleId):
        logging.info("Finished updating deals for Advanced DM rule ")
        
    @classmethod
    def get_account_contents(cls, rule):
        contents = []
        if rule.accountPromoteType == dm_const.ACCOUNT_PROMOTE_TYPE_CITY_CATEGORY:
            for topic in rule.topics:
                for location in rule.locations: 
                    handle = cls.get_account_handle(location, topic)
                    if handle is None:
                        continue
                    memKey = topic+":"+location+':'+handle
                    msg = memcache.get(memKey)
                    if msg is None:
                        title = "To see all of the daily deals, group buying deals and special discounts on {{City Category}} in {{City Name}}, follow @{{Handle}}"%(Topic.get_by_topic_key(topic).name,Topic.get_by_topic_key(location).name,handle)
                        msg = MessageProcessor().create({'msg':title,'msgShort80':str_util.slice_double_byte_character_set(title,80)})
                        memcache.set(memKey, msg)
                    contents.append(msg.id)
        elif rule.accountPromoteType == dm_const.ACCOUNT_PROMOTE_TYPE_CITY:
            for location in rule.locations:
                handle = cls.get_account_handle(location)
                if handle is None:
                    continue
                memKey = location+":"+handle
                msg = memcache.get(memKey)
                if msg is None:
                    title = "To see all of the daily deals, group buying deals and special discounts in the great city of %s, please follow @%s"%(Topic.get_by_topic_key(location).name,handle)
                    msg = MessageProcessor().create({'msg':title,'msgShort80':str_util.slice_double_byte_character_set(title,80)})
                    memcache.set(memKey, msg)
                contents.append(msg.id)
        return contents
        
        
    @classmethod
    def get_account_handle(cls, location,category=None):
        if category is None:
            accounts = TAccount.all().filter('topics', location).fetch(limit=100)
            mainAccount = None
            for account in accounts:
                if len(account.topics) == 1:
                    mainAccount = account
            return mainAccount
        else:
            accounts = TAccount.all().filter('topics', location).filter('topics', category).fetch(limit=1)
            if len(accounts) > 0:
                return accounts[0]
            else:
                return None
        
    @classmethod
    def get_deal_contents(cls, rule):
        topics = rule.topics
        locations = rule.locations
        memKey = "|".join(topics)+":"+"|".join(locations)
        contents = memcache.get(memKey)
        if contents is None:
            contents = []
            if len(topics) == 0:
                for location in locations:
                    deal = DealBuilderProcessor().getTopDeal(location=location, category=None)
                    if deal is None :
                        continue
                    contents.append(cls.get_deal_msg(deal).id)
            elif len(locations) == 0:
                for category in topics:
                    deal = DealBuilderProcessor().getTopDeal(location=None, category=category)
                    if deal is None :
                        continue
                    contents.append(cls.get_deal_msg(deal).id)
            else:
                for category in topics:
                    for location in locations:
                        deal = DealBuilderProcessor().getTopDeal(location, category)
                        if deal is None :
                            continue
                        contents.append(cls.get_deal_msg(deal).id)
            memcache.set(memKey, contents, time=3600)
        logging.info('Find %d deals'%len(contents))
        return contents
    
    @classmethod
    def get_deal_msg(cls, deal):
        title = deal.title
        url = deal.keyNameStrip()
        p = {}
        p['msg'] = title
        p['msgShort80'] = str_util.slice_double_byte_character_set(title,80)
        p['url'] = url
        msg = MessageProcessor().create(p)
        return msg
            
    @classmethod
    def _deferred_sync_dm_campaigns(cls, rid):
        rule = db.get(rid)
        topics = rule.topics + rule.locations
        contents = cls.get_deal_contents(rule)
        allAccounts = set([])
        for topic in topics:
            allTopics = Topic.all().filter('ancestorTopics', topic).fetch(limit=100) + [Topic.get_by_topic_key(topic)]
            for child in allTopics:
                if child is not None:
                    channels = TAccount.all().filter('topics', child.keyNameStrip()).fetch(limit=10)
                    allAccounts.update(channels)
        logging.info("Find total %s matched channels for Advanced DM rule '%s'." % (len(allAccounts), rule.name))
        for account in allAccounts:   
            attrs = {}
            for key in rule.properties().keys():
                attrs[key] = getattr(rule,key)
            attrs.pop('search_index')
            attrs.pop('state')
            attrs.pop('scheduleNext')
            attrs['sourceChannel'] = account.id
            attrs['advancedCampaign'] = rule.id
            attrs['name'] = attrs['name'] + ' : ' + account.name
            attrs['uid'] = account.parent().uid
            attrs['contents'] = contents
            if account.advancedDMCampaign is None or db.get(account.advancedDMCampaign).deleted==True:
                DMCampaignProcessor().create(attrs)
                account.advancedDMCampaign = rule.id
                account.put()
                logging.info('Create DM rule for channel %s'%account.name)
            elif account.advancedDMCampaign == rule.id:
                dmRules = BasicDMCampaignProcessor().getModel().all().filter('sourceChannel', account).filter('advancedCampaign', rule.id).filter('deleted', False).fetch(limit=1)
                if len(dmRules) > 0:
                    attrs.pop('sourceChannel')
                    attrs.pop('name')
                    attrs.pop('nameLower')
                    attrs.pop('contents')
                    attrs.pop('number')
                    attrs['id'] = dmRules[0].id
                    DMCampaignProcessor().update(attrs)
                    logging.info('Update DM rule for channel %s'%account.name)
                else:
                    DMCampaignProcessor().create(attrs)
                    logging.info('Create DM rule for channel %s'%account.name)
            else:
                logging.info('Already own DM rule for channel %s'%account.name)
