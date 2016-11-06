from django.conf.urls.defaults import patterns

urlpatterns = patterns('',
#    (r'^$', 'soup.user.views.my_profile'),
    (r'^(?P<uid>\d*)$', 'soup.user.views.profile'),
    (r'^twitter/disconnect/$', 'soup.user.views.twitter_disconnect'),
    (r'^twitter/login/$', 'soup.user.views.twitter_login'),
    (r'^friend/invite/$', 'soup.user.views.friend_invite'),
    (r'^friends/$', 'soup.user.views.friends'),
)