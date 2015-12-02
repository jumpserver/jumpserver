from django.conf.urls import patterns, include, url


urlpatterns = patterns('',
    # Examples:
    (r'^$', 'jumpserver.views.index'),
    (r'^api/user/$', 'jumpserver.api.api_user'),
    (r'^skin_config/$', 'jumpserver.views.skin_config'),
    (r'^login/$', 'jumpserver.views.Login'),
    (r'^logout/$', 'jumpserver.views.Logout'),
    (r'^exec_cmd/$', 'jumpserver.views.exec_cmd'),
    (r'^file/upload/$', 'jumpserver.views.upload'),
    (r'^file/download/$', 'jumpserver.views.download'),
    (r'^setting', 'jumpserver.views.setting'),
    (r'^juser/', include('juser.urls')),
    (r'^jasset/', include('jasset.urls')),
    (r'^jlog/', include('jlog.urls')),
    (r'^jperm/', include('jperm.urls')),
)
