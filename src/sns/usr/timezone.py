from pytz import timezone

from common.utils import timezone as ctz_util
from common.utils import datetimeparser
from sns.core.core import get_user


def trans_output(params, key_list):
    for key in params.keys():
        if key in key_list and params[key] is not None:
            dt = datetimeparser.parseDateTime(params[key])
            dt = to_usertz(dt)
            params[key]=dt
            
def trans_input(params, key_list):
    for key in params.keys():
        if key in key_list and params[key] is not None:
            dt=params[key]
            dt=to_utc(dt)
            params[key]=dt

def gettimedelta():
    tzname=get_user().timeZone
    loc=timezone(tzname)
    td=loc.utcoffset(True)
    return td

def to_utc(dt):
    tz_name = get_user().timeZone
    tz = timezone(tz_name)
    if dt.tzinfo is None  :
        dt = tz.localize(dt)
    utc=timezone('UTC')
    dt=dt.astimezone(utc)
    return dt.replace(tzinfo=None)

def to_usertz(dt):
    tz_name = get_user().timeZone
    return ctz_util.to_tz(dt, tz_name)

