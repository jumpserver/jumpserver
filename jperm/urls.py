from django.conf.urls import patterns, include, url
from jperm.views import *

urlpatterns = patterns('jperm.views',
    # Examples:
    # url(r'^$', 'jumpserver.views.home', name='home'),
    # url(r'^blog/', include('blog.urls')),

    (r'^perm_edit/$', view_splitter, {'su': perm_edit, 'adm': perm_edit_adm}),
    (r'^dept_perm_edit/$', 'dept_perm_edit'),
    (r'^perm_list/$', view_splitter, {'su': perm_list, 'adm': perm_list_adm}),
    (r'^dept_perm_list/$', 'dept_perm_list'),
    (r'^perm_user_detail/$', 'perm_user_detail'),
    (r'^perm_detail/$', 'perm_detail'),
    (r'^perm_del/$', 'perm_del'),
    (r'^perm_asset_detail/$', 'perm_asset_detail'),
    (r'^sudo_list/$', view_splitter, {'su': sudo_list, 'adm': sudo_list_adm}),
    (r'^sudo_del/$', 'sudo_del'),
    (r'^sudo_edit/$', view_splitter, {'su': sudo_edit, 'adm': sudo_edit_adm}),
    (r'^sudo_refresh/$', 'sudo_refresh'),
    (r'^sudo_detail/$', 'sudo_detail'),
    (r'^cmd_add/$', view_splitter, {'su': cmd_add, 'adm': cmd_add_adm}),
    (r'^cmd_list/$', 'cmd_list'),
    (r'^cmd_del/$', 'cmd_del'),
    (r'^cmd_edit/$', 'cmd_edit'),
    (r'^apply/$', 'perm_apply'),
    (r'^apply_show/(\w+)/$', 'perm_apply_log'),
    (r'^apply_exec/$', 'perm_apply_exec'),
    (r'^apply_info/$', 'perm_apply_info'),
    (r'^apply_search/$', 'perm_apply_search'),
)
