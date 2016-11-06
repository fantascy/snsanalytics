from django.conf.urls.defaults import patterns, include

urlpatterns = patterns('',
    (r'^$', 'cake.dashboard.views.home'),
    (r'^click/$', 'cake.article.views.article_click'),
    (r'^login/$', 'cake.dashboard.views.login'),
    (r'^topic/find/$', 'cake.topic.views.topic_find'),
    (r'^corp/tos$', 'cake.corp.views.tos'),
    (r'^robots.txt', 'django.views.generic.simple.direct_to_template', {'template':'cake/robots.txt', 'mimetype':'text/plain'}),
    (r'^user/', include('cake.user.urls')),
)