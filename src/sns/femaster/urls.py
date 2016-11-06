from django.conf.urls.defaults import patterns

urlpatterns = patterns('',
    (r'^worker_get_tgtflwrs/$', 'sns.femaster.views.worker_get_tgtflwrs'),
    (r'^worker_report_status/$', 'sns.femaster.views.worker_report_status'),
)

