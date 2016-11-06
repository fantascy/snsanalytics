from django.conf.urls.defaults import patterns

urlpatterns = patterns('',
    (r'^$', 'sns.dashboard.views.home'),                  
    (r'^chart/html5$', 'sns.dashboard.views.homeChartDetailHTML5'),      
)