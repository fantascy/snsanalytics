from django.conf.urls.defaults import patterns

urlpatterns = patterns('',
    (r'^$', 'sns.cont.feed.views.feed_list'),
    (r'^create/$', 'sns.cont.feed.views.feed_create'),
    (r'^update/$', 'sns.cont.feed.views.feed_update'),
    (r'^delete/$', 'sns.cont.feed.views.feed_delete'),
    (r'^edit/$', 'sns.cont.feed.views.feed_edit'),
    (r'^custom/$', 'sns.cont.feed.views.feed_custom'),
    (r'^custom/upload/$', 'sns.cont.feed.views.feed_custom_upload'),
    (r'^topic/$', 'sns.cont.feed.views.topic'),
)