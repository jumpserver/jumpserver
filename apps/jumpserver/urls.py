# ~*~ coding: utf-8 ~*~
from __future__ import unicode_literals

from django.conf.urls import url, include
from django.conf import settings
from django.conf.urls.static import static

from rest_framework.schemas import get_schema_view
from rest_framework_swagger.renderers import SwaggerUIRenderer, OpenAPIRenderer

from .views import IndexView

schema_view = get_schema_view(title='Users API', renderer_classes=[OpenAPIRenderer, SwaggerUIRenderer])
urlpatterns = [
    url(r'^$', IndexView.as_view(), name='index'),
    url(r'^users/', include('users.urls.views_urls', namespace='users')),
    url(r'^assets/', include('assets.urls.views_urls', namespace='assets')),
    url(r'^perms/', include('perms.urls.views_urls', namespace='perms')),
    url(r'^audits/', include('audits.urls.views_urls', namespace='audits')),
    url(r'^applications/', include('applications.urls.views_urls', namespace='applications')),
    url(r'^ops/', include('ops.urls.view_urls', namespace='ops')),

    # Api url view map
    url(r'^api/users/', include('users.urls.api_urls', namespace='api-users')),
    url(r'^api/assets/', include('assets.urls.api_urls', namespace='api-assets')),
    url(r'^api/perms/', include('perms.urls.api_urls', namespace='api-perms')),
    url(r'^api/audits/', include('audits.urls.api_urls', namespace='api-audits')),
    url(r'^api/applications/', include('applications.urls.api_urls', namespace='api-applications')),
    url(r'^api/ops/', include('ops.urls.api_urls', namespace='api-ops')),
    url(r'^captcha/', include('captcha.urls')),

]


if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += [
        url(r'^docs/', schema_view, name="docs"),
    ]

