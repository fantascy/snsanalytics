from exceptions import Exception
import logging
import json


"""
Constants and utilities to handle Twitter errors.
"""

TWITTER_ERROR_CODE_POST_LIMIT_EXCEEDED = 1001
TWITTER_ERROR_CODE_MISSING_OAUTH_TOKEN = 1002


TWITTER_ERROR_OVER_DAILY_LIMIT = "over daily status update limit"
TWITTER_ERROR_INCORRECT_SIGNATURE = "Incorrect signature"
TWITTER_ERROR_COULD_NOT_AUTHENTICATE = "Could not authenticate you"
TWITTER_ERROR_COULD_NOT_OAUTH = "Could not authenticate with OAuth"
FACEBOOK_ERROR_FEED_ACTION_LIMIT = "Feed action request limit reached"
FACEBOOK_ERROR_OAUTH = "Error processing access token"
TWITTER_ERROR_UNKNOWN = "Unknown error"


ERROR_MAP = {
    TWITTER_ERROR_OVER_DAILY_LIMIT : (TWITTER_ERROR_OVER_DAILY_LIMIT, 3600),
    TWITTER_ERROR_INCORRECT_SIGNATURE : ("Incorrect signature. Account may have made too many posts last hour.", 300),
    TWITTER_ERROR_COULD_NOT_AUTHENTICATE: (TWITTER_ERROR_COULD_NOT_AUTHENTICATE, 7200),
    TWITTER_ERROR_COULD_NOT_OAUTH : (TWITTER_ERROR_COULD_NOT_OAUTH, 18000),
    FACEBOOK_ERROR_FEED_ACTION_LIMIT : (FACEBOOK_ERROR_FEED_ACTION_LIMIT, 3600),
    FACEBOOK_ERROR_OAUTH : (FACEBOOK_ERROR_OAUTH,18000),
    TWITTER_ERROR_UNKNOWN : (TWITTER_ERROR_UNKNOWN, None),
            }


PERMANENT_ERROR_LIST = [
    TWITTER_ERROR_OVER_DAILY_LIMIT,
    TWITTER_ERROR_INCORRECT_SIGNATURE,
    TWITTER_ERROR_COULD_NOT_AUTHENTICATE,
    TWITTER_ERROR_COULD_NOT_OAUTH,
    FACEBOOK_ERROR_FEED_ACTION_LIMIT,
    FACEBOOK_ERROR_OAUTH,
                      ]


class TwitterError(Exception):
    def __init__(self, resp_content, status_code=0, oauth_access_token=None):
        user_str = oauth_access_token.user_str() if oauth_access_token else None
        Exception.__init__(self, "Twitter API error - %s - %s - %s" % (status_code, user_str, resp_content[:256]))
        self.status_code = status_code
        self.oauth_access_token = oauth_access_token
        try:
            resp = json.loads(resp_content)
            error = resp['errors'][0]
            self.error_code = error['code']
            self.error_message = error['message']
        except:
            logging.error("TwitterError: Couldn't decode response to json object. %s" % resp_content)
            self.error_code = 0
            self.error_message = "Not able to parse error message from response."

    def is_following_suspended_target(self):
        return self.status_code == 403 and self.message.find("this account has been suspended")!=-1

    @classmethod
    def raise_post_limit_exceeded(cls, oauth_access_token):
        message = "{'errors':[{'code':%d, 'message':'Twitter POST limit exceeded for %s!'}]}" % (TWITTER_ERROR_CODE_POST_LIMIT_EXCEEDED, oauth_access_token.user_str())
        raise cls(message, status_code=TWITTER_ERROR_CODE_POST_LIMIT_EXCEEDED, oauth_access_token=oauth_access_token)

    @classmethod
    def raise_missing_oauth_access_token(cls):
        message = "{'errors':[{'code':%d, 'message':'Missing OAuth access token!'}]}" % TWITTER_ERROR_CODE_MISSING_OAUTH_TOKEN
        raise cls(message, status_code=TWITTER_ERROR_CODE_MISSING_OAUTH_TOKEN)


def matchError(errorMsg) :
    """ 
    There are a lot of Twitter errors. Some of them are temporary. Some of them may be permanent.
    Overall, different errors needs different recover time.
    This function helps identify an error from error msg. 
    It then returns the matched error and retry secondss if not matched; otherwise, return (None, None).
    """
    for k,v in ERROR_MAP.items() :
        if errorMsg.find(k)!=-1 :
            return v
    return (TWITTER_ERROR_UNKNOWN, None)


def _matchErrorMsg(ex, msg):
    ex = str(ex).decode('utf-8','ignore')
    ex = ex.lower()
    if ex.find(msg.lower()) != -1 :
        return True
    else:
        return False

def isAppError2(ex):
    return _matchErrorMsg(ex, "ApplicationError: 2")
            
def isAppError5(ex):
    return _matchErrorMsg(ex, "ApplicationError: 5")

def isOverCapacity(ex):
    """
    130 - Over capacity
    """
    return isinstance(ex, TwitterError) and ex.error_code == 130

def isStatus401(ex):
    return _matchErrorMsg(ex, "return status: 401")

def isStatus401InvalidApp(ex):
    return isStatus401(ex) and _matchErrorMsg(ex, "Invalid application")

def isStatus401NotAuthorized(ex):
    return isStatus401(ex) and _matchErrorMsg(ex, "Not authorized")

def isStatus403(ex):
    return _matchErrorMsg(ex, "return status: 403")

def isStatus404(ex):
    return _matchErrorMsg(ex, "return status: 404")

def isStatus404OrNotFound(ex):
    return isStatus404(ex) or isNotFound(ex)

def isStatus500(ex):
    return _matchErrorMsg(ex, "return status: 500")

def isStatus502(ex):
    return _matchErrorMsg(ex, "return status: 502")

def isStatus503(ex):
    return _matchErrorMsg(ex, "return status: 503")

def isSuspended(ex):
    """
    159 - Sorry, this account has been suspended
    """
    if _matchErrorMsg(ex, 'authentication is not supported') or _matchErrorMsg(ex, 'could not authenticate') or _matchErrorMsg(ex, 'suspended'):
        logging.error(str(ex))
        return True
    else:
        return False

def isTargetSuspended(ex):
    """
    159 - Sorry, this account has been suspended
    """
    return isinstance(ex, TwitterError) and ex.error_code == 159

def isWriteRequiringToken(ex): 
    return _matchErrorMsg(ex, "Write operations require an access token")

def isRateLimitExceeded(ex):
    return isinstance(ex, TwitterError) and ex.error_code == TWITTER_ERROR_CODE_POST_LIMIT_EXCEEDED or _matchErrorMsg(ex, "Rate limit exceeded")

def isPageNotExist(ex):
    """
    34 - Sorry, that page does not exist
    """
    return isinstance(ex, TwitterError) and ex.error_code == 34

def isNotFound(ex):
    """
    108 - Cannot find specified user
    """
    return isinstance(ex, TwitterError) and ex.error_code == 108 or _matchErrorMsg(ex, "Not found")

def isNotFriend(ex):
    return _matchErrorMsg(ex, "You are not friends with the specified user")

def isCouldNotFollow(ex): 
    """
    162 - You have been blocked from following this account at the request of the user
    """
    return isinstance(ex, TwitterError) and ex.error_code == 162 or _matchErrorMsg(ex, "Could not follow user")

def isDuplicatedTweet(ex): 
    return _matchErrorMsg(ex, "Status is a duplicate")

def isInvalidToken(ex): 
    return _matchErrorMsg(ex, "Error validating access token")

def isMissingToken(ex): 
    return isinstance(ex, TwitterError) and ex.error_code == TWITTER_ERROR_CODE_MISSING_OAUTH_TOKEN

def isPossiblySuspended(ex): 
    return isSuspended(ex) or isStatus401NotAuthorized(ex) or isWriteRequiringToken(ex)

def isTemporaryError(ex): 
    return isOverCapacity(ex) or isAppError2(ex) or isAppError5(ex) or isStatus500(ex) or isStatus503(ex)

def is_over_140_chars(ex): 
    return _matchErrorMsg(ex, "over 140 characters")

def isAlreadyFollowing(ex): 
    """
    160 - You've already requested to follow
    """
    return isinstance(ex, TwitterError) and ex.error_code == 160

