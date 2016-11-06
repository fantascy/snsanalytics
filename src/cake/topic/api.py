import context
from sns.serverutils import memcache
from sns.core import core as db_core
from sns.log import api as sns_log_api
from sns.url.models import UrlKeyName
from soup.rank import api as soup_rank_api
from cake import consts as cake_const

def get_hot_articles(topicKey, mediaType, excludeArticles=set([])):
    """ 
    This should be the single place to filter all iframe blacklisted articles.
    This should be the single place to filter all articles visited in the same user session. 
    """
    soupArticles = soup_rank_api.getSoupArticles(topicKey, cake_const.RANK_TYPE_HOT, mediaType)
    sessionHistory = None
    session = context.get_context().http_user_session()
    if session is not None :
        sessionHistory = memcache.get(session)
    if sessionHistory is None :
        sessionHistory = set([])
    cakeArticles = []
    for article in soupArticles :
        articleId = db_core.normalize_2_id(article)
        if articleId is None or articleId in excludeArticles or articleId in sessionHistory :
            continue 
        url = UrlKeyName.urlFromKey(article)
        if not sns_log_api.on_always_blacklist(url) :
            cakeArticles.append(article)
    return cakeArticles
    

