# ~*~ coding: utf-8 ~*~
from __future__ import unicode_literals
import re
import os

from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from rest_framework.response import Response
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
from django.utils.encoding import iri_to_uri
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

from .views import IndexView, LunaView

schema_view = get_schema_view(
   openapi.Info(
      title="Jumpserver API Docs",
      default_version='v1',
      description="Jumpserver Restful api docs",
      terms_of_service="https://www.jumpserver.org",
      contact=openapi.Contact(email="support@fit2cloud.com"),
      license=openapi.License(name="GPLv2 License"),
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
    _path, query = request.path, request.GET.urlencode()
    matched = api_url_pattern.match(_path)
    if matched:
        version, app, extra = matched.groups()
        _path = '/api/{app}/{version}/{extra}?{query}'.format(**{
            "app": app, "version": version, "extra": extra,
            "query": query
        })
        return HttpResponseTemporaryRedirect(_path)
    else:
        return Response({"msg": "Redirect url failed: {}".format(_path)}, status=404)


v1_api_patterns = [
    path('users/v1/', include('users.urls.api_urls', namespace='api-users')),
    path('assets/v1/', include('assets.urls.api_urls', namespace='api-assets')),
    path('perms/v1/', include('perms.urls.api_urls', namespace='api-perms')),
    path('terminal/v1/', include('terminal.urls.api_urls', namespace='api-terminal')),
    path('ops/v1/', include('ops.urls.api_urls', namespace='api-ops')),
    path('audits/v1/', include('audits.urls.api_urls', namespace='api-audits')),
    path('orgs/v1/', include('orgs.urls.api_urls', namespace='api-orgs')),
    path('common/v1/', include('common.urls.api_urls', namespace='api-common')),
]

app_view_patterns = [
    path('users/', include('users.urls.views_urls', namespace='users')),
    path('assets/', include('assets.urls.views_urls', namespace='assets')),
    path('perms/', include('perms.urls.views_urls', namespace='perms')),
    path('terminal/', include('terminal.urls.views_urls', namespace='terminal')),
    path('ops/', include('ops.urls.view_urls', namespace='ops')),
    path('audits/', include('audits.urls.view_urls', namespace='audits')),
    path('orgs/', include('orgs.urls.views_urls', namespace='orgs')),
]

if settings.XPACK_ENABLED:
    app_view_patterns.append(path('xpack/', include('xpack.urls', namespace='xpack')))


urlpatterns = [
    path('', IndexView.as_view(), name='index'),
    path('luna/', LunaView.as_view(), name='luna-error'),
    path('settings/', include('common.urls.view_urls', namespace='settings')),
    path('common/', include('common.urls.view_urls', namespace='common')),
    path('api/v1/', redirect_format_api),
    path('api/', include(v1_api_patterns)),

    # External apps url
    path('captcha/', include('captcha.urls')),
]
urlpatterns += app_view_patterns
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT) \
            + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

if settings.DEBUG:
    urlpatterns += [
        re_path('swagger(?P<format>\.json|\.yaml)$', schema_view.without_ui(cache_timeout=None), name='schema-json'),
        path('docs/', schema_view.with_ui('swagger', cache_timeout=None), name="docs"),
        path('redoc/', schema_view.with_ui('redoc', cache_timeout=None), name='redoc'),
    ]
