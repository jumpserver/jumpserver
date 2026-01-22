from django.core.handlers.asgi import ASGIRequest

from routing.discover import Route
from routing.resolver import View
from schema.endpoint import Endpoint, MethodSchema


class BaseExtractor:

    def __init__(self, view: View):
        self.view = view
        self.fake_request = self.get_fake_request()
    
    def get_fake_request(self) -> ASGIRequest:
        scope = {
            'type': 'http',
            'method': 'GET',
            'path': '/',
            'query_string': b'',
            'headers': [],
        }
        async def receive():
            return {'type': 'http.request', 'body': b''}
        fake_request = ASGIRequest(scope, receive)
        setattr(fake_request, 'query_params', {})
        return fake_request

    def extract(self) -> Endpoint:
        url = self.view.route.path
        endpoint = Endpoint(
            path=self.view.route.path, 
            requires_auth=self.view_requires_auth()
        )
        methods = self.get_http_methods()
        for method in methods:
            query_fields = self.extract_query_fields(method)
            body_fields = self.extract_body_fields(method)
            method_schema = MethodSchema(
                method=method, 
                query_fields=query_fields, 
                body_fields=body_fields,
            )
            endpoint.methods[method] = method_schema
        return endpoint

    def get_http_methods(self) -> list:
        return ['GET', 'POST']
    
    def view_requires_auth(self) -> bool:
        return False
    
    def extract_query_fields(self, method: str) -> list:
        return []

    def extract_body_fields(self, method: str) -> list:
        return []
    