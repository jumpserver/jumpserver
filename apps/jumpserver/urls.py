# ~*~ coding: utf-8 ~*~
from __future__ import unicode_literals

from django.conf.urls import url, include
from django.conf import settings
from django.conf.urls.static import static

from rest_framework.schemas import get_schema_view
from rest_framework_swagger.renderers import SwaggerUIRenderer, OpenAPIRenderer

from .views import IndexView, LunaView

schema_view = get_schema_view(title='Users API', renderer_classes=[OpenAPIRenderer, SwaggerUIRenderer])
urlpatterns = [
    url(r'^$', IndexView.as_view(), name='index'),
    url(r'^luna/', LunaView.as_view(), name='luna-error'),
    url(r'^users/', include('users.urls.views_urls', namespace='users')),
    url(r'^assets/', include('assets.urls.views_urls', namespace='assets')),
    url(r'^perms/', include('perms.urls.views_urls', namespace='perms')),
    url(r'^terminal/', include('terminal.urls.views_urls', namespace='terminal')),
    url(r'^ops/', include('ops.urls.view_urls', namespace='ops')),
    url(r'^settings/', include('common.urls.view_urls', namespace='settings')),
    url(r'^common/', include('common.urls.view_urls', namespace='common')),

    # Api url view map
    url(r'^api/users/', include('users.urls.api_urls', namespace='api-users')),
    url(r'^api/assets/', include('assets.urls.api_urls', namespace='api-assets')),
    url(r'^api/perms/', include('perms.urls.api_urls', namespace='api-perms')),
    url(r'^api/terminal/', include('terminal.urls.api_urls', namespace='api-terminal')),
    url(r'^api/ops/', include('ops.urls.api_urls', namespace='api-ops')),
    url(r'^api/common/', include('common.urls.api_urls', namespace='api-common')),

    # External apps url
    url(r'^captcha/', include('captcha.urls')),
]

if settings.DEBUG:
    urlpatterns += [
        url(r'^docs/', schema_view, name="docs"),
    ] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT) \
      + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

