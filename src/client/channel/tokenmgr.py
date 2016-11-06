import logging
import random

from twitter.api import TwitterApi
from twitter import tokenpool as twitter_tokenpool
from sns.chan import consts as channel_const
from client import apiclient
from client.channel.api import TwitterOAuthToken, TAccountApi, TwitterOAuthTokenApi


def get_random_tapi():
    return get_random_tapi_from(twitter_tokenpool.FE_TOKENS)


def get_random_tapi_from(token_list):
    index = random.randint(0, len(token_list)-1)
    chid, handle, oauth_token, oauth_token_secret = token_list[index]
    key_name = "Twitter:%s" % chid
    return TwitterApi(oauth_access_token=TwitterOAuthToken(key_name=key_name, handle=handle,  oauth_token=oauth_token, oauth_token_secret=oauth_token_secret))
    

def retrieve_all_active_tokens():
    channel_map = {}
    channel_list = TAccountApi().query_all(params=dict(state=channel_const.CHANNEL_STATE_NORMAL))
    for channel in channel_list:
        channel = TAccountApi(channel)
        channel_map[channel.chid] = channel
    oauth_tokens = TwitterOAuthTokenApi().query_all()
    token_list = []
    for oauth_token in oauth_tokens:
        otoken = TwitterOAuthToken(**oauth_token)
        chid = otoken.chid
        if not channel_map.has_key(chid):
            continue
        channel = channel_map.get(chid)
        otoken.handle = channel.name
        token_list.append(otoken)
    token_list.sort(cmp=lambda x, y: cmp(x.handle, y.handle))
    logging.info("Retrieved %d active oauth tokens." % len(token_list))
    return token_list
    

def retrieve_all_tokens():
    oauth_tokens = TwitterOAuthTokenApi().query_all()
    token_list = []
    for oauth_token in oauth_tokens:
        otoken = TwitterOAuthToken(**oauth_token)
        token_list.append(otoken)
    token_list.sort(cmp=lambda x, y: cmp(x.handle, y.handle))
    logging.info("Retrieved total %d oauth tokens." % len(token_list))
    return token_list
    

TOKEN_HEADER = ['ID', 'Handle', 'Access Token', 'Secret Token']


if __name__ == '__main__':
    apiclient.login_as_admin()
    token_list = retrieve_all_tokens()
    print ",".join(TOKEN_HEADER)
    for token in token_list:
        print ",".join((str(token.chid), token.handle, token.oauth_token, token.oauth_token_secret))
    
