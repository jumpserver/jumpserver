from django.conf.urls import patterns, include, url
from jperm.views import *

urlpatterns = patterns('jperm.views',
                       (r'^user/$', perm_user_list),
                       (r'^perm_user_edit/$', perm_user_edit),
                       (r'^perm_user_detail/$', perm_user_detail),
                       (r'^group/$', perm_group_list),
                       (r'^perm_group_edit/$', perm_group_edit),
                       (r'^log/$', log),
                       (r'^sys_user_add/$', sys_user_add),
                       (r'^sys_user_list/$', sys_user_list),
                       (r'^sys_user_del/$', sys_user_del),
                       (r'^sys_user_edit/$', sys_user_edit),
                       )
