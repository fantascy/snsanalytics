from django.conf.urls.defaults import patterns

urlpatterns = patterns('',
    (r'^$', 'sns.deal.views.deal_list'),
    (r'^create/$', 'sns.deal.views.deal_create'),
    (r'^update/$', 'sns.deal.views.deal_update'),
    (r'^delete/$', 'sns.deal.views.deal_delete'),
    (r'^stats/$', 'sns.deal.views.deal_stats'),
    (r'^rss/(?P<location>.*)/(?P<cat>.*)/mobile/$', 'sns.deal.views.deal_rss_location_cat_mobile'),
    (r'^rss/(?P<location>.*)/mobile/$', 'sns.deal.views.deal_rss_location_mobile'),
    (r'^rss/(?P<location>.*)/(?P<cat>.*)/$', 'sns.deal.views.deal_rss_location_cat'),
    (r'^rss/(?P<location>.*)/$', 'sns.deal.views.deal_rss_location'),
    
)
