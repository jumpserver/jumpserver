# ~*~ coding: utf-8 ~*~
from __future__ import unicode_literals

from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from django.views.i18n import JavaScriptCatalog

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
    path('prometheus/metrics/', api.PrometheusMetricsApi.as_view())
]

app_view_patterns = [
    path('auth/', include('authentication.urls.view_urls'), name='auth'),
    path('ops/', include('ops.urls.view_urls'), name='ops'),
    re_path(r'flower/(?P<path>.*)', views.celery_flower_view, name='flower-view'),
]

if settings.XPACK_ENABLED:
    api_v1.append(
        path('xpack/', include('xpack.urls.api_urls', namespace='api-xpack'))
    )


apps = [
    'users', 'assets', 'perms', 'terminal', 'ops', 'audits', 'orgs', 'auth',
    'applications', 'tickets', 'settings', 'xpack',
    'flower', 'luna', 'koko', 'ws', 'docs', 'redocs',
]

urlpatterns = [
    path('', views.IndexView.as_view(), name='index'),
    path('api/v1/', include(api_v1)),
    re_path('api/(?P<app>\w+)/(?P<version>v\d)/.*', views.redirect_format_api),
    path('api/health/', views.HealthCheckView.as_view(), name="health"),
    # External apps url
    path('core/auth/captcha/', include('captcha.urls')),
    path('core/', include(app_view_patterns)),
    path('ui/', views.UIView.as_view()),
]

# 静态文件处理路由
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT) \
            + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

# js i18n 路由文件
urlpatterns += [
    path('core/jsi18n/', JavaScriptCatalog.as_view(), name='javascript-catalog'),
]

# docs 路由
urlpatterns += [
    re_path('^api/swagger(?P<format>\.json|\.yaml)$',
            views.get_swagger_view().without_ui(cache_timeout=1), name='schema-json'),
    re_path('api/docs/?', views.get_swagger_view().with_ui('swagger', cache_timeout=1), name="docs"),
    re_path('api/redoc/?', views.get_swagger_view().with_ui('redoc', cache_timeout=1), name='redoc'),
]


# 兼容之前的
old_app_pattern = '|'.join(apps)
old_app_pattern = r'^{}'.format(old_app_pattern)
urlpatterns += [re_path(old_app_pattern, views.redirect_old_apps_view)]


handler404 = 'jumpserver.views.handler404'
handler500 = 'jumpserver.views.handler500'
