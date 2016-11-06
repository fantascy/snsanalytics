from soup.api.processors import API_PROCESSOR_MAP
import consts as api_const

CAKE_API_PROCESSOR_MAP = {
    }

"""
Register Cake API processors
"""
_CAKE_API_PROCESSOR_REGISTERED = False
def _cake_register_error_codes():
    global _CAKE_API_PROCESSOR_REGISTERED
    if _CAKE_API_PROCESSOR_REGISTERED :
        return
    API_PROCESSOR_MAP.update(CAKE_API_PROCESSOR_MAP)
    _CAKE_API_PROCESSOR_REGISTERED = True
_cake_register_error_codes()