# ~*~ coding: utf-8 ~*~
from __future__ import unicode_literals

from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static

from . import views, api

api_v1 = [
    path('index/', api.IndexApi.as_view()),
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
    path('auth/', include('authentication.urls.view_urls'), name='auth'),
    path('ops/', include('ops.urls.view_urls'), name='ops'),
    re_path(r'flower/(?P<path>.*)', views.celery_flower_view, name='flower-view'),
]


if settings.XPACK_ENABLED:
    app_view_patterns.append(
        path('xpack/', include('xpack.urls.view_urls', namespace='xpack'))
    )
    api_v1.append(
        path('xpack/', include('xpack.urls.api_urls', namespace='api-xpack'))
    )


apps = [
    'users', 'assets', 'perms', 'terminal', 'ops', 'audits', 'orgs', 'auth',
    'applications', 'tickets', 'settings', 'xpack'
    'flower', 'luna', 'koko', 'ws', 'docs', 'redocs',
]


urlpatterns = [
    path('', views.IndexView.as_view(), name='index'),
    path('api/v1/', include(api_v1)),
    path('api/v2/', include(api_v2)),
    re_path('api/(?P<app>\w+)/(?P<version>v\d)/.*', views.redirect_format_api),
    path('api/health/', views.HealthCheckView.as_view(), name="health"),
    # External apps url
    path('core/auth/captcha/', include('captcha.urls')),
    path('core/', include(app_view_patterns)),
    path('ui/', views.UIView.as_view())
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT) \
            + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
# urlpatterns += js_i18n_patterns

handler404 = 'jumpserver.views.handler404'
handler500 = 'jumpserver.views.handler500'

if settings.DEBUG:
    urlpatterns += [
        re_path('^api/swagger(?P<format>\.json|\.yaml)$',
                views.get_swagger_view().without_ui(cache_timeout=1), name='schema-json'),
        path('api/docs/', views.get_swagger_view().with_ui('swagger', cache_timeout=1), name="docs"),
        path('api/redoc/', views.get_swagger_view().with_ui('redoc', cache_timeout=1), name='redoc'),

        re_path('^api/v2/swagger(?P<format>\.json|\.yaml)$',
                views.get_swagger_view().without_ui(cache_timeout=1), name='schema-json'),
        path('api/docs/v2/', views.get_swagger_view("v2").with_ui('swagger', cache_timeout=1), name="docs"),
        path('api/redoc/v2/', views.get_swagger_view("v2").with_ui('redoc', cache_timeout=1), name='redoc'),
    ]


# 兼容之前的
old_app_pattern = '|'.join(apps)
old_app_pattern = r'^{}'.format(old_app_pattern)
urlpatterns += [re_path(old_app_pattern, views.redirect_old_apps_view)]


