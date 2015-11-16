from django.conf.urls import patterns, include, url


urlpatterns = patterns('',
    # Examples:
    (r'^$', 'jumpserver.views.index'),
    (r'^api/user/$', 'jumpserver.api.api_user'),
    (r'^skin_config/$', 'jumpserver.views.skin_config'),
    (r'^install/$', 'jumpserver.views.install'),
    (r'^base/$', 'jumpserver.views.base'),
    (r'^login/$', 'jumpserver.views.Login'),
    (r'^logout/$', 'jumpserver.views.Logout'),
    (r'^file/upload/$', 'jumpserver.views.upload'),
    (r'^file/download/$', 'jumpserver.views.download'),
    (r'^setting', 'jumpserver.views.setting'),
    (r'^error/$', 'jumpserver.views.httperror'),
    (r'^juser/', include('juser.urls')),
    (r'^jasset/', include('jasset.urls')),
    (r'^jlog/', include('jlog.urls')),
    (r'^jperm/', include('jperm.urls')),
    (r'^node_auth/', 'jumpserver.views.node_auth'),
    (r'download/(\d{4}/\d\d/\d\d/.*)', 'jumpserver.views.download_file'),
    (r'test2', 'jumpserver.views.test2'),
)
