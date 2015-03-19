from django.conf.urls import patterns, include, url
from jumpserver.api import view_splitter
from juser.views import *

urlpatterns = patterns('juser.views',
    # Examples:
    # url(r'^$', 'jumpserver.views.home', name='home'),
    # url(r'^blog/', include('blog.urls')),

    (r'^dept_list/$', view_splitter, {'su': dept_list, 'adm': dept_list_adm}),
    (r'^dept_add/$', 'dept_add'),
    (r'^dept_del/$', 'dept_del'),
    (r'^dept_detail/$', 'dept_detail'),
    (r'^dept_del_ajax/$', 'dept_del_ajax'),
    (r'^dept_edit/$', 'dept_edit'),
    (r'^dept_user_ajax/$', 'dept_user_ajax'),
    (r'^group_add/$', view_splitter, {'su': group_add, 'adm': group_add_adm}),
    (r'^group_list/$', view_splitter, {'su': group_list, 'adm': group_list_adm}),
    (r'^group_detail/$', 'group_detail'),
    (r'^group_del/$', view_splitter, {'su': group_del, 'adm': group_del_adm}),
    (r'^group_del_ajax/$', 'group_del_ajax'),
    (r'^group_edit/$', view_splitter, {'su': group_edit, 'adm': group_edit_adm}),
    (r'^user_add/$', 'user_add'),
    (r'^user_list/$', view_splitter, {'su': user_list, 'adm': user_list_adm}),
    (r'^user_detail/$', 'user_detail'),
    (r'^user_del/$', 'user_del'),
    (r'^user_del_ajax/$', 'user_del_ajax'),
    (r'^user_edit/$', view_splitter, {'su': user_edit, 'adm': user_edit_adm}),
    (r'^profile/$', 'profile'),
    (r'^chg_pass/$', 'chg_pass'),
)
