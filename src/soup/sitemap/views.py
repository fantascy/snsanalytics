from django.http import HttpResponse
from soup import consts as soup_const
from sns.url.models import SiteMap

def site_map_index(request):
    siteMapIndex = SiteMap.get_index()
    content = soup_const.SITE_MAP_INDEX_HEADER + siteMapIndex.content + '</sitemapindex>'
    return HttpResponse(content=content,mimetype='text/xml')
    

def site_map(request,date):
    siteMap = SiteMap.get_by_key_name(SiteMap.keyName(date))
    if siteMap is None :
        return HttpResponse(status=404)
    if siteMap.content is None :
        siteMap.content = ''
    content = soup_const.SITE_MAP_HEADER + siteMap.content + '</urlset>'
    return HttpResponse(content=content,mimetype='text/xml')
