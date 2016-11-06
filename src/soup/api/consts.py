# -*- coding: utf-8 -*-
"""
This module contains all API related constants that should be shared with any API client.
"""

from sns.api.consts import *

"""
All Soup API modules.
Not all API modules support all API operations.
"""
SOUP_API_M_USER         = 'rating'
SOUP_API_M_TOPIC_RANK   = 'topicrank'

"""
All Soup API operations.
Not all API modules support all API operations.
"""
SOUP_API_O_RATE                 = 'rate'
SOUP_API_O_TOGGLE_ARTICLE_FOLLOW  = 'toggle_article_follow'
SOUP_API_O_IS_ARTICLE_FOLLOWED     = 'is_article_followed'

"""
The second value marks whether the OP is admin or not.
The third value marks whether the OP is cron or not. A cron job is an admin job that doesn't require a current login user.
"""
SOUP_API_OPERATION_MAP = {
    SOUP_API_O_RATE: (API_HTTP_METHOD_GET, False, False),
                     }


"""
Register Soup API operations.
"""
_SOUP_API_OPERATIONS_REGISTERED = False
def _soup_register_api_operations():
    global _SOUP_API_OPERATIONS_REGISTERED
    if _SOUP_API_OPERATIONS_REGISTERED :
        return
    API_OPERATION_MAP.update(SOUP_API_OPERATION_MAP)
    _SOUP_API_OPERATIONS_REGISTERED = True
_soup_register_api_operations()

if __name__ == '__main__':
    pass