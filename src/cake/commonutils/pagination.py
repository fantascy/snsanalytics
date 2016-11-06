import urllib

def get_path(request):
    path = request.path
    request_p = {}
    for key in request.GET.keys():
        if key != 'page':
            request_p[key] = request.GET[key]
    if len(request_p) > 0 :
        path = path + '?' +urllib.urlencode(request_p)
    return path

def get_page_numbers(request,paginate_by,count):
    page = int(request.GET.get('page',1))
    page_numbers = []
    for i in range(page-5, page+5):
        if i > 0 and (i-1)*paginate_by< count:
            page_numbers.append(i)
    return page_numbers