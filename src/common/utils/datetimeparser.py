import re
from datetime import datetime
from datetime import date
from datetime import timedelta

from pytz import FixedOffset

_INTERVAL_UNIT_MAP = {
    'min': 1L, 
    'minute':1L,
    'hr':60L,
    'hour':60L,
    'day':60L*24,
    'wk':60L*24*7,
    'week':60L*24*7,
    'mo':60L*24*30,
    'month':60L*24*30,
                 }    

def parseInterval(interval, expedite_factor=1):
    """
    A valid interval should be a number followed by a time unit, e.g., '15Min', '3Hr', '4Day', etc.
    Valid time unit includes: 'Min'/'Minute', 'Hr'/'Hour', 'Day', 'Week'/'Wk', 'Month'/'Mo', case insensitive
    Returns a timedelta value of the interval
    """
    try :
        values = re.match(r'(\d+)(\w+)', interval).groups()
        if expedite_factor is None :
            expedite_factor = 1
           
        number = int(values[0])/expedite_factor
        unit = values[1].lower()
        return timedelta(minutes=number*_INTERVAL_UNIT_MAP[unit])
        
    except :
        raise Exception("Invalid time interval '%s'!" % interval)
     
def parseDateTime(s):
    """Create datetime object representing date/time
       expressed in a string
 
    Takes a string in the format produced by calling str()
    on a python datetime object and returns a datetime
    instance that would produce that string.
 
    Acceptable formats are: "YYYY-MM-DD HH:MM:SS.ssssss+HH:MM",
                            "YYYY-MM-DD HH:MM:SS.ssssss",
                            "YYYY-MM-DD HH:MM:SS+HH:MM",
                            "YYYY-MM-DD HH:MM:SS"
    Where ssssss represents fractional seconds.     The timezone
    is optional and may be either positive or negative
    hours/minutes east of UTC.
    """
    if s is None:
        return None
    # Split string in the form 2007-06-18 19:39:25.3300-07:00
    # into its constituent date/time, microseconds, and
    # timezone fields where microseconds and timezone are
    # optional.
    m = re.match(r'(.*?)(?:\.(\d+))?(([-+]\d{1,2}):(\d{2}))?$',
                 str(s))
    datestr, fractional, tzname, tzhour, tzmin = m.groups()
 
    # Create tzinfo object representing the timezone
    # expressed in the input string.  The names we give
    # for the timezones are lame: they are just the offset
    # from UTC (as it appeared in the input string).  We
    # handle UTC specially since it is a very common case
    # and we know its name.
    if tzname is None:
        tz = None
    else:
        tzhour, tzmin = int(tzhour), int(tzmin)
        if tzhour == tzmin == 0:
            tzname = 'UTC'
        tz = FixedOffset(timedelta(hours=tzhour,
                                   minutes=tzmin), tzname)
 
    # Convert the date/time field into a python datetime
    # object.
    x = datetime.strptime(datestr, "%Y-%m-%d %H:%M:%S")
 
    # Convert the fractional second portion into a count
    # of microseconds.
    if fractional is None:
        fractional = '0'
    fracpower = 6 - len(fractional)
    fractional = float(fractional) * (10 ** fracpower)
 
    # Return updated datetime object with microseconds and
    # timezone information.
    return x.replace(microsecond=int(fractional), tzinfo=tz)
 

"""
When using the following isXxxDiff() functions, make sure set input datetimes be in the same time zone.
"""
def isMinuteDiff(dt1,dt2):
    return dt1.minute!=dt2.minute or dt1.hour!=dt2.hour or dt1.day!=dt2.day or dt1.month!=dt2.month or dt1.year!=dt2.year
    
def isHourDiff(dt1, dt2):
    return dt1.hour!=dt2.hour or dt1.day!=dt2.day or dt1.month!=dt2.month or dt1.year!=dt2.year

def isDayDiff(dt1, dt2):
    return dt1.day!=dt2.day or dt1.month!=dt2.month or dt1.year!=dt2.year

def isWeekDiff(dt1, dt2):
    timedelta = dt2 - dt1
    return dt1.weekday()>dt2.weekday() or dt1.weekday()==dt2.weekday() and timedelta.days>0 or dt1.weekday()<dt2.weekday() and timedelta.days>7
    
def isMonthDiff(dt1, dt2):
    return dt1.month!=dt2.month or dt1.year!=dt2.year

def isYearDiff(dt1, dt2):
    return dt1.year!=dt2.year

def date_2_datetime(d):
    return datetime(d.year, d.month, d.day) if d else None
    
def truncate_2_hour(dt):
    if dt is None: return None
    if isinstance(dt, datetime):
        pass
    elif isinstance(dt, date):
        dt = date_2_datetime(dt)
    td = timedelta(minutes=dt.minute, seconds=dt.second, microseconds=dt.microsecond)
    return dt - td

def truncate_2_day(dt):
    if isinstance(dt, datetime):
        return dt.date() 
    elif isinstance(dt, date):
        return dt
    else:
        raise Exception("Invalid input date time!")

"""
The intXXXX functions returns an int value that preserves the comparison order of a datetime.
For instance, a datetime (2009, 09, 01, 07, 30) is constructed to 
    2009090107 by intHour(), 
    20090901 by intDay(), 
    20090831 by intWeek(), # intWeek always returns the last Monday  
    200909 by intMonth(),
    2009 by intYear(). 
"""
INT_DATE_FORMAT = "%Y%m%d" 

def intYear(d):
    return int(str(d.year).zfill(4))
    
def intMonth(d):
    return intYear(d)*100 + d.month
    
def intDay(d):
    return intMonth(d)*100 + d.day
    
def intWeek(d):
    td = timedelta(days=d.weekday())
    lastMonday = d - td
    return intDay(lastMonday)
    
def intHour(d):
    return intDay(d)*100 + d.hour

def intMinute(d):
    return intHour(d)*100 + d.minute   

def _int_datetime_2_list(idt):
    l = []
    while idt:
        l.append(idt % 100)
        idt /= 100
    int_year = l[-1] * 100 + l[-2]
    l[-2]  = int_year
    l = l[:-1]
    l.reverse()
    return l

def int_day_2_datetime(idt):
    l = _int_datetime_2_list(idt)
    return datetime(year=l[0], month=l[1], day=l[2])
 
def int_hour_2_datetime(idt):
    l = _int_datetime_2_list(idt)
    return datetime(year=l[0], month=l[1], day=l[2], hour=l[3])
    
def decrement_int_month(im):
    d = datetime.strptime(str(im * 100 + 1), INT_DATE_FORMAT)
    return intMonth(d - timedelta(days=1))

def timedelta_in_seconds(td):
    return None if td is None else td.days*86400 + td.seconds
    
def timedelta_in_minutes(td):
    return None if td is None else timedelta_in_seconds(td)/60
    
def timedelta_in_hours(td):
    return None if td is None else timedelta_in_minutes(td)/60

def first_monday_of_month(dordt):
    dofm = date(dordt.year, dordt.month, 1)
    while dofm.isocalendar()[2] != 1:
        dofm += timedelta(days=1)
    return dofm
        
def is_in_first_week_of_month(dordt):
    d = truncate_2_day(dordt)
    first_monday = first_monday_of_month(d)
    second_monday = first_monday + timedelta(days=7)
    return d >= first_monday and d < second_monday

def is_in_second_week_of_month(dordt):
    return is_in_first_week_of_month(dordt - timedelta(days=7))

def is_in_third_week_of_month(dordt):
    return is_in_first_week_of_month(dordt - timedelta(days=14))





    
    
