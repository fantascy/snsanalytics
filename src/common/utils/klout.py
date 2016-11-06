import time
import urllib, urllib2
import logging

import json

import deploysns
from common.utils import url as url_util


KLOUT_V1_API_URL = "http://api.klout.com/1"
KLOUT_MAX_USER_BATCH_SIZE = 5


def get_params(key, *args, **kwargs):
    params = {} if kwargs is None else kwargs.copy()
    params.update({
              'key': key,
              })
    return urllib.urlencode(url_util.normalize_params(params))        


def url_open(url, retry=0):
    try:
        opener = urllib2.urlopen(url)
        result = opener.read()
        return json.loads(result) 
    except Exception, ex:
        if hasattr(ex, 'code') and ex.code==404:
            logging.error("Klout socre doesn't exist for %s" % url)
            return {}
        logging.error("Klout API Error for %d times for %s %s" % (retry, url, str(ex)))
        if retry<3:
            return url_open(url, retry+1)
    return {}


def op_url(op):
    return "%s/%s.json" % (KLOUT_V1_API_URL, op)


def op_klout_url(key, twitter_handles):
    return "%s?%s" % (op_url('klout'), get_params(key, users=','.join(twitter_handles))) 


def op_klout(key, twitter_handles):
    return url_open(op_klout_url(key, twitter_handles))


def op_klout_scores_batch(key, twitter_handles):
    try:
        results = op_klout(key, twitter_handles)
        users = results.get('users', [])
        return dict([(user['twitter_screen_name'], int(100*user['kscore'])) for user in users])
    except:
        return {}


def op_klout_scores(key, twitter_handles):
    results = {}
    try:
        index = KLOUT_MAX_USER_BATCH_SIZE
        while len(twitter_handles[index-KLOUT_MAX_USER_BATCH_SIZE:index])>0:
            batch_scores = op_klout_scores_batch(key, twitter_handles[index-KLOUT_MAX_USER_BATCH_SIZE:index])
            if len(batch_scores)>0:
                results.update(batch_scores)
            index += KLOUT_MAX_USER_BATCH_SIZE
            time.sleep(0.1)
    except:
        pass
    return results


def main():
    key = deploysns.KLOUT_KEY
    twitter_handles_1 = ['alanxing', 'TravelingDad', 'ZapposUpdate', 'JerryBrownDaily']
    twitter_handles_2 = ['chrishelleman', 'JerryBrownDaily']
    twitter_handles_3 = ['Diablo3Update', 'DragonAgeUpdate', 'GodOfWarNews', 'iPlantsZombies', 'iUFCUndisputed', 'MargieGuildWars']
    twitter_handles_4 = twitter_handles_3 + ['MargieGuildWars', 'MassEffectNews', 'StarCraftUpdate', 'TheWWESmackDown', 'WarcraftUpdate']
    url = op_klout_url(key, twitter_handles_1)
    print url
    results = op_klout_scores(key, twitter_handles_1)
    print json.dumps(results)
    results = op_klout_scores(key, twitter_handles_2)
    print json.dumps(results)
    results = op_klout_scores(key, twitter_handles_3)
    print json.dumps(results)
    results = op_klout_scores(key, twitter_handles_4)
    print json.dumps(results)

    
if __name__ == '__main__':
    main()