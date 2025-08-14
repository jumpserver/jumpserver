import os


from drf_spectacular.views import (
    SpectacularSwaggerView, SpectacularRedocView,
    SpectacularYAMLAPIView, SpectacularJSONAPIView
)
from rest_framework import permissions


class SwaggerUI(SpectacularSwaggerView):
    with_auth = os.environ.get('DOC_AUTH', '1') == '1'

    def get_permission_classes(self):
        if self.with_auth:
            return [permissions.IsAuthenticated]
        return []

class Redoc(SpectacularRedocView):
    with_auth = os.environ.get('DOC_AUTH', '1') == '1'
    def get_permission_classes(self):
        if self.with_auth:
            return [permissions.IsAuthenticated]
        return []


def get_swagger_view(ui=None, **kwargs):
    if ui == 'swagger':
        return SwaggerUI.as_view(url_name='schema')
    elif ui == 'redoc':
        return Redoc.as_view(url_name='schema')
    elif ui == 'json':
        return SpectacularJSONAPIView.as_view()
    elif ui == 'yaml':
        return SpectacularYAMLAPIView.as_view()