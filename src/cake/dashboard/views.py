from django.views.generic.simple import direct_to_template

from sns.cont.models import Topic
from cake.topic.views import next_hot_article
            
    
def home(request):
    return next_hot_article(request, Topic.TOPIC_KEY_FRONTPAGE)
    
    
def login(request):
    return direct_to_template(request,'cake/login.html')
    
    
