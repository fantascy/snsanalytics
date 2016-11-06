from django.conf.urls.defaults import *

urlpatterns = patterns('',
    (r'^$', 'fe.dashboard.views.home'),
    (r'^follow/', include('fe.follow.urls')),
)