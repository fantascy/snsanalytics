from django.conf.urls.defaults import patterns

urlpatterns = patterns('',
    #(r'^$', 'sns.email.views.list'),
    (r'^list/$', 'sns.email.views.list'),
    (r'^list/create/$', 'sns.email.views.create'),
    (r'^list/update/$', 'sns.email.views.update'),
    (r'^list/delete/$', 'sns.email.views.delete'),
    (r'^list/export/$', 'sns.email.views.export'),
    (r'^list/importFromCSV/$', 'sns.email.views.importFromCSV'),
    
    (r'^contact/$', 'sns.email.views.contact_list'),
    #(r'^contact/list/$', 'sns.email.views.contact_list'),
    (r'^contact/create/$', 'sns.email.views.contact_create'),
    (r'^contact/update/$', 'sns.email.views.contact_update'),
    (r'^contact/delete/$', 'sns.email.views.contact_delete'),
    
    (r'^template/$', 'sns.email.views.template_list'),
    #(r'^template/list$', 'sns.email.views.template_list'),
    (r'^template/create/$', 'sns.email.views.template_create'),
    (r'^template/update/$', 'sns.email.views.template_update'),
    (r'^template/delete/$', 'sns.email.views.template_delete'),
    (r'^template/send/$', 'sns.email.views.template_send'),
    
    
    (r'^campaign/$', 'sns.email.views.campaign_list'),
    (r'^campaign/list$', 'sns.email.views.campaign_list'),
    (r'^campaign/create/$', 'sns.email.views.campaign_create'),
    (r'^campaign/update/$', 'sns.email.views.campaign_update'),
    (r'^campaign/delete/$', 'sns.email.views.campaign_delete'),
    (r'^campaign/detail/(.*)$', 'sns.email.views.campaign_detail'),
    (r'^campaign/activate/$', 'sns.email.views.activate'),
    (r'^campaign/deactivate/$', 'sns.email.views.deactivate'),
    (r'^campaign/record/$', 'sns.email.views.record'),
    (r'^campaign/test$', 'sns.email.views.test'),
    
    (r'^unsub/$', 'sns.email.views.unsubscribe'),
    
)