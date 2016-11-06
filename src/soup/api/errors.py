from sns.api.errors import *

"""
Soup API error codes, from 5000 to 5999
"""
SOUP_API_ERROR_USER_SUSPENDED = 5001
SOUP_API_ERROR_BAD_TOPIC_DESCRIPTION = 5601


"""
Soup API error code map
"""
SOUP_API_ERROR_CODE_MAP = {
    SOUP_API_ERROR_USER_SUSPENDED : "Soup user suspended. id: %s; name: %s",                           
    SOUP_API_ERROR_BAD_TOPIC_DESCRIPTION : "Bad topic description for topic '%s': '%s'",
                      }


"""
Register Soup API error codes
"""
_SOUP_ERROR_CODES_REGISTERED = False
def _soup_register_error_codes():
    global _SOUP_ERROR_CODES_REGISTERED
    if _SOUP_ERROR_CODES_REGISTERED :
        return
    API_ERROR_CODE_MAP.update(SOUP_API_ERROR_CODE_MAP)
    _SOUP_ERROR_CODES_REGISTERED = True
_soup_register_error_codes()