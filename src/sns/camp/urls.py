from django.conf.urls.defaults import patterns

urlpatterns = patterns('',
                       
    (r'^$', 'sns.camp.views.list'),
    (r'^create/$', 'sns.camp.views.create'),
    (r'^update/$', 'sns.camp.views.update'),
    (r'^delete/$', 'sns.camp.views.delete'),
    (r'^detail/$', 'sns.camp.views.detail'),
    (r'^activate/$', 'sns.camp.views.activate'),
    (r'^deactivate/$', 'sns.camp.views.deactivate'),
    (r'^test/$', 'sns.camp.views.test'),
)