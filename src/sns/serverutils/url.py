import context
from common.utils import url as url_util

from django.template.defaultfilters import urlize

def short_url(url_id):
    return url_util.short_url(context.get_context().short_domain(), url_id) 

def short_url_with_long_domain(url_id):
    return url_util.short_url(context.get_context().long_domain(), url_id) 

def extractUrlsFromText(text):
    
    url_list = []
    
    new_text = urlize(text)
    if not new_text.find('<a href=\"') < 0:
        urls = new_text.split('<a href=\"')
        for url in urls[1:]:
            url = url[0:url.find('\"')]
            if not str(url).startswith("mailto:"):
                url_list.append(url)
    return url_list


