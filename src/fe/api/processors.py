from sns.api.processors import API_PROCESSOR_MAP

from fe.api.consts import *
from fe.follow.api import FollowCampaignProcessor


FE_API_PROCESSOR_MAP = {
    API_M_FOLLOW        :FollowCampaignProcessor,
    }

"""
Register FE API processors
"""
_FE_API_PROCESSOR_REGISTERED = False
def _fe_register_error_codes():
    global _FE_API_PROCESSOR_REGISTERED
    if _FE_API_PROCESSOR_REGISTERED :
        return
    API_PROCESSOR_MAP.update(FE_API_PROCESSOR_MAP)
    _FE_API_PROCESSOR_REGISTERED = True
_fe_register_error_codes()