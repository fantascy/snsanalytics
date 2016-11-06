from common.utils import string as str_util


def get(request, param, default=None):
    value = request.REQUEST.get(param, None)
    if str_util.strip(value) is None:
        value = default
    return value


    