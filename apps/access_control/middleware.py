# -*- coding: utf-8 -*-
#
from django.contrib.auth import logout
from django.conf import settings
from django.shortcuts import redirect

from access_control.utils import check_user_policies


class AccessControlMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = request.user
        if user.is_authenticated and not check_user_policies(request.user, request):
            logout(request)
            if settings.AUTH_OPENID:
                return redirect(settings.AUTH_OPENID_AUTH_LOGOUT_URL_NAME)
            else:
                return redirect('authentication:logout')
        response = self.get_response(request)
        return response
