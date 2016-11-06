import urllib
import datetime
import json

from common import consts as common_const


def get_short_url_length():
    from sns.serverutils import memcache
    length = memcache.get(common_const.TWITTER_SHORT_URL_LENGTH_KEY)
    if length is None:
        url = 'https://api.twitter.com/1.1/help/configuration.json'
        data = urllib.urlopen(url).read()
        data = json.loads(data)
        length = data['short_url_length']
        memcache.set(common_const.TWITTER_SHORT_URL_LENGTH_KEY, length)
    return length
        

TWITTER_PEOPLE_SEARCH_URL = "https://twitter.com/#!/search/users/%s"
def get_people_search_url(term):
    if term is None:
        term = 'users'
    return TWITTER_PEOPLE_SEARCH_URL % term


def t_strptime(tstr):
    """ Twitter created_at time sample "Mon Feb 26 18:05:55 +0000 2007" """
    try:
        if not tstr: return None
        splits = tstr.split()
        splits = splits[:4] + splits[-1:]
        tstr = ' '.join(splits)
        fmt = "%a %b %d %H:%M:%S %Y"
        return datetime.datetime.strptime(tstr, fmt)
    except:
        return None


def hack_tweet_with_media(s):
    if not s: return s
    msg_length = 90
    separator = ' http://'
    tokens = s.split(separator)
    return ''.join([tokens[0][slice(0, msg_length-3)].strip(), '...', separator, tokens[1]])


TWEET_URL_STUB = "https://twitter.com/statuses/"
def tweet_id_2_url(tweet_id):
    return "%s%s" % (TWEET_URL_STUB, tweet_id)






    
    