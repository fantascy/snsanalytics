import datetime

from django.http import HttpResponse

from common.utils import timezone as ctz_util


def get_csv_response_base(name, dated_file_name=True):
    response = HttpResponse(mimetype='text/csv')
    response.write('\xEF\xBB\xBF')
    if dated_file_name:
        usp_now = ctz_util.uspacificnow() - datetime.timedelta(days=1)
        file_name = "%s - %s.csv" % (name, datetime.datetime.strftime(usp_now, "%Y-%m-%d"))
    else:
        file_name = "%s.csv" % name
    response['Content-Disposition'] = "attachment; filename=%s" % file_name
    return response

