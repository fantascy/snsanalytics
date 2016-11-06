from django.http import HttpResponse
import json
from sns.core.core import get_user_id,UserUrlClickParent
from sns.post.models import SPost
from sns.url.models import GlobalShortUrl


def surlSearch(request):
    keyword=request.GET.get('keyword','')
    keyword = keyword.strip()
    result=[]
    if keyword=='':
        pass
    else:
        urlHash = keyword
        globalShortUrl = GlobalShortUrl.get_by_surl(urlHash)
        if globalShortUrl is not None:
            post = SPost.get_by_key_name(SPost.keyName(urlHash), globalShortUrl.campaignParent)        
            if post is not None:
                result.append(keyword)
    data = json.dumps(dict(result=result), indent=4)
    return HttpResponse(data, mimetype='application/javascript') 

