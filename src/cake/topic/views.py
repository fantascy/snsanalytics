from django.http import HttpResponseRedirect
from django.http import HttpResponse
import context
from sns.core import core as db_core
from sns.cont.models import Topic
from cake import consts as cake_const
from cake.topic import api as cake_topic_api 
from cake.view.controllerview import ControllerView


def next_hot_article(request, topic):
    context.get_context().set_login_required(False)
    topicKey = topic
    articles = cake_topic_api.get_hot_articles(topicKey, cake_const.MEDIA_TYPE_ALL)
    for article in articles :
        globalUrlCounter = db_core.normalize_2_model(article)
        if globalUrlCounter is None :
            continue
        globalUrl = globalUrlCounter.globalUrl()
        if globalUrl is None :
            continue
        return HttpResponseRedirect(ControllerView.frame_page_url_by_title_key(globalUrl.titleKey, topicKey).encode('utf-8'))
    if topicKey == Topic.cake_frontpage_topic().keyNameStrip():
        return ControllerView.page_not_found()
    else : 
        return HttpResponseRedirect('/') 


def topic_find(request):
    name = request.REQUEST.get('name','') 
    topic = Topic.all().filter('name',name)[0]
    return HttpResponse(topic.keyNameStrip())
        
