"""
WSGI config for AutoSa project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/1.6/howto/deployment/wsgi/
"""

import os
import sys
sys.path.append('/opt/jumpserver/webroot/AutoSa')
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "AutoSa.settings")

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
