"""
Constants and utilities to handle all non API errors.
"""

from exceptions import Exception

ERROR_TWITTER_OVER_DAILY_LIMIT = 1001
ERROR_TWITTER_INCORRECT_SIGNATURE = 1002
ERROR_TWITTER_COULD_NOT_AUTHENTICATE = 1003
ERROR_TWITTER_COULD_NOT_OAUTH = 1004
ERROR_FACEBOOK_FEED_ACTION_LIMIT = 1101
ERROR_FACEBOOK_OAUTH = 1102
ERROR_FACEBOOK_AUTHORITY = 1103
ERROR_TIME_OUT = 9901
ERROR_UNKNOWN = 9999


""" This matches an internal error message to a standard user friendly error message. """
ERROR_INFO_MAP = {
    ERROR_TWITTER_OVER_DAILY_LIMIT : "Your Twitter account '%s' reached daily limit on Twitter API usage.",
    ERROR_TWITTER_INCORRECT_SIGNATURE : "Your Twitter account '%s' may have made too many posts in last hour. Your limit could be reset in half hour or less.",
    ERROR_TWITTER_COULD_NOT_AUTHENTICATE: "Could not authenticate your Twitter account '%s'. It is likely your account is suspended by Twitter.",
    ERROR_TWITTER_COULD_NOT_OAUTH : "The OAuth authentication of this account doesn't work any more. Check the status of your account, and try to remove and re-add.",
    ERROR_FACEBOOK_FEED_ACTION_LIMIT : "You have reached Facebook post limit. Your limit will be reset within 48 hours typically.",
    ERROR_FACEBOOK_OAUTH : "The OAuth authentication of this account doesn't work any more. Check the status of your account, and try to remove and re-add.",
    ERROR_FACEBOOK_AUTHORITY : "You have no permission to make this post on this Facebook wall.",
    ERROR_TIME_OUT : "Your request is timed out. Please check your connection with Internet.",
    ERROR_UNKNOWN : "Sorry, an unknown error is encountered. Please try later.",
            }


""" This associates an error code with an error identifier string. """
ERROR_IDENTIFIER_MAP = {
    ERROR_TWITTER_OVER_DAILY_LIMIT : "over daily status update limit",
    ERROR_TWITTER_INCORRECT_SIGNATURE : "Incorrect signature",
    ERROR_TWITTER_COULD_NOT_AUTHENTICATE : "Could not authenticate you",
    ERROR_TWITTER_COULD_NOT_OAUTH : "Could not authenticate with OAuth",
    ERROR_FACEBOOK_FEED_ACTION_LIMIT : "Feed action request limit reached",
    ERROR_FACEBOOK_OAUTH : "Error processing access token",
    ERROR_FACEBOOK_AUTHORITY : "User not visible",
    ERROR_TIME_OUT : "timed out",
    ERROR_UNKNOWN : "Unknown Error",
            }


""" Number of seconds to wait and retry, for each error type. """
ERROR_RETRY_MAP = {
    ERROR_TWITTER_OVER_DAILY_LIMIT : 3600,
    ERROR_TWITTER_INCORRECT_SIGNATURE : 300,
    ERROR_TWITTER_COULD_NOT_AUTHENTICATE: 7200,
    ERROR_TWITTER_COULD_NOT_OAUTH : 18000,
    ERROR_FACEBOOK_FEED_ACTION_LIMIT : 3600,
    ERROR_FACEBOOK_OAUTH : 18000,
    ERROR_TIME_OUT : None,
    ERROR_UNKNOWN : None,
            }


class Error(Exception):
    """
    There are all sorts of different error situations in our system. 
    Let's organize them, handle them systematically.
    error_code - an integer 
    error_info - A msg presented to end user. Usually, the msg is a standard one as defined in the ERROR_INFO_MAP.
        This msg could also be passed over when constructing an error object. In such, we can satisfy needs for different UI pages.
    *args - possible positional arguments used to bind variables in error msg, not used yet
    **kwds - possible dictionary-based arguments for named variables in error msg, not used yet
    """
    def __init__(self, error_code, *args, **kwds):
        if not ERROR_INFO_MAP.has_key(error_code) :
            self.error_code = ERROR_UNKNOWN
            self.args = None
            self.kwds = None
        else :
            self.error_code = error_code
            self.args = args
            self.kwds = kwds
        #if error_info is None :
            self.error_info = ERROR_INFO_MAP.get(self.error_code)
        #else :
        #    self.error_info = error_info 

    def __str__(self):
        return  self.getErrorInfo()
    
    def getErrorInfo(self) :
        if self.error_info.find("%s")!=-1:
            return  self.error_info % self.args
        else:
            return  self.error_info

    def getErrorIdentifier(self) :
        return ERROR_IDENTIFIER_MAP.get(self.error_code, None)

    def getRetrySeconds(self) :
        return ERROR_RETRY_MAP.get(self.error_code, None)

    @classmethod
    def getErrorCodeByIdentifier(self,errorMsg) :
        for k,v in ERROR_IDENTIFIER_MAP.items() :
            if errorMsg.find(v)!=-1 :
                return k
        return ERROR_UNKNOWN

    @classmethod
    def getErrorByIdentifier(self,errorMsg,name) :
        errorCode = self.getErrorCodeByIdentifier(errorMsg)
        return Error(errorCode,name)
    
