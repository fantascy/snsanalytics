from django.conf.urls.defaults import patterns

urlpatterns = patterns('',
    (r'^$', 'sns.feedbuilder.views.lst'),
    (r'^create/$', 'sns.feedbuilder.views.create'),
    (r'^help/$', 'sns.feedbuilder.views.hlp'),
    (r'^update/$', 'sns.feedbuilder.views.update'),
    (r'^delete/$', 'sns.feedbuilder.views.delete'),

)
