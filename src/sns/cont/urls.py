from django.conf.urls.defaults import patterns, include

urlpatterns = patterns('',
    (r'^message/', include('sns.cont.message.urls')),
    (r'^rssfeed/', include('sns.cont.feed.urls')),
)