# -*- coding: utf-8 -*-
from rest_framework.throttling import SimpleRateThrottle


class RateThrottle(SimpleRateThrottle):

    def __init__(self):
        # Override the usual SimpleRateThrottle, because we can't determine
        # the rate until called by the view.
        pass

    def allow_request(self, request, view):
        if getattr(request, "user", None) and request.user.is_authenticated:
            if getattr(request.user, "is_service_account", False):
                self.scope = "service_account"
            else:
                self.scope = "user"
        else:
            self.scope = "anon"

        self.rate = self.get_rate()
        self.num_requests, self.duration = self.parse_rate(self.rate)
        return super().allow_request(request, view)

    def get_cache_key(self, request, view):
        if request.user and request.user.is_authenticated:
            ident = request.user.pk
        else:
            ident = self.get_ident(request)

        return self.cache_format % {
            'scope': self.scope,
            'ident': ident
        }
