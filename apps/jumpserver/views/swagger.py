
from drf_spectacular.views import (
    SpectacularSwaggerView, SpectacularRedocView,
    SpectacularYAMLAPIView, SpectacularJSONAPIView
)
from rest_framework.response import Response
from django.contrib.auth.mixins import LoginRequiredMixin


class SwaggerUI(LoginRequiredMixin, SpectacularSwaggerView):
    pass


class Redoc(LoginRequiredMixin, SpectacularRedocView):
    pass


class SchemeMixin:
    def get(self, request, *args, **kwargs):
        schema = super().get(request, *args, **kwargs).data
        host = request.get_host()
        schema['servers'] = [
            {"url": f"https://{host}", "description": "HTTPS Server"},
            {"url": f"http://{host}", "description": "HTTP Server"},
        ]
        if request.scheme == 'http':
            schema['servers'] = schema['servers'][::-1]

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