# -*- coding: utf-8 -*-
"""
This module contains all API related constants that should be shared with any API client.
"""

from sns.api.consts import *

"""
All FE API modules.
Not all API modules support all API operations.
"""
API_M_FOLLOW        = 'follow'


"""
The second value marks whether the OP is admin or not.
The third value marks whether the OP is cron or not. A cron job is an admin job that doesn't require a current login user.
"""
FE_API_OPERATION_MAP = {
    }


"""
Register FE API operations.
"""
_FE_API_OPERATIONS_REGISTERED = False
def _fe_register_api_operations():
    global _FE_API_OPERATIONS_REGISTERED
    if _FE_API_OPERATIONS_REGISTERED :
        return
    API_OPERATION_MAP.update(FE_API_OPERATION_MAP)
    _FE_API_OPERATIONS_REGISTERED = True
_fe_register_api_operations()


if __name__ == '__main__':
    pass
