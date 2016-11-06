# -*- coding: utf-8 -*-
import os, sys

# Add current folder to sys.path, so we can import aecmd.
# App Engine causes main.py to be reloaded if an exception gets raised
# on the first request of a main.py instance, so don't add current_dir multiple
# times.
current_dir = os.path.abspath(os.path.dirname(__file__))
if current_dir not in sys.path:
    sys.path = [current_dir] + sys.path

import aecmd
aecmd.setup_project()

from appenginepatcher.patch import patch_all, setup_logging
patch_all()

import django.core.handlers.wsgi
from google.appengine.ext.webapp import util
from django.conf import settings

global path_backup
try:
    sys.path = path_backup[:]
except:
    path_backup = sys.path[:]
os.environ.update(aecmd.env_ext)
setup_logging()

# Create a Django application for WSGI.
application = django.core.handlers.wsgi.WSGIHandler()
