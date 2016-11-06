import time
import logging

from common.utils import formatter
from sns.api import consts as api_const
from sns.chan import consts as channel_const
from client import conf as client_conf
from client import apiclient
from client.channel.api import TAccountStatsApi
from client.channel import tokenmgr


SEARCH_RESULT_FORMATTER = formatter.JsonFormatter(
    fmt=['id', 'screen_name', 'protected', 'followers_count', 'statuses_count','statuses_count', 'verified'])


def refresh_search_rank(cstats):
    chid_handle_str = None
    try:
        cstats_api = TAccountStatsApi(obj=cstats)
        chid_handle_str = cstats_api.chid_handle_str()
        try:
            if cstats_api.search_term:
                tapi = tokenmgr.get_random_tapi() if client_conf.USE_TOKEN_POOL else cstats_api.tapi
                results = tapi.users.search(q=cstats_api.search_term)
                results = SEARCH_RESULT_FORMATTER.format(results)
            else:
                logging.warn("Channel %s doesn't have search term!" % chid_handle_str)
                results = []
        except Exception, tex:
            logging.error("Error searching keyword %s! %s" % (cstats_api.search_term, str(tex)))
            results = []
        rank = TAccountStatsApi().admin(params=dict(op='refresh_search_rank', chid=cstats_api.chid, search_results=results), http_method=api_const.API_HTTP_METHOD_POST)
        logging.info("Search term %s of channel %s is ranked %s." % (cstats_api.search_term, chid_handle_str, rank))
    except Exception, ex:
        logging.exception("Unexpected error while refresh_search_rank(%s)! %s" % (chid_handle_str, str(ex)))
        return None


if __name__ == '__main__':
    count = 0
    while True:
        try:
            apiclient.login_as_admin()
            cstats_qr = TAccountStatsApi().query(params=dict(chanState=channel_const.CHANNEL_STATE_NORMAL, order='searchRankModifiedTime', limit=10))
            cstats_list = cstats_qr['objs']
            for cstats in cstats_list:
                refresh_search_rank(cstats)
                count += 1
        except:
            logging.exception("Unexpected exception while refreshing search rank!")
        logging.info("Finished search rank refresh for total %d channels." % count)
        time.sleep(300)





