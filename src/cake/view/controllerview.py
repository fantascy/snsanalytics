from django.views.defaults import page_not_found as django_page_not_found

import deploycake
import context
from common.view.controllerview import ControllerView as CommonControllerView
from sns.cont.models import Topic
from sns.cont.topic.api import TopicCacheMgr
from soup.view import controllerview as soup_controllerview
from cake import consts as cake_const
from cake.user import consts as user_const


class ControllerView(CommonControllerView):
    def __init__(self):
        CommonControllerView.__init__(self)
        self.const = cake_const
        self.userConst = user_const
    
    def name(self):
        return "Home"
    
    def topicNames(self):
        return TopicCacheMgr.get_all_topic_names()
    
    def articleRoot(self):
        return ControllerView.article_root() 
    
    @classmethod         
    def article_root(cls):
        return 'share'
        
    @classmethod         
    def page_not_found(cls):
        return django_page_not_found(context.get_context().request(), template_name="cake/404.html")

    @classmethod
    def no_image_url(cls):
        import settings 
        return "%scake/images/no_image.png" % settings.MEDIA_URL
     
    @classmethod
    def frame_page_url_by_title_key(cls, url_title_key, topic=None):
        url = "http://%s/r/%s" % (context.get_context().long_domain(app_deploy=deploycake), url_title_key.encode("utf-8"))
        if topic is not None :
            url = "%s?topic=%s" % (url.decode('utf-8'), topic.decode('utf-8'))
        return url

    @classmethod         
    def defaultPageTitle(cls):
        return Topic.cake_frontpage_topic().description

    def pageTitle(self):
        return ControllerView.defaultPageTitle()

    def pageDescription(self):
        return None

    def _keywords(self):
        return ["RippleOne", "Socially Curated"]

    def keywords(self):
        return ','.join(self._keywords())


class ArticleInfo(soup_controllerview.ArticleInfo):
    def __init__(self, globalUrlCounter, globalUrl=None, userRating=None) :
        soup_controllerview.ArticleInfo.__init__(self, globalUrlCounter, globalUrl, userRating)

    def articleRoot(self):
        return ControllerView.article_root() 
        

class ContentView(ControllerView):
    def __init__(self):
        context.get_context().set_login_required(False)
        ControllerView.__init__(self)
        
    def name(self):
        return Topic.cake_frontpage_topic().name
    
    
