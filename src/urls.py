# -*- coding: utf-8 -*-
from django.conf.urls.defaults import patterns, include
from django.contrib import admin as django_admin
from common.appenginepatch.ragendja.urlsauto import urlpatterns
from common.appenginepatch.ragendja.auth.urls import urlpatterns as auth_patterns

from common.view.controllerview import DEFAULT_CONTROLLER_VIEW 


django_admin.autodiscover()
handler404 = 'entry.page_not_found'
handler500 = 'ragendja.views.server_error'


common_url = patterns('',
    (r'^$', 'entry.home'),  
    (r'^home$', 'entry.home'),
    (r'^home/$', 'entry.home'),
    ('^api/(.*)', 'facade.route'),
    (r'^callback/twitter/', 'entry.twitter_callback'),
    (r'^callback/facebook/','entry.facebook_callback' ),
    (r'^robots.txt$', 'entry.robot_txt'),
    (r'^favicon.ico$', 'entry.favicon'),
    (r'^login', 'django.views.generic.simple.direct_to_template', {'template': 'login.html', 'extra_context': {'view': DEFAULT_CONTROLLER_VIEW}}),
    (r'^logout', 'django.views.generic.simple.direct_to_template', {'template': 'logout.html', 'extra_context': {'view': DEFAULT_CONTROLLER_VIEW}}),)


sns_url = patterns('',
    (r'^(?P<urlHash>\w*\d\w*)', 'entry.redirect'),
    (r'^sns/', include('sns.urls')),
    (r'^message/', include('sns.cont.message.urls')),
    (r'^log/', include('sns.log.urls')),
    (r'^jobs/', include('sns.job.urls')),
    (r'^rssfeed/', include('sns.cont.feed.urls')),
    (r'^chan/', include('sns.chan.urls')),
    (r'^post/', include('sns.post.urls')),
    (r'^feedbuilder/', include('sns.feedbuilder.urls')),
    (r'^deal/', include('sns.deal.urls')),
    (r'^url/', include('sns.url.urls')),
    (r'^cont/', include('sns.cont.urls')),
    (r'^graph/', include('sns.report.urls')),
    (r'^usr/', include('sns.usr.urls')),
    (r'^dashboard/', include('sns.dashboard.urls')),
    (r'^email/', include('sns.email.urls')),
    (r'^camp/', include('sns.camp.urls')),
    (r'^mgmt/', include('sns.mgmt.urls')),
    (r'^dm/', include('sns.dm.urls')),
    (r'^acctmgmt/', include('sns.acctmgmt.urls')),
    )


fe_url = patterns('',
    (r'^fe/', include('fe.urls')),
    (r'^channel/', include('sns.chan.urls')),
    (r'^user/', include('sns.usr.urls')),
    )


msb_url = patterns('',
    (r'^newsfeed/(?P<q>.*)/$', 'sns.feedbuilder.views.combo_feed'),
    (r'^topicscorefeed/(?P<q>.*)/$', 'sns.feedbuilder.views.topic_score_feed'),
    (r'^troverss/(?P<q>.*)/$', 'sns.feedbuilder.views.trove_feed'),
    (r'^rss/(?P<uri>.*)/$', 'sns.feedbuilder.views.feed'),
    (r'^msb/', include('msb.urls')),
    )


soup_url = patterns('',
    (r'^brew/', include('soup.urls')),
    (r'^soup/(?P<title>.*)$', 'soup.article.views.article_main'),
    (r'^(?P<topic>\w*)/hot/(?P<media>\w*)$', 'soup.topic.views.hot_articles'),
    (r'^(?P<topic>\w*)/top/(?P<media>\w*)/(?P<range>\w*)$', 'soup.topic.views.top_articles'),
    (r'^(?P<topic>\w*)/new/(?P<media>\w*)$', 'soup.topic.views.new_articles'),
    (r'^submit/$', 'soup.dashboard.views.share'),
    (r'^submit/check/$', 'soup.dashboard.views.share_check'),
    (r'^submit/update/$', 'soup.dashboard.views.update'),
    (r'^submit/form/check/$', 'soup.dashboard.views.share_form_check'),
    (r'^submit/confirm/$', 'soup.dashboard.views.share_confirm'),
    (r'^submit/update/confirm/$', 'soup.dashboard.views.update_confirm'),
    (r'^search/$', 'soup.search.views.google_custom_search'),
    (r'^search/topic/$', 'soup.topic.views.topic_search'),
    (r'^profile/', include('soup.user.urls')),
    (r'^settings/$', 'soup.user.views.user_setting'),
    (r'^sitemapindex.xml$', 'soup.sitemap.views.site_map_index'),
    (r'^sitemap/(?P<date>.*)/$', 'soup.sitemap.views.site_map'),
    (r'^(?P<topic>\w*)$', 'soup.topic.views.default_articles'),
    )


cake_url = patterns('',
    (r'^cake/', include('cake.urls')),
    (r'^share/(?P<title>.*)$', 'cake.article.views.article_main'),
    (r'^r/(?P<title>.*)$', 'cake.article.views.article_main'),
    (r'^topic/(?P<topic>\w*)/$', 'cake.topic.views.next_hot_article'),
    )


appspot_url = patterns('',
    )


urlpatterns = auth_patterns + common_url + sns_url + fe_url + msb_url + soup_url + cake_url + urlpatterns
