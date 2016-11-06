from sns.api.errors import *
from soup.api.errors import *

"""
Cake API error codes, from 6000 to 6999
"""


"""
Cake API error code map
"""
CAKE_API_ERROR_CODE_MAP = {
                      }


"""
Register Cake API error codes
"""
_CAKE_ERROR_CODES_REGISTERED = False
def _cake_register_error_codes():
    global _CAKE_ERROR_CODES_REGISTERED
    if _CAKE_ERROR_CODES_REGISTERED :
        return
    API_ERROR_CODE_MAP.update(CAKE_API_ERROR_CODE_MAP)
    _CAKE_ERROR_CODES_REGISTERED = True
_cake_register_error_codes()