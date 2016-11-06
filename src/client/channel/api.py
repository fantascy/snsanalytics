import logging
import random

from twitter.api import TwitterApi

from sns.api import consts as api_const
from sns.chan import consts as channel_const
from client import apiclient
from client.base.api import ApiBase


class TwitterOAuthToken():
    def __init__(self, **oauth_token):
        self.handle = oauth_token['handle']
        self.oauth_token = oauth_token['oauth_token']
        self.oauth_token_secret = oauth_token['oauth_token_secret']
        self.key_name = oauth_token['key_name']
        
    @property
    def chid(self):
        return int(self.key_name.split(':')[-1])
    
    def user_str(self):
        try:
            return "%s@%s" % (self.key_name, self.handle)
        except:
            return "%s" % self.handle
        
    def __str__(self):
        return "%s oauth_token:%s, oauth_token_secret: %s" % (self.user_str(), self.oauth_token, self.oauth_token_secret)


class TwitterOAuthTokenApi(ApiBase):
    API_MODULE = api_const.API_M_TWITTER_OAUTH_TOKEN

    def get_by_chid(self, chid):
        params = dict(key_name="sns:%s" % chid)
        return self.get(params)

class TAccountApi(ApiBase):
    API_MODULE = api_const.API_M_CHANNEL
    
    @property        
    def chid(self):
        return int(self.obj['chid'])
    
    @classmethod
    def retrieve_followers(cls, chid, user_id, cursor=None):
        chid = int(chid)
        user_id = int(user_id)
        cursor = -1 if cursor is None else int(cursor)
        return cls.transform_obj(cls().admin(params=dict(op='retrieve_followers', chid=chid, user_id=user_id, cursor=cursor)))


class TAccountStatsApi(ApiBase):
    API_MODULE = api_const.API_M_LOG_CMP_TWITTER_STATS

    def __init__(self, obj=None):
        ApiBase.__init__(self, obj)
        self._tapi = None
    
    def chid_handle_str(self):
        return "%s@%s" % (self.key_name, self.name)

    @property
    def chid(self):
        return int(self.key_name)
    
    @property
    def name(self):
        return self.obj['name']
    
    @property
    def search_term(self):
        return self.obj['searchTerm']
    
    @property
    def tapi(self):
        if not self._tapi:
            oauth_token = TwitterOAuthTokenApi().get(params=dict(id=self.obj['oauthAccessToken']))
            self._tapi = TwitterApi(oauth_access_token=TwitterOAuthToken(**oauth_token))
        return self._tapi
    

class TAccountCacheMgr:
    channel_map = {}
    channel_list = []
    once_suspended_channels = set([])

    @classmethod
    def clear(cls):
        cls.channel_map = {}
        cls.channel_list = []
        cls.once_suspended_channels = set([])
    
    @classmethod
    def load(cls):
        cls.channel_map = {}
        cls.channel_list = []
        cls.once_suspended_channels = set(TAccountStatsApi().admin(params=dict(op='once_suspended_channel_list')))
        cstats_list = TAccountStatsApi().query_all(params=dict(chanState=channel_const.CHANNEL_STATE_NORMAL))
        for cstats in cstats_list:
            chid = int(TAccountStatsApi(cstats).key_name)
            channel = {'chid': chid,
                       'nameLower': cstats['nameLower'],
                       'name': cstats['name'],
                       'topicInfo': cstats['topicInfo'],
                       'followers': cstats['latelyFollower'],
                       }
            cls.channel_map[chid] = channel
        oauth_tokens = TwitterOAuthTokenApi().query_all()
        for oauth_token in oauth_tokens:
            otoken = TwitterOAuthToken(**oauth_token)
            chid = otoken.chid
            if not cls.channel_map.has_key(chid):
                continue
            cls.channel_map[chid]['oauth_token'] = otoken
        cls.channel_list = cls.channel_map.values()
        cls.channel_list.sort(cmp=lambda x, y: cmp(x['followers'], y['followers']), reverse=True)
        logging.info("Loaded %d channels into cache." % len(cls.channel_map))

    @classmethod
    def has_key(cls, chid):
        return cls.channel_map.has_key(int(chid)) 
    
    @classmethod
    def get(cls, chid):
        return cls.channel_map.get(int(chid), None) 
    
    @classmethod
    def get_tapi(cls, chid):
        channel = cls.channel_map.get(int(chid), None)
        return TwitterApi(oauth_access_token=channel['oauth_token']) if channel else None

    @classmethod
    def chid_handle_str(cls, chid):
        channel = cls.get(chid)
        if channel:
            return "%s@%s" % (chid, channel['name'])
        else:
            return "%s@None" % chid

    @classmethod
    def first_topic_key(cls, chid):
        channel = cls.get(chid)
        if not channel: return None
        topic_infos = channel['topicInfo']
        topic_infos = eval(topic_infos) if topic_infos else None
        topic_info = topic_infos[0] if topic_infos else None
        return topic_info[0] if topic_info else None
    
    @classmethod
    def get_random_tapi(cls):
        size = len(cls.channel_list)
        if size == 0:
            return None
        channel = cls.channel_list[random.randint(size/5, size-1)]
        return TwitterApi(oauth_access_token=channel['oauth_token'])

    @classmethod
    def get_random_block(cls, size=10):
        total = len(cls.channel_list)
        if total == 0:
            return None
        start_index = random.randint(0, total/size-1)*size
        return cls.channel_list[start_index:start_index+size]

    @classmethod
    def is_once_suspended(cls, chid):
        return int(chid) in cls.once_suspended_channels    


if __name__ == "__main__":
    apiclient.login_as_admin()
    followers_page1 = TAccountApi.retrieve_followers(chid=39434042, user_id=626706531)
    followers_page2 = TAccountApi.retrieve_followers(chid=39434042, user_id=2557521, cursor=1472912040651209039)
    print len(followers_page1['ids']), len(followers_page2['ids'])
    channels = TAccountApi().query(params=dict(limit=10))
    oauth_tokens = TwitterOAuthTokenApi().query(params=dict(limit=10))
    print 'channels', len(channels['objs']), 'oauth_tokens', len(oauth_tokens['objs'])
    if oauth_tokens:
        chid = oauth_tokens['objs'][0]['key_name'].split(':')[-1]
        first_token = TwitterOAuthTokenApi().get_by_chid(chid)
        print 'First token', TwitterOAuthToken(**first_token)
    TAccountCacheMgr.load()
    TAccountCacheMgr.clear()
    