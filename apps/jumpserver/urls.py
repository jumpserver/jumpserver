# ~*~ coding: utf-8 ~*~
from __future__ import unicode_literals

from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from django.conf.urls.i18n import i18n_patterns
from django.views.i18n import JavaScriptCatalog

from . import views

api_v1 = [
    path('users/', include('users.urls.api_urls', namespace='api-users')),
    path('assets/', include('assets.urls.api_urls', namespace='api-assets')),
    path('perms/', include('perms.urls.api_urls', namespace='api-perms')),
    path('terminal/', include('terminal.urls.api_urls', namespace='api-terminal')),
    path('ops/', include('ops.urls.api_urls', namespace='api-ops')),
    path('audits/', include('audits.urls.api_urls', namespace='api-audits')),
    path('orgs/', include('orgs.urls.api_urls', namespace='api-orgs')),
    path('settings/', include('settings.urls.api_urls', namespace='api-settings')),
    path('authentication/', include('authentication.urls.api_urls', namespace='api-auth')),
    path('common/', include('common.urls.api_urls', namespace='api-common')),
    path('applications/', include('applications.urls.api_urls', namespace='api-applications')),
    path('tickets/', include('tickets.urls.api_urls', namespace='api-tickets')),
]

api_v2 = [
    path('terminal/', include('terminal.urls.api_urls_v2', namespace='api-terminal-v2')),
    path('users/', include('users.urls.api_urls_v2', namespace='api-users-v2')),
]


app_view_patterns = [
    path('users/', include('users.urls.views_urls', namespace='users')),
    path('assets/', include('assets.urls.views_urls', namespace='assets')),
    path('perms/', include('perms.urls.views_urls', namespace='perms')),
    path('terminal/', include('terminal.urls.views_urls', namespace='terminal')),
    path('ops/', include('ops.urls.view_urls', namespace='ops')),
    path('audits/', include('audits.urls.view_urls', namespace='audits')),
    path('orgs/', include('orgs.urls.views_urls', namespace='orgs')),
    path('auth/', include('authentication.urls.view_urls'), name='auth'),
    path('applications/', include('applications.urls.views_urls', namespace='applications')),
    path('tickets/', include('tickets.urls.views_urls', namespace='tickets')),
    re_path(r'flower/(?P<path>.*)', views.celery_flower_view, name='flower-view'),
]


if settings.XPACK_ENABLED:
    app_view_patterns.append(
        path('xpack/', include('xpack.urls.view_urls', namespace='xpack'))
    )
    api_v1.append(
        path('xpack/', include('xpack.urls.api_urls', namespace='api-xpack'))
    )

js_i18n_patterns = i18n_patterns(
    path('jsi18n/', JavaScriptCatalog.as_view(), name='javascript-catalog'),
)


urlpatterns = [
    path('', views.IndexView.as_view(), name='index'),
    path('api/v1/', include(api_v1)),
    path('api/v2/', include(api_v2)),
    re_path('api/(?P<app>\w+)/(?P<version>v\d)/.*', views.redirect_format_api),
    path('api/health/', views.HealthCheckView.as_view(), name="health"),
    re_path('luna/.*', views.LunaView.as_view(), name='luna-view'),
    re_path('koko/.*', views.KokoView.as_view(), name='koko-view'),
    re_path('ws/.*', views.WsView.as_view(), name='ws-view'),
    path('i18n/<str:lang>/', views.I18NView.as_view(), name='i18n-switch'),
    path('settings/', include('settings.urls.view_urls', namespace='settings')),

    # External apps url
    path('captcha/', include('captcha.urls')),
]

urlpatterns += app_view_patterns
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT) \
            + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
urlpatterns += js_i18n_patterns

handler404 = 'jumpserver.views.handler404'
handler500 = 'jumpserver.views.handler500'

if settings.DEBUG:
    urlpatterns += [
        re_path('^swagger(?P<format>\.json|\.yaml)$',
                views.get_swagger_view().without_ui(cache_timeout=1), name='schema-json'),
        path('docs/', views.get_swagger_view().with_ui('swagger', cache_timeout=1), name="docs"),
        path('redoc/', views.get_swagger_view().with_ui('redoc', cache_timeout=1), name='redoc'),

        re_path('^v2/swagger(?P<format>\.json|\.yaml)$',
                views.get_swagger_view().without_ui(cache_timeout=1), name='schema-json'),
        path('docs/v2/', views.get_swagger_view("v2").with_ui('swagger', cache_timeout=1), name="docs"),
        path('redoc/v2/', views.get_swagger_view("v2").with_ui('redoc', cache_timeout=1), name='redoc'),
    ]

