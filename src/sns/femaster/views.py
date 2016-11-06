import json
import logging

from django.http import HttpResponse

from common import consts as common_const
from sns.femaster.models import Source, TgtflwrFollowLog


def worker_get_tgtflwrs(request):
    data = None
    state = common_const.JSON_HTTP_RESPONSE_STATE_FAILURE
    try:
        chid = request.REQUEST.get('chid')
        source = Source.get_or_insert_by_chid(chid) 
        if source.enough:
            data = eval(source.tgtflwrs)
            state = common_const.JSON_HTTP_RESPONSE_STATE_SUCCESS
    except:
        logging.exception("Error when getting allocated target followers!")
    resp = json.dumps(dict(state=state, data=data), indent=4)
    return HttpResponse(resp)


def worker_report_status(request):
    data = None
    state = common_const.JSON_HTTP_RESPONSE_STATE_FAILURE
    try:
        chid = int(request.REQUEST.get('chid'))
        source = Source.get_or_insert_by_chid(chid)
        TgtflwrFollowLog.create(chid, source.get_tgtflwrs())
        source.reset(db_put=True)
        state = common_const.JSON_HTTP_RESPONSE_STATE_SUCCESS
    except:
        logging.exception("Error when clearing allocated target followers!")
    resp = json.dumps(dict(state=state, data=data), indent=4)
    return HttpResponse(resp)


