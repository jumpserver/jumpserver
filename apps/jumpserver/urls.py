# ~*~ coding: utf-8 ~*~
from __future__ import unicode_literals
import re

from django.conf.urls import url, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework.response import Response
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
from django.utils.encoding import iri_to_uri
from rest_framework import permissions

# from rest_framework.schemas import get_schema_view
# from rest_framework_swagger.renderers import SwaggerUIRenderer, OpenAPIRenderer
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

from .views import IndexView, LunaView

# schema_view = get_schema_view(title='Users API', renderer_classes=[OpenAPIRenderer, SwaggerUIRenderer])
schema_view = get_schema_view(
   openapi.Info(
      title="Snippets API",
      default_version='v1',
      description="Test description",
      terms_of_service="https://www.google.com/policies/terms/",
      contact=openapi.Contact(email="contact@snippets.local"),
      license=openapi.License(name="BSD License"),
   ),
   public=True,
   permission_classes=(permissions.AllowAny,),
)
api_url_pattern = re.compile(r'^/api/(?P<version>\w+)/(?P<app>\w+)/(?P<extra>.*)$')


class HttpResponseTemporaryRedirect(HttpResponse):
    status_code = 307

    def __init__(self, redirect_to):
        HttpResponse.__init__(self)
        self['Location'] = iri_to_uri(redirect_to)


@csrf_exempt
def redirect_format_api(request, *args, **kwargs):
    path, query = request.path, request.GET.urlencode()
    matched = api_url_pattern.match(path)
    if matched:
        version, app, extra = matched.groups()
        path = '/api/{app}/{version}/{extra}?{query}'.format(**{
            "app": app, "version": version, "extra": extra,
            "query": query
        })
        return HttpResponseTemporaryRedirect(path)
    else:
        return Response({"msg": "Redirect url failed: {}".format(path)}, status=404)


v1_api_patterns = [
    url(r'^users/v1/', include('users.urls.api_urls', namespace='api-users')),
    url(r'^assets/v1/', include('assets.urls.api_urls', namespace='api-assets')),
    url(r'^perms/v1/', include('perms.urls.api_urls', namespace='api-perms')),
    url(r'^terminal/v1/', include('terminal.urls.api_urls', namespace='api-terminal')),
    url(r'^ops/v1/', include('ops.urls.api_urls', namespace='api-ops')),
    url(r'^audits/v1/', include('audits.urls.api_urls', namespace='api-audits')),
    url(r'^orgs/v1/', include('orgs.urls.api_urls', namespace='api-orgs')),
    url(r'^common/v1/', include('common.urls.api_urls', namespace='api-common')),
]

app_view_patterns = [
    url(r'^users/', include('users.urls.views_urls', namespace='users')),
    url(r'^assets/', include('assets.urls.views_urls', namespace='assets')),
    url(r'^perms/', include('perms.urls.views_urls', namespace='perms')),
    url(r'^terminal/', include('terminal.urls.views_urls', namespace='terminal')),
    url(r'^ops/', include('ops.urls.view_urls', namespace='ops')),
    url(r'^audits/', include('audits.urls.view_urls', namespace='audits')),
    url(r'^orgs/', include('orgs.urls.views_urls', namespace='orgs')),
]


urlpatterns = [
    url(r'^$', IndexView.as_view(), name='index'),
    url(r'^luna/', LunaView.as_view(), name='luna-error'),
    url(r'^settings/', include('common.urls.view_urls', namespace='settings')),
    url(r'^common/', include('common.urls.view_urls', namespace='common')),
    url(r'^api/v1/.*', redirect_format_api),
    url(r'^api/', include(v1_api_patterns)),

    # Api url view map
    # External apps url
    url(r'^captcha/', include('captcha.urls')),
]
urlpatterns += app_view_patterns
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT) \
            + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

if settings.DEBUG:
    urlpatterns += [
        url(r'^swagger(?P<format>\.json|\.yaml)$', schema_view.without_ui(cache_timeout=None), name='schema-json'),
        url(r'^docs/', schema_view.with_ui('swagger', cache_timeout=None), name="docs"),
        url(r'^redoc/$', schema_view.with_ui('redoc', cache_timeout=None), name='redoc'),
    ]
