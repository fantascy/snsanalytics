from sets import ImmutableSet
import logging

from google.appengine.ext import db
from google.appengine.api import users
from twitter.api import TwitterApi
from twitter.oauth import TwitterOAuthAccessToken

from sns.core.core import ChannelParent
from sns.core.base import  parseBool
from sns.api.base import BaseProcessor
from sns.api import base as api_base
from sns.api import errors as api_error
from sns.api import consts as api_const
from sns.usr.api import UserProcessor
from sns.chan import consts as channel_const
from sns.chan.models import TAccount, FAccount, FAdminPage, ChannelClickCounter


class TAccountProcessor(BaseProcessor):
    def getModel(self):
        return TAccount

    def query_base(self, **kwargs):
        q_base = self.getModel().all().ancestor(ChannelParent.get_or_insert_parent()).filter('deleted', False)
        return q_base
    
    def create(self, params, errorOnExisting=True):
        if self.isAddLimited():
            raise api_error.ApiError(api_error.API_ERROR_USER_EXCEED_ADD_LIMIT, UserProcessor().getChannelAddLimit(), 'Twitter account')            
        paramsCopy = params.copy()
        if not paramsCopy.has_key('name') :
            paramsCopy['name'] = paramsCopy['login']
        if not paramsCopy.has_key("avatarUrl") :
            oauthAccessToken = paramsCopy.get("oauthAccessToken", None)
            avatarUrl = TwitterApi(oauth_access_token=oauthAccessToken).account.verify_credentials()["profile_image_url"]
            paramsCopy['avatarUrl'] = avatarUrl
    
        errorOnExisting = paramsCopy.pop('errorOnExisting', errorOnExisting)
        errorOnExisting = parseBool(errorOnExisting)
        key_name = TAccount.keyName(paramsCopy['chid'])
        channel = TAccount.get_by_key_name(key_name, ChannelParent.get_or_insert_parent())
        if channel:
            if channel.deleted :
                channel.deleted=False
                channel.name=paramsCopy["name"]
                channel.state = channel_const.CHANNEL_STATE_NORMAL
                channel.oauthAccessToken=paramsCopy.get("oauthAccessToken", None)
                channel.avatarUrl=paramsCopy.get("avatarUrl", channel_const.DEFAULT_TWITTER_AVATAR_URL)
                db.put(channel)
                return channel
            else:
                if errorOnExisting :
                    raise api_error.ApiError(api_error.API_ERROR_DATA_UNIQUENESS, 'Channel', 'login', params['login'])
                else :
                    return channel                
        paramsCopy['key_name'] = key_name
        return BaseProcessor.create(self, paramsCopy)
            
    def _trans_create(self, params):
        params['userEmail'] = users.get_current_user().email()
        channel = api_base.createModelObject(self.getModel(), params)
        db.put(channel)
        return channel

    def defaultOrderProperty(self):
        return "nameLower"  

    def isAddLimited(self):
        return False

    def sync(self, params):
        channel = None
        try:
            updated = False
            channel=self.get(params)
            tapi = channel.get_twitter_api()
            twitterInfo = tapi.account.verify_credentials()
            if channel.avatarUrl!=twitterInfo["profile_image_url"]:
                channel.avatarUrl=twitterInfo["profile_image_url"]
                updated = True 
            if channel.name!=twitterInfo['screen_name']:
                channel.name = twitterInfo['screen_name']
                channel.nameLower = channel.name.lower()
                updated = True 
            if channel.state==channel_const.CHANNEL_STATE_SUSPENDED:
                channel.state = channel_const.CHANNEL_STATE_NORMAL
                updated = True
            if updated:
                channel.put()
                logging.info("Updated profile for channel '%s'." % channel.name)
                return channel, True
            else:
                return channel, False
        except Exception, ex:
            if channel:
                logging.warn("Twitter acct %s sync error! %s" % (channel.chid_handle_str(), str(ex)))
            else:
                logging.exception("Error when updating channel profile:")
        return None, False

    def execute_admin(self, params):
        op = params.pop('op', None)
        if op:
            if op=='fix_suspended_time':
                return self._fix_suspended_time()
            elif op=='sync_state':
                return self._sync_state(params)
            elif op=='retrieve_followers':
                return self._retrieve_followers(params)
            elif op=='mark_deleted':
                return self._mark_deleted(params)
        return BaseProcessor.execute_admin(self, params)
    
    def _fix_suspended_time(self):
        query = TAccount.all().filter('state = ', channel_const.CHANNEL_STATE_SUSPENDED).order('-suspendedTime')
        suspended = query.fetch(limit=200)
        re_suspended = []
        for channel in suspended:
            if channel.isRestored:
                channel.suspendedTime = channel.modifiedTime
                re_suspended.append(channel)
        db.put(re_suspended)
        return re_suspended
        
    def _sync_state(self, params):
        obj = self.query(params)[0]
        return obj.syncState()

    def _retrieve_followers(self, params):
        chid = int(params['chid'])
        target_user_id = int(params['user_id'])
        cursor = int(params.get('cursor', -1))
        channels = TAccount.all().filter('chid', str(chid)).fetch(limit=10)
        channels = filter(lambda x: x.deleted == False, channels)
        if not channels: return "No channel found for chid %s!" % chid
        channel = channels[0]
        tapi = channel.get_twitter_api()
        response = tapi.followers.ids(user_id=target_user_id, cursor=cursor)
        resp_msg = "chid=%s; user_id=%s; previous_cursor=%s; next_cursor=%s; count=%s" % (
                    chid, target_user_id, 
                    response['previous_cursor'], 
                    response['next_cursor'], 
                    len(response['ids']))
        logging.info(resp_msg)
        return response

    def _mark_deleted(self, params):
        chid = int(params['chid'])
        channels = TAccount.all().filter('chid', str(chid)).fetch(limit=100)
        total_count = len(channels)
        channels = filter(lambda x: x.deleted == False, channels)
        delete_count = len(channels)
        for channel in channels:
            channel.deleted = True
        db.put(channels)
        return "Deleted %d out of total %d channel objects for chid %s!" % (delete_count, total_count, chid)

    def query_cmp_channels(self, params):
        if not params.has_key('query_all'):
            params['query_all'] = True
        if not params.has_key('deleted'):
            params['deleted'] = False
        params['isContent'] = True
        return self.query_by_cursor(params)

        
class FAccountProcessor(BaseProcessor):
    def getModel(self):
        return FAccount
  
    @classmethod
    def supportedOperations(cls):
        """"
        Supported public API operations of this processor
        """
        return ImmutableSet([api_const.API_O_QUERY_ALL]).union(BaseProcessor.supportedOperations())

    def create(self, params, errorOnExisting=True):
        paramsCopy = params.copy()
        key_name = FAccount.keyName(paramsCopy['chid'])
        fchannel = FAccount.get_by_key_name(key_name, ChannelParent.get_or_insert_parent())
        if fchannel is not None:
            if fchannel.deleted:
                fchannel.deleted = False
                fchannel.state = channel_const.CHANNEL_STATE_NORMAL
                fchannel.oauthAccessToken = paramsCopy['oauthAccessToken']
                db.put(fchannel)
            return fchannel
        paramsCopy['key_name'] = key_name
        return BaseProcessor.create(self, paramsCopy)

    def _trans_create(self, params):
        fchannel = api_base.createModelObject(self.getModel(), params)
        db.put(fchannel)
        return fchannel
    
    def query_base(self, **kwargs):
        q_base = self.getModel().all().ancestor(ChannelParent.get_or_insert_parent()).filter('deleted', False)
        return q_base
    

class TwitterOAuthTokenProcessor(BaseProcessor):
    def getModel(self):
        return TwitterOAuthAccessToken


class FAdminPageProcessor(BaseProcessor):
    def getModel(self):
        return FAdminPage

    def create(self, params, errorOnExisting=True):
        paramsCopy = params.copy()
        key_name = FAdminPage.keyName(paramsCopy['pageid'])
        pchannel = FAdminPage.get_by_key_name(key_name, ChannelParent.get_or_insert_parent())
        if pchannel is not None:
            if pchannel.deleted:
                pchannel.deleted = False
                pchannel.state = channel_const.CHANNEL_STATE_NORMAL
                pchannel.name = paramsCopy['name']
                if paramsCopy.has_key('oauthAccessToken'):
                    pchannel.oauthAccessToken = paramsCopy['oauthAccessToken']
                    db.put(pchannel)
            return pchannel
        paramsCopy['key_name'] = key_name
        return BaseProcessor.create(self, paramsCopy)

    def _trans_create(self, params):
        #api_base.addLowerProperty(params)
        pchannel = api_base.createModelObject(self.getModel(), params)
        db.put(pchannel)
        return pchannel

    def query_base(self, **kwargs):
        q_base = self.getModel().all().ancestor(ChannelParent.get_or_insert_parent()).filter('deleted', False)
        return q_base

  
class ChannelClickCounterProcessor(BaseProcessor):
    def getModel(self):
        return ChannelClickCounter


def main():
    pass    

if __name__ == "__main__":
    main()
