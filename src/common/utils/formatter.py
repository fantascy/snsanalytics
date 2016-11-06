import json
# import yaml

from common.utils import jsonpath


"""
All formatters take a json data object and a format.
"""


def get_formatter(fmt='json'):
    if fmt == 'yaml':
        return YamlFormatter()
    elif fmt == 'json':
        return JsonFormatter()
    else:
        return JsonpathFormatter(fmt=fmt)


class BaseFormatter:
    def __init__(self, fmt=None):
        self.fmt = fmt
        
    @classmethod
    def utf8_encode(cls, value):
        if value is None: return ''
        return value.encode('utf-8') if isinstance(value, unicode) else str(value)


class YamlFormatter(BaseFormatter):
    def format(self, data):
        data = json_filter(data, self.fmt)
        return #yaml.safe_dump(data, default_flow_style=False, indent=4)
    

class JsonFormatter(BaseFormatter):
    def format(self, data):
        data = json_filter(data, self.fmt)
        return json.dumps(data, indent=4)


class TabFormatter(BaseFormatter):
    def format(self, data, delimiter='\t', newline='\n'):
        output = ''
        fmtobj = JsonpathTabFormatter(fmt=self.fmt).format(data)
        for pos, obj in enumerate(fmtobj):
            output += obj['label'] + delimiter
            fields = obj['fields']
            if fields:
                output += delimiter.join([self.utf8_encode(i) for i in fields])
            for subrow in obj['rows']:
                output += newline
                output += subrow['label'] + delimiter
                fields = subrow['fields']
                if fields:
                    output += delimiter.join([self.utf8_encode(i) for i in fields])
                if pos != len(fmtobj)-1:
                    output += newline
            if pos != len(fmtobj)-1:
                output += newline
        return output


class JsonpathTabFormatter(BaseFormatter):
    def __init__(self, fmt=None):
        BaseFormatter.__init__(self, fmt if fmt else {})
        
    def format(self, data):
        ''' Takes a format object and a jsonstring
            and formats the jsonstring into a formatted
            object representation.
            # TODO: add example
        '''
    
        def maybe_list(obj):
            ''' Wrap an object in a list if it isn't already a list '''
            if isinstance(obj, list):
                return obj
            else:
                return [obj]
    
        def applyformat(obj, fmt):
            return {
                'label'  : fmt.get('label', ''),
                'fields' : jsonpath.jsonpath(obj, fmt['fields'])
            }
    
        output = []
        for jsn in maybe_list(data):
            formatted = applyformat(jsn, self.fmt)
            formatted['rows'] = []
            for row in self.fmt.get('rows', []):
                root = row.get('root')
                if root:
                    jsn = jsonpath.jsonpath(jsn, root)
                for j in maybe_list(jsn):
                    formatted['rows'].append(applyformat(j, row))
            output.append(formatted)
        return output


class JsonpathFormatter(BaseFormatter):
    def __init__(self, fmt=None):
        if fmt is None: raise Exception("Jsonpath should not be empty!")
        if not fmt.startswith('$'): fmt = '$.' + fmt
        BaseFormatter.__init__(self, fmt)
    
    def format(self, data, raise_exception=True):
        try:
            results = jsonpath.jsonpath(data, self.fmt)    
            if results is False:
                raise Exception("Invalid format! %s" % self.fmt)
            if len(results) == 1:
                result = results[0]
                if isinstance(result, dict) or isinstance(result, list) or isinstance(result, tuple):
                    return json.dumps(result, indent=4)
                else:
                    return self.utf8_encode(result)
            return json.dumps(results, indent=4)
        except Exception, ex:
            if raise_exception:
                raise ex
            else:
                return None

def json_filter(data, fmt=None):
    """ Filter the input json data using the input format. """
    if fmt is None:
        return data
    data_out = [] if isinstance(fmt, list) else {}
    _json_filter(data, data_out, fmt)
    return data_out


def _json_filter(data, data_out, fmt):
    if isinstance(fmt, basestring):
        """ both data and dataout must be dict. """
        if not data.has_key(fmt): return
        data_out[fmt] = data.get(fmt, None) if data else None
    elif isinstance(fmt, dict):
        key = fmt.keys()[0]
        if not data.has_key(key): return
        if isinstance(fmt[key], list):
            data_out[key] = []
        else:
            data_out[key] = {}
        _json_filter(data[key], data_out[key], fmt[key])
    elif isinstance(fmt, tuple):
        """ both data and dataout must be dict. """
        if not fmt:
            data_out.update(data)
        for f in fmt:
            _json_filter(data, data_out, f)
    elif isinstance(fmt, list):
        """ both data and dataout must be list as well. """
        fmt_tuple = tuple(fmt)
        for d in data:
            d_out = {}
            _json_filter(d, d_out, fmt_tuple)
            data_out.append(d_out)
    else:
        raise Exception("Invalid data or format!\nfmt=%s\ndata=%s\ndata_out=%s" % (fmt, data, data_out))



