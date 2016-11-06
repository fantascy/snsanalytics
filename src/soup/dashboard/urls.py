from django.conf.urls.defaults import patterns

urlpatterns = patterns('',
    (r'^$', 'soup.dashboard.views.home'),                  
)