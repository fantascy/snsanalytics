from django.conf.urls.defaults import patterns

urlpatterns = patterns('',
    (r'^$', 'cake.dashboard.views.home'),                  
)