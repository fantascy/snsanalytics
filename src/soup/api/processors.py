from sns.api.processors import API_PROCESSOR_MAP
import consts as api_const
from soup.user.api import ChannelProcessor
from soup.rank.api import TopicRankProcessor

SOUP_API_PROCESSOR_MAP = {
    api_const.SOUP_API_M_USER : ChannelProcessor,
    api_const.SOUP_API_M_TOPIC_RANK : TopicRankProcessor,
    }

"""
Register Soup API processors
"""
_SOUP_API_PROCESSOR_REGISTERED = False
def _soup_register_error_codes():
    global _SOUP_API_PROCESSOR_REGISTERED
    if _SOUP_API_PROCESSOR_REGISTERED :
        return
    API_PROCESSOR_MAP.update(SOUP_API_PROCESSOR_MAP)
    _SOUP_API_PROCESSOR_REGISTERED = True
_soup_register_error_codes()