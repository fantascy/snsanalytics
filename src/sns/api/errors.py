from exceptions import Exception

API_ERROR_INVALID_HTTP_METHOD = 1001
API_ERROR_UNSUPPORTED_OPERATION = 1002
API_ERROR_UNSUPPORTED_INVOCATION = 1003
API_ERROR_INVALID_MODEL_TYPE = 1004
API_ERROR_USER_NOT_LOGGED_IN = 1005
API_ERROR_USER_NOT_APPROVED = 1006
API_ERROR_GEO_NOT_FOUND=1007
API_ERROR_USER_READ_ONLY = 1008
API_ERROR_MEMCACHE_USER_MISSING = 1009
API_ERROR_USER_INFO_INCOMPLETE = 1010
API_ERROR_USER_EXCEED_ADD_LIMIT=1011
API_ERROR_USER_NO_RIGHT_MODIFY = 1012
API_ERROR_DATA_UNIQUENESS = 1100
API_ERROR_DATA_TYPE_NOT_SUPPORTED = 1101
API_ERROR_DATA_MISSING = 1102
API_ERROR_POSTING_RULE_INVALID_SCHEDULE_INTERVAL = 1309
API_ERROR_POSTING_RULE_OP_NOT_SUPPORTED_IN_STATE = 1310
API_ERROR_URL_INVALID = 1400
API_ERROR_LIMIT_EXCEEDED_DAILY_POST_PER_USER = 2001
API_ERROR_ADMIN_OPERATION = 3003
API_ERROR_ADMIN_PAGE = 3004
#API_ERROR_GAE_MAINTENANCE = 4001
API_ERROR_FB_UNSUPPORTED_OG_TAG = 5001
API_ERROR_UNKNOWN = 9999


API_ERROR_CODE_MAP = {
    API_ERROR_INVALID_HTTP_METHOD : "Request HTTP Method '%s' is invalid for operation '%s'.",
    API_ERROR_UNSUPPORTED_OPERATION : "Operation '%s' is not supported for API module '%s'.",
    API_ERROR_UNSUPPORTED_INVOCATION : "Unsupported invocation!",
    API_ERROR_INVALID_MODEL_TYPE : "Expected type is '%s', while returned type is '%s'.",
    API_ERROR_USER_NOT_LOGGED_IN : "User has not logged in.",
    API_ERROR_USER_READ_ONLY : "Read only for the user",
    API_ERROR_USER_NO_RIGHT_MODIFY : "You have no right to modify",
    API_ERROR_USER_NOT_APPROVED : "Your account has not been approved to use our beta service. To get approval, please email to support@snsanalytics.com.",
    API_ERROR_MEMCACHE_USER_MISSING : "User is logged in but memcache is missing.",
    API_ERROR_USER_INFO_INCOMPLETE : "User information is not complete",
    API_ERROR_DATA_UNIQUENESS : "The model '%s' property '%s' value '%s' already exists.",
    API_ERROR_DATA_TYPE_NOT_SUPPORTED : "Model property data type '%s' is not supported.",
    API_ERROR_DATA_MISSING : "Required data is missing: %s",
    API_ERROR_POSTING_RULE_INVALID_SCHEDULE_INTERVAL : "'%s' is an invalid schedule interval for posting rules.",
    API_ERROR_POSTING_RULE_OP_NOT_SUPPORTED_IN_STATE : "Operation '%s' is invalid for posting rule '%s' with state '%s'",  
    API_ERROR_URL_INVALID : "Invalid URL: '%s'",  
    API_ERROR_LIMIT_EXCEEDED_DAILY_POST_PER_USER : "The user %s has reached daily post limit of %s. Posting abandoned for this user.",
    API_ERROR_ADMIN_OPERATION : "Operation '%s' requires admin privilege.",
    API_ERROR_ADMIN_PAGE : "To see the page requires admin privilege.",
    API_ERROR_USER_EXCEED_ADD_LIMIT :"You can add at most %d %ss!",
    #API_ERROR_GAE_MAINTENANCE:"GAE maintenance error.",
    API_ERROR_UNKNOWN : "%s",
                      }


class ApiError(Exception):
    """
    Exception thrown hen there is an error in API invocation.
    error_code - api error code
    *args - rest of the positional arguments used to bind variables in error msg
    **kwds - dictionary-based arguments for named variables in error msg, not used yet
    """
    def __init__(self, error_code, *args, **kwds):
        self.error_code = error_code if API_ERROR_CODE_MAP.has_key(error_code) else API_ERROR_UNKNOWN
        self.args = args
        self.kwds = kwds

    def __str__(self):
        return  API_ERROR_CODE_MAP[self.error_code] % self.args
    
    
if __name__ == "__main__":
    try:
        raise Exception('spam', 'eggs')
    except Exception, inst:
        print type(inst)     # the exception instance
        print inst.args      # arguments stored in .args
        print inst           # __str__ allows args to printed directly
        x, y = inst          # __getitem__ allows args to be unpacked directly
        print 'x =', x
        print 'y =', y
