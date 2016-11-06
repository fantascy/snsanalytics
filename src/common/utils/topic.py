from common.utils import string as str_util


def canonical_name(name):
    return str_util.strip(name.split(',')[0].split('(')[0])
