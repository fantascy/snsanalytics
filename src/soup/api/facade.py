'''
The single entry point that routes all external and internal API requests.
'''
from common.api.facade import ApiFacade
import consts
import errors
from processors import API_PROCESSOR_MAP

SOUP_API_FACADE = ApiFacade(api_const=consts, api_error=errors, api_processor_map=API_PROCESSOR_MAP)

route = SOUP_API_FACADE.route

iapi = SOUP_API_FACADE.iapi


