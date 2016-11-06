import datetime
from pytz import timezone


"""
Commented away all non integer time zones to make report aggregation easier.
"""        
TZ_LIST = [
    ("US/Pacific","US/Pacific"),
    ("US/Mountain","US/Mountain"),
    ("US/Central","US/Central"),
    ("US/Eastern","US/Eastern"),
    ("US/Alaska","US/Alaska"),
    ("US/Hawaii","US/Hawaii"),
    ("Canada/Pacific","Canada/Pacific"),
    ("Canada/Mountain","Canada/Mountain"),
    ("Canada/Central","Canada/Central"),
    ("Canada/Eastern","Canada/Eastern"),
    ("Canada/Atlantic","Canada/Atlantic"),
    ("Pacific/Kiritimati", "(GMT+14:00) Pacific/Kiritimati"),
    ("Pacific/Enderbury", "(GMT+13:00) Pacific/Enderbury"),
    ("Pacific/Tongatapu", "(GMT+13:00) Pacific/Tongatapu"),
    #("Pacific/Chatham", "(GMT+12:45) Pacific/Chatham"),
    ("Asia/Kamchatka", "(GMT+12:00) Asia/Kamchatka"),
    ("Pacific/Auckland", "(GMT+12:00) Pacific/Auckland"),
    ("Pacific/Fiji", "(GMT+12:00) Pacific/Fiji"),
    #("Pacific/Norfolk", "(GMT+11:30) Pacific/Norfolk"),
    ("Pacific/Guadalcanal", "(GMT+11:00) Pacific/Guadalcanal"),
    #("Australia/Lord_Howe", "(GMT+10:30) Australia/Lord_Howe"),
    ("Australia/Brisbane", "(GMT+10:00) Australia/Brisbane"),
    ("Australia/Sydney", "(GMT+10:00) Australia/Sydney"),
    #("Australia/Adelaide", "(GMT+09:30) Australia/Adelaide"),
    #("Australia/Darwin", "(GMT+09:30) Australia/Darwin"),
    ("Asia/Seoul", "(GMT+09:00) Asia/Seoul"),
    ("Asia/Tokyo", "(GMT+09:00) Asia/Tokyo"),
    ("Asia/Hong_Kong", "(GMT+08:00) Asia/Hong_Kong"),
    ("Asia/Kuala_Lumpur", "(GMT+08:00) Asia/Kuala_Lumpur"),
    ("Asia/Manila", "(GMT+08:00) Asia/Manila"),
    ("Asia/Shanghai", "(GMT+08:00) Asia/Shanghai"),
    ("Asia/Singapore", "(GMT+08:00) Asia/Singapore"),
    ("Asia/Taipei", "(GMT+08:00) Asia/Taipei"),
    ("Australia/Perth", "(GMT+08:00) Australia/Perth"),
    ("Asia/Bangkok", "(GMT+07:00) Asia/Bangkok"),
    ("Asia/Jakarta", "(GMT+07:00) Asia/Jakarta"),
    ("Asia/Saigon", "(GMT+07:00) Asia/Saigon"),
    ("Asia/Rangoon", "(GMT+06:30) Asia/Rangoon"),
    ("Asia/Dacca", "(GMT+06:00) Asia/Dacca"),
    #("Asia/Katmandu", "(GMT+05:45) Asia/Katmandu"),
    ("Asia/Calcutta", "(GMT+05:30) Asia/New_Delhi"),
    #("Asia/Colombo", "(GMT+05:30) Asia/Colombo"),
    ("Asia/Karachi", "(GMT+05:00) Asia/Karachi"),
    ("Asia/Tashkent", "(GMT+05:00) Asia/Tashkent"),
    ("Asia/Yekaterinburg", "(GMT+05:00) Asia/Yekaterinburg"),
    #("Asia/Kabul", "(GMT+04:30) Asia/Kabul"),
    ("Asia/Dubai", "(GMT+04:00) Asia/Dubai"),
    ("Asia/Tbilisi", "(GMT+04:00) Asia/Tbilisi"),
    #("Asia/Tehran", "(GMT+03:30) Asia/Tehran"),
    ("Africa/Nairobi", "(GMT+03:00) Africa/Nairobi"),
    ("Asia/Baghdad", "(GMT+03:00) Asia/Baghdad"),
    ("Asia/Kuwait", "(GMT+03:00) Asia/Kuwait"),
    ("Asia/Riyadh", "(GMT+03:00) Asia/Riyadh"),
    ("Europe/Moscow", "(GMT+03:00) Europe/Moscow"),
    ("Africa/Cairo", "(GMT+02:00) Africa/Cairo"),
    ("Africa/Johannesburg", "(GMT+02:00) Africa/Johannesburg"),
    ("Asia/Jerusalem", "(GMT+02:00) Asia/Jerusalem"),
    ("Europe/Athens", "(GMT+02:00) Europe/Athens"),
    ("Europe/Bucharest", "(GMT+02:00) Europe/Bucharest"),
    ("Europe/Helsinki", "(GMT+02:00) Europe/Helsinki"),
    ("Europe/Istanbul", "(GMT+02:00) Europe/Istanbul"),
    ("Europe/Minsk", "(GMT+02:00) Europe/Minsk"),
    ("Europe/Amsterdam", "(GMT+01:00) Europe/Amsterdam"),
    ("Europe/Berlin", "(GMT+01:00) Europe/Berlin"),
    ("Europe/Brussels", "(GMT+01:00) Europe/Brussels"),
    ("Europe/Paris", "(GMT+01:00) Europe/Paris"),
    ("Europe/Prague", "(GMT+01:00) Europe/Prague"),
    ("Europe/Rome", "(GMT+01:00) Europe/Rome"),
    ("Europe/Dublin", "(GMT+00:00) Europe/Dublin"),
    ("Europe/Lisbon", "(GMT+00:00) Europe/Lisbon"),
    ("Europe/London", "(GMT+00:00) Europe/London"),
    ("GMT", "(GMT+00:00) GMT"),
    ("Atlantic/Cape_Verde", "(GMT-01:00) Atlantic/Cape_Verde"),
    ("Atlantic/South_Georgia", "(GMT-02:00) Atlantic/South_Georgia"),
    ("America/Buenos_Aires", "(GMT-03:00) America/Buenos_Aires"),
    ("America/Sao_Paulo", "(GMT-03:00) America/Sao_Paulo"),
    #("America/St_Johns", "(GMT-03:30) America/St_Johns"),
    ("America/Halifax", "(GMT-04:00) America/Halifax"),
    ("America/Puerto_Rico", "(GMT-04:00) America/Puerto_Rico"),
    ("America/Santiago", "(GMT-04:00) America/Santiago"),
    ("Atlantic/Bermuda", "(GMT-04:00) Atlantic/Bermuda"),
    #("America/Caracas", "(GMT-04:30) America/Caracas"),
    ("America/Bogota", "(GMT-05:00) America/Bogota"),
    ("America/Indianapolis", "(GMT-05:00) America/Indianapolis"),
    ("America/Lima", "(GMT-05:00) America/Lima"),
    ("America/New_York", "(GMT-05:00) America/New_York"),
    ("America/Panama", "(GMT-05:00) America/Panama"),
    ("America/Chicago", "(GMT-06:00) America/Chicago"),
    ("America/El_Salvador", "(GMT-06:00) America/El_Salvador"),
    ("America/Mexico_City", "(GMT-06:00) America/Mexico_City"),
    ("America/Denver", "(GMT-07:00) America/Denver"),
    ("America/Phoenix", "(GMT-07:00) America/Phoenix"),
    ("America/Los_Angeles", "(GMT-08:00) America/Los_Angeles"),
    ("America/Tijuana", "(GMT-08:00) America/Tijuana"),
    ("America/Anchorage", "(GMT-09:00) America/Anchorage"),
    ("Pacific/Honolulu", "(GMT-10:00) Pacific/Honolulu"),
    ("Pacific/Niue", "(GMT-11:00) Pacific/Niue"),
    ("Pacific/Pago_Pago", "(GMT-11:00) Pacific/Pago_Pago")
]


def to_tz(dt, tz_name):
    utc = timezone('UTC')
    tz = timezone(tz_name)
    if dt.tzinfo is None  :
        dt = utc.localize(dt)
    return dt.astimezone(tz)


def localize(time, tz_name):
    tz = timezone(tz_name)
    time = tz.localize(time)
    return time.astimezone(tz)


def to_utc(time):
    return to_tz(time, 'UTC')


def to_uspacific(time):
    return to_tz(time, 'US/Pacific')


def uspacificnow():
    return to_uspacific(time=datetime.datetime.utcnow())


def uspacific_today():
    return to_uspacific(time=datetime.datetime.utcnow()).date()


def uspacific_yesterday():
    return uspacific_today() - datetime.timedelta(days=1)


def timestamp_2_utc(tstamp):
    return datetime.datetime.fromtimestamp(tstamp, tz=timezone('UTC')).replace(tzinfo=None)
    
    
def main():
    utcnow = datetime.datetime.utcnow()
    uspacificnow = to_uspacific(utcnow)
    print "utcnow=%s; uspacificnow=%s; uspacifichour=%s" % (utcnow, uspacificnow, uspacificnow.hour)
    print "yesterday=%s; today=%s" % (uspacific_yesterday(), uspacific_today())
    naivenow = datetime.datetime(year=2012, month=1, day=1)
    print "naivenow=%s; localize=%s" % (naivenow, localize(naivenow, 'US/Pacific'))
    

if __name__ == "__main__":
    main()
