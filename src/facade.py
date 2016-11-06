import context
from sns.api import facade as sns_api_facade
from fe.api import facade as fe_api_facade
from soup.api import facade as soup_api_facade
from appspot.api import facade as appspot_api_facade


API_FACADE_MAP = {
    "sns" : sns_api_facade,
    "fe" : fe_api_facade,
    "soup" : soup_api_facade,
    "appspot" : appspot_api_facade,
    }

def route(request, url):
    """
    This is the single function that routes all external API requests.
    """
    return API_FACADE_MAP[context.get_context().app()].route(request, url)
