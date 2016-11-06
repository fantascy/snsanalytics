from sns.api.errors import *

"""
FE API error codes, from 7000 to 7999
"""


"""
FE API error code map
"""
FE_API_ERROR_CODE_MAP = {
    }


"""
Register FE API error codes
"""
_FE_ERROR_CODES_REGISTERED = False
def _fe_register_error_codes():
    global _FE_ERROR_CODES_REGISTERED
    if _FE_ERROR_CODES_REGISTERED :
        return
    API_ERROR_CODE_MAP.update(FE_API_ERROR_CODE_MAP)
    _FE_ERROR_CODES_REGISTERED = True
_fe_register_error_codes()