import datetime

from common.utils import string as str_util
from client.common.filehandler import JsonlinesHandler 


class HarkJsonlinesHandler(JsonlinesHandler):
    def transform(self, lines):
        objs = []
        for line in lines:
            valid_line = False
            try:
                line = eval(line)
                url = line.get('url', None)
                title = self._get_value(line, 'title')
                keywords = self._get_keywords(line)
                description = self._get_value(line, 'description')
                publish_date = self._get_publish_date(line)
                if url and title and keywords and publish_date:
                    objs.append({
                                 'url': url, 
                                 'title': title, 
                                 'keywords': keywords,
                                 'publish_date': publish_date,
                                 'description': description, 
                                 })
                    valid_line = True
            except:
                pass
            if not valid_line:
                self.bad_count += 1
        return objs
            
    def _get_keywords(self, line):
        try:
            value = self._get_value(line, 'keywords')
            if value:
                keywords = value.split(',')
                return [str_util.strip(keyword) for keyword in keywords]
        except:
            pass
        return None
             
    def _get_value(self, line, attr):
        try:
            value = line.get(attr, None)
            if value and isinstance(value, list):
                value = value[0]
            value = str_util.strip(value)
            if value:
                return value
        except:
            pass
        return None

    def _get_publish_date(self, line):
        try:
            date_str = self._get_value(line, 'uploadDate')
            return datetime.datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%SZ")
        except:
            return None

            
