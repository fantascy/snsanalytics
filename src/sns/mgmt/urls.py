from django.conf.urls.defaults import patterns

urlpatterns = patterns('',
    (r'^$', 'sns.mgmt.views.list'),
    (r'^create/$', 'sns.mgmt.views.create'),
    (r'^update/$', 'sns.mgmt.views.update'),
    (r'^delete/$', 'sns.mgmt.views.delete'),
    (r'^confirm/$', 'sns.mgmt.views.confirm'),
    (r'^sync/$', 'sns.mgmt.views.sync'),
    (r'^update_channel_campaign/$', 'sns.mgmt.views.update_channel_campaign'),
    (r'^topic/$', 'sns.mgmt.views.tc_list'),
    (r'^topic/create/$', 'sns.mgmt.views.tc_create'),
    (r'^topic/update/$', 'sns.mgmt.views.tc_update'),
    (r'^topic/delete/$', 'sns.mgmt.views.tc_delete'),
    (r'^topic/activate/$', 'sns.mgmt.views.tc_activate'),
    (r'^topic/nochannel/$', 'sns.mgmt.views.tc_nochannel'),
    (r'^topic/notopic/$', 'sns.mgmt.views.tc_notopic'),
    (r'^topic/nochannel/export/$', 'sns.mgmt.views.tc_nochannel_export'),
    (r'^topic/nochannel/update/$', 'sns.mgmt.views.tc_nochannel_update'),
    
)