import datetime
import time
import logging
import csv

from twitter.api import TwitterApi
from client.channel.api import TwitterOAuthToken


CHID_LIST = []
TAPI_BY_CHID = {}


def remove_tweets(chid, tapi):
    remove_count = 0
    try:
        statuses = tapi.statuses.user_timeline(user_id=chid, count=10)
        if not statuses:
            logging.info("Channel %d has no tweet any more!" % chid)
            return 0
        for status in statuses:
            status_id = status['id']
            tapi.statuses.destroy(id=status_id)
            remove_count += 1
        logging.info("Removed %d tweets for channel %d." % (remove_count, chid))
    except Exception, ex:
        logging.exception("Unexpected error after removing %d tweets for channel %s! %s" % (remove_count, chid, str(ex)))
    return remove_count


def read_chids(cfile):
    with open(cfile, 'r') as f:
        for line in f:
            if line: CHID_LIST.append(int(line))


def read_tokens(tfile):
    token_reader = csv.reader(open(tfile, 'rbU'))
    is_header = True
    for row in token_reader:
        if is_header:
            is_header = False
            continue
        chid = int(row[0])
        token_dict = dict(key_name="sns:%d"%chid, handle=row[1], oauth_token=row[2], oauth_token_secret=row[3])
        oauth_access_token = TwitterOAuthToken(**token_dict)
        TAPI_BY_CHID[chid] = TwitterApi(oauth_access_token=oauth_access_token)
        

def execute(args):
    read_chids(args.cfile)
    read_tokens(args.tfile)
    total_count = 0
    tapi_by_chid = {}
    for chid in CHID_LIST:
        tapi = TAPI_BY_CHID.get(chid, None)
        if tapi:
            tapi_by_chid[chid] = tapi
        else:
            logging.error("No oauth token found for channel %d!" % chid)
    while True:
        count = 0
        start_time = datetime.datetime.now()
        try:
            for chid, tapi in tapi_by_chid.items():
                new_count = remove_tweets(chid, tapi)
                if new_count == 0: tapi_by_chid.pop(chid)
                total_count += new_count
                count += new_count
        except:
            logging.exception("Unexpected exception while removing tweets!")
        end_time = datetime.datetime.now()
        duration = int((end_time - start_time).total_seconds())
        logging.info("Finished removing %d tweets in %d seconds for %d channels. Removed total %d tweets." % (count, duration, len(tapi_by_chid), total_count))
        if duration < 1000: time.sleep(1000-duration)
    

def add_subparser(parsers): 
    parser = parsers.add_parser('removetweets', description="Remove tweets", help='remove tweets')
    parser.add_argument('--tfile', required=True, help='tokens file name')
    parser.add_argument('--cfile', required=True, help='channels file name')
    parser.set_defaults(func=execute)


