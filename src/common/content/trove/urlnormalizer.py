from common.utils import url as url_util


def _url_normalizer_mercurynews(url):
    return "%s?source=rss" % url_util.remove_all_params(url)

def _url_normalizer_bbc(url):
    full_domain = url_util.full_domain(url)
    if full_domain == 'www.bbc.com' or full_domain == 'bbc.com':
        return url.replace('bbc.com', 'bbc.co.uk', 1)    
    else:
        return url

def _url_normalizer_default(url):
    return url_util.remove_all_params(url) if url else url


NORMALIZER_MAP = {
    'mercurynews.com': _url_normalizer_mercurynews,
    'bbc.com': _url_normalizer_bbc,
                  }

def normalize(url):
    url = url_util.sanitize_url(url)
    url = url_util.normalize_url(url)
    root_domain = url_util.root_domain(url)
    normalizer = NORMALIZER_MAP.get(root_domain, _url_normalizer_default)
    return normalizer(url) if normalizer else url

