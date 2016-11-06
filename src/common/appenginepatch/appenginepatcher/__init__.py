from google.appengine.api import apiproxy_stub_map
import os, sys

have_appserver = bool(apiproxy_stub_map.apiproxy.GetStub('datastore_v3'))

if have_appserver:
    appid = os.environ.get('APPLICATION_ID')
else:
    try:
        from google.appengine.tools import dev_appserver
        from aecmd import PROJECT_DIR
        appConfig = dev_appserver.LoadAppConfig(PROJECT_DIR, {})
        appid = appConfig[0].application
    except ImportError:
        appid = None

on_production_server = have_appserver and \
    not os.environ.get('SERVER_SOFTWARE', '').lower().startswith('devel')
