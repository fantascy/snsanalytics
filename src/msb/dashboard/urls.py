from django.conf.urls.defaults import patterns

urlpatterns = patterns('',
    (r'^$', 'msb.dashboard.views.home'),                  
)