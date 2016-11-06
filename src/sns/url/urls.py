from django.conf.urls.defaults import patterns

urlpatterns = patterns('',
    (r'^website/list/$', 'sns.url.views.website_list'),
    (r'^website/create/$', 'sns.url.views.website_create'),
    (r'^website/update/$', 'sns.url.views.website_update'),
    (r'^website/delete/$', 'sns.url.views.website_delete'),
    (r'^website/upload/$', 'sns.url.views.website_upload'),
    (r'^website/export/$', 'sns.url.views.website_export'),
    (r'^globalurl/(?P<url>.*)$', 'sns.url.views.global_url_get'),
    (r'^globalurlcounter/(?P<url>.*)$', 'sns.url.views.global_url_counter_get'),
)