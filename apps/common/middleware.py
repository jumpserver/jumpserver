from django.conf import settings
from django.utils.deprecation import MiddlewareMixin

from django.http import HttpResponse


class SessionCookieMiddleware(MiddlewareMixin):

    @staticmethod
    def process_response(request, response):
        key = settings.SESSION_COOKIE_NAME_PREFIX_KEY
        value = settings.SESSION_COOKIE_NAME_PREFIX
        if request.COOKIES.get(key) == value:
            return response
        response: HttpResponse
        response.set_cookie(key, value)
        return response
