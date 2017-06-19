# ~*~ coding: utf-8 ~*~

import os
import pytz
from django.utils import timezone
from django.utils.deprecation import MiddlewareMixin
from django.shortcuts import HttpResponse


DEMO_MODE = os.environ.get("DEMO_MODE", "")
SAFE_URL = ["/users/login",]


class TimezoneMiddleware(MiddlewareMixin):
    def process_request(self, request):
        tzname = request.META.get('TZ')
        if tzname:
            timezone.activate(pytz.timezone(tzname))
        else:
            timezone.deactivate()


class DemoMiddleware(MiddlewareMixin):
    def process_request(self, request):
        if DEMO_MODE and request.method not in ["GET", "HEAD"] and request.path not in SAFE_URL:
                return HttpResponse("Demo mode, only get request accept", 403)
