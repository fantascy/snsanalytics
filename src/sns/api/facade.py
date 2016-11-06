'''
The single entry point that routes all external and internal API requests.
'''

from common.api.facade import ApiFacade
from sns.api import consts
from sns.api import errors
from sns.api import processors 

SNS_API_FACADE = ApiFacade(api_const=consts, api_error=errors, api_processor_map=processors.API_PROCESSOR_MAP)

route = SNS_API_FACADE.route    

iapi = SNS_API_FACADE.iapi


