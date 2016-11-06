from django.conf.urls.defaults import patterns

urlpatterns = patterns('',
    (r'^$', 'sns.cont.message.views.list'),
    (r'^create/$', 'sns.cont.message.views.create'),
    (r'^update/$', 'sns.cont.message.views.update'),
    (r'^delete/$', 'sns.cont.message.views.delete'),
    

)