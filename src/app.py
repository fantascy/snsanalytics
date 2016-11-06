from common.appenginepatch import wsgi
aep_wsgi = wsgi.application

from common.appenginepatch import main_deferred_wsgi
aep_deferred_wsgi = main_deferred_wsgi.application