from django.conf.urls import patterns, include, url
from api import view_splitter
from views import index, admin_index


urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'jumpserver.views.home', name='home'),
    # url(r'^blog/', include('blog.urls')),
    # (r'^$', view_splitter, {'su': index, 'adm': admin_index}),
    (r'^$', 'jumpserver.views.index'),
    (r'^api/user/$', 'jumpserver.api.api_user'),
    (r'^skin_config/$', 'jumpserver.views.skin_config'),
    (r'^install/$', 'jumpserver.views.install'),
    (r'^base/$', 'jumpserver.views.base'),
    (r'^login/$', 'jumpserver.views.login'),
    (r'^logout/$', 'jumpserver.views.logout'),
    (r'^juser/', include('juser.urls')),
    (r'^jasset/', include('jasset.urls')),
    (r'^jlog/', include('jlog.urls')),
    (r'^jperm/', include('jperm.urls')),

)
