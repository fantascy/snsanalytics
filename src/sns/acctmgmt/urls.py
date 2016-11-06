from django.conf.urls.defaults import patterns
urlpatterns = patterns('',
    (r'^cmp/upload/$', 'sns.acctmgmt.views.cmp_upload'),
    (r'^cmp/pwdupload/$', 'sns.acctmgmt.views.cmp_pwdupload'),
    (r'^yahoo/$', 'sns.acctmgmt.views.yahoo_list'),
    (r'^yahoo/create/$', 'sns.acctmgmt.views.yahoo_create'),
    (r'^yahoo/delete/$', 'sns.acctmgmt.views.yahoo_delete'),
    (r'^yahoo/update/$', 'sns.acctmgmt.views.yahoo_update'),
    (r'^yahoo/detail/$', 'sns.acctmgmt.views.yahoo_detail'),
)