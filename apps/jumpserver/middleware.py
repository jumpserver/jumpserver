# ~*~ coding: utf-8 ~*~

import os
import re
import pytz
from django.utils import timezone
from django.utils.deprecation import MiddlewareMixin
from django.shortcuts import HttpResponse


DEMO_MODE = os.environ.get("DEMO_MODE", "")
SAFE_URL = r'^/users/login|^/api/applications/v1/.*|/api/audits/.*|/api/users/v1/auth/|/api/users/v1/profile/'


class TimezoneMiddleware(MiddlewareMixin):
    def process_request(self, request):
        tzname = request.META.get('TZ')
        if tzname:
            timezone.activate(pytz.timezone(tzname))
        else:
            timezone.deactivate()


class DemoMiddleware(MiddlewareMixin):
    def process_request(self, request):
        if DEMO_MODE and request.method not in ["GET", "HEAD"] and not re.match(SAFE_URL, request.path):
                return HttpResponse("Demo mode, only get request accept", status=403)
