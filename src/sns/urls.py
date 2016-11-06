from django.conf.urls.defaults import patterns, include

from common.view.controllerview import DEFAULT_CONTROLLER_VIEW


urlpatterns = patterns('',
    (r'^aboutus.html', 'django.views.generic.simple.direct_to_template', {'template': 'sns/aboutus.html','extra_context':{'view':DEFAULT_CONTROLLER_VIEW}}),
    (r'^contactus.html', 'django.views.generic.simple.direct_to_template', {'template': 'sns/contactus.html','extra_context':{'view':DEFAULT_CONTROLLER_VIEW}}),
    (r'^joinus.html', 'django.views.generic.simple.direct_to_template', {'template': 'sns/joinus.html','extra_context':{'view':DEFAULT_CONTROLLER_VIEW}}),
    (r'^help.html', 'django.views.generic.simple.direct_to_template', {'template': 'sns/help.html','extra_context':{'view':DEFAULT_CONTROLLER_VIEW}}),
    (r'^terms.html', 'django.views.generic.simple.direct_to_template', {'template': 'sns/terms.html','extra_context':{'view':DEFAULT_CONTROLLER_VIEW}}),
    (r'^privacy.html', 'django.views.generic.simple.direct_to_template', {'template': 'sns/privacy.html','extra_context':{'view':DEFAULT_CONTROLLER_VIEW}}),
    (r'^unsub.html', 'django.views.generic.simple.direct_to_template', {'template': 'sns/unsub.html','extra_context':{'view':DEFAULT_CONTROLLER_VIEW}}),
    (r'^404.html', 'django.views.generic.simple.direct_to_template', {'template': 'sns/404.html','extra_context':{'view':DEFAULT_CONTROLLER_VIEW}}),
    (r'^robots.txt', 'django.views.generic.simple.direct_to_template', {'template': 'sns/robots.txt'}),

    (r'^topic/', include('sns.cont.topic.urls')),
    (r'^femaster/', include('sns.femaster.urls')),
)