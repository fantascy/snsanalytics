from django.conf.urls.defaults import patterns

urlpatterns = patterns('',
    (r'^$', 'msb.dashboard.views.home'),
    (r'^robots.txt', 'django.views.generic.simple.direct_to_template', {'template':'msb/robots.txt', 'mimetype':'text/plain'}),
)