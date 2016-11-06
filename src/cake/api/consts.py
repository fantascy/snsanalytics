# -*- coding: utf-8 -*-
"""
This module contains all API related constants that should be shared with any API client.
"""

from sns.api.consts import *
from soup.api.consts import *

"""
All Cake API modules.
Not all API modules support all API operations.
"""

"""
All Cake API operations.
Not all API modules support all API operations.
"""

"""
The second value marks whether the OP is admin or not.
The third value marks whether the OP is cron or not. A cron job is an admin job that doesn't require a current login user.
"""
CAKE_API_OPERATION_MAP = {
                     }


"""
Register Cake API operations.
"""
_CAKE_API_OPERATIONS_REGISTERED = False
def _cake_register_api_operations():
    global _CAKE_API_OPERATIONS_REGISTERED
    if _CAKE_API_OPERATIONS_REGISTERED :
        return
    API_OPERATION_MAP.update(CAKE_API_OPERATION_MAP)
    _CAKE_API_OPERATIONS_REGISTERED = True
_cake_register_api_operations()

if __name__ == '__main__':
    pass