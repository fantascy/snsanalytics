from django.conf.urls.defaults import patterns

urlpatterns = patterns('',
    (r'^$', 'sns.cont.topic.views.topic_list'),
    (r'^list/$', 'sns.cont.topic.views.topic_list'),
    (r'^create/$', 'sns.cont.topic.views.topic_create'),
    (r'^update/$', 'sns.cont.topic.views.topic_update'),
    (r'^delete/$', 'sns.cont.topic.views.topic_delete'),
    (r'^upload/$', 'sns.cont.topic.views.topic_upload'),
    (r'^validate/$', 'sns.cont.topic.views.topic_upload_validate'),
    (r'^export/$', 'sns.cont.topic.views.topic_export'),
    (r'^exportlevel/$', 'sns.cont.topic.views.topic_level_export'),
    (r'^cache/$', 'sns.cont.topic.views.topic_cache_refresh'),
)