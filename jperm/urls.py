from django.conf.urls import patterns, include, url
from jperm.views import *

urlpatterns = patterns('jperm.views',
                       (r'^rule/$', perm_rule_list),
                       (r'^perm_rule_add/$', perm_rule_add),
                       (r'^perm_rule_detail/$', perm_rule_detail),
                       (r'^perm_rule_edit/$', perm_rule_edit),
                       (r'^perm_rule_delete/$', perm_rule_delete),
                       (r'^role/$', perm_role_list),
                       (r'^role/perm_role_add/$', perm_role_add),
                       (r'^role/perm_role_delete/$', perm_role_delete),
                       (r'^role/perm_role_detail/$', perm_role_detail),
                       (r'^role/perm_role_edit/$', perm_role_edit),
                       (r'^role/perm_role_push/$', perm_role_push),
                       (r'^sudo/$', perm_sudo_list),
                       (r'^sudo/perm_sudo_add/$', perm_sudo_add),
                       (r'^sudo/perm_sudo_delete/$', perm_sudo_delete),
                       (r'^sudo/perm_sudo_edit/$', perm_sudo_edit),

                       (r'^log/$', log),
                       (r'^sys_user_add/$', sys_user_add),
                       (r'^perm_user_list/$', sys_user_list),
                       (r'^sys_user_del/$', sys_user_del),
                       (r'^sys_user_edit/$', sys_user_edit),
                       )
