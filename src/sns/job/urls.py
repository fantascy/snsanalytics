from django.conf.urls.defaults import patterns

from common.view.controllerview import DEFAULT_CONTROLLER_VIEW


urlpatterns = patterns('',
    (r'^senior_designer.html', 'django.views.generic.simple.direct_to_template', {'template': 'sns/job/senior_designer.html','extra_context':{'view':DEFAULT_CONTROLLER_VIEW}}),
    (r'^senior_ux_designer.html', 'django.views.generic.simple.direct_to_template', {'template': 'sns/job/senior_ux_designer.html','extra_context':{'view':DEFAULT_CONTROLLER_VIEW}}),
    (r'^designer_first_class.html', 'django.views.generic.simple.direct_to_template', {'template': 'sns/job/designer_first_class.html','extra_context':{'view':DEFAULT_CONTROLLER_VIEW}}),
    (r'^shoe_designer.html', 'django.views.generic.simple.direct_to_template', {'template': 'sns/job/shoe_designer.html','extra_context':{'view':DEFAULT_CONTROLLER_VIEW}}),
    (r'^graphic_designer.html', 'django.views.generic.simple.direct_to_template', {'template': 'sns/job/graphic_designer.html','extra_context':{'view':DEFAULT_CONTROLLER_VIEW}}),
)