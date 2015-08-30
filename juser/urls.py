from django.conf.urls import patterns, include, url
from jumpserver.api import view_splitter
from juser.views import *

urlpatterns = patterns('juser.views',
    # Examples:
    # url(r'^$', 'jumpserver.views.home', name='home'),
    # url(r'^blog/', include('blog.urls')),

    (r'^group_add/$', group_add),
    (r'^group_list/$', group_list),
    (r'^group_del/$', group_del),
    (r'^group_del_ajax', group_del_ajax),
    (r'^group_edit/$', group_edit),
    (r'^user_add/$', user_add),
    (r'^user_list/$', view_splitter, {'su': user_list, 'adm': user_list_adm}),
    (r'^user_detail/$', 'user_detail'),
    (r'^user_del/$', 'user_del'),
    (r'^user_del_ajax/$', 'user_del_ajax'),
    (r'^user_edit/$', view_splitter, {'su': user_edit, 'adm': user_edit_adm}),
    (r'^profile/$', 'profile'),
    (r'^chg_info/$', 'chg_info'),
    (r'^chg_role/$', 'chg_role'),
    (r'^down_key/$', 'down_key'),
)
