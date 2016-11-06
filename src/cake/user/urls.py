from django.conf.urls.defaults import patterns

urlpatterns = patterns('',
    (r'^feedback/$', 'cake.user.views.feedback'),
)