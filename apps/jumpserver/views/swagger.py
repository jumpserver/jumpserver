
from drf_spectacular.views import (
    SpectacularSwaggerView, SpectacularRedocView,
    SpectacularYAMLAPIView, SpectacularJSONAPIView
)
from rest_framework.response import Response
from django.contrib.auth.mixins import LoginRequiredMixin
from common.permissions import IsValidUser


class SwaggerUI(LoginRequiredMixin, SpectacularSwaggerView):
    permission_classes = [IsValidUser]


class Redoc(LoginRequiredMixin, SpectacularRedocView):
    permission_classes = [IsValidUser]


class SchemeMixin:
    permission_classes = [IsValidUser]

    def get(self, request, *args, **kwargs):
        schema = super().get(request, *args, **kwargs).data
        host = request.get_host()
        schema['servers'] = [
            {"url": f"https://{host}", "description": "HTTPS Server"},
            {"url": f"http://{host}", "description": "HTTP Server"},
        ]
        if request.scheme == 'http':
            schema['servers'] = schema['servers'][::-1]

        schema['components']['securitySchemes'] = {
            'Bearer': {
                'type': 'http',
                'scheme': 'bearer',
                'bearerFormat': 'JWT',
            }
        }
        return Response(schema)
    
class JsonApi(SchemeMixin, SpectacularJSONAPIView):
    pass

class YamlApi(SchemeMixin, SpectacularYAMLAPIView):
    pass


def get_swagger_view(ui=None, **kwargs):
    if ui == 'swagger':
        return SwaggerUI.as_view(url_name='schema')
    elif ui == 'redoc':
        return Redoc.as_view(url_name='schema')
    elif ui == 'json':
        return JsonApi.as_view()
    elif ui == 'yaml':
        return YamlApi.as_view()
