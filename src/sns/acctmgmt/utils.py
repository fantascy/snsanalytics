import datetime
import logging

from common import consts as common_const
from common.utils import string as str_util
from sns.acctmgmt import consts as acctmgmt_const


def str_2_datetime(dateStr):
    dateStr = str_util.strip(dateStr)
    if dateStr is None:
        return None
    try:
        return datetime.datetime.strptime(dateStr, common_const.COMMON_DATE_FORMAT)
    except:
        try:
            return datetime.datetime.strptime(dateStr, common_const.COMMON_DATETIME_FORMAT)
        except:
            logging.error("'%s' is wrong date format!" % dateStr)
    return None

    
def state_property(acctType):
    if acctType==acctmgmt_const.ACCT_TYPE_YAHOO:
        return "state"
    else:
        return "tState" 

def time_property(acctType, op):
    if acctType==acctmgmt_const.ACCT_TYPE_YAHOO:
        if op in (acctmgmt_const.ACCT_MGMT_OP_LOGIN, acctmgmt_const.ACCT_MGMT_OP_DUMP):
            return "lastLoginTime"
        else:
            return "lastPasswdChangeTime"
    else:
        if op in (acctmgmt_const.ACCT_MGMT_OP_LOGIN, acctmgmt_const.ACCT_MGMT_OP_DUMP):
            return "tLastLoginTime"
        else:
            return "tLastPasswdChangeTime"
