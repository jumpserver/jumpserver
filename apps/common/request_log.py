from django.http.request import HttpRequest
from django.http.response import HttpResponse

from orgs.utils import current_org


class RequestLogMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request: HttpRequest):
        print(f'Request {request.method} --> ', request.get_raw_uri())
        response: HttpResponse = self.get_response(request)
        print(f'Response {current_org.name} {request.method} {response.status_code} --> ', request.get_raw_uri())
        return response
