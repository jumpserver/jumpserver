from django.conf.urls import patterns, include, url
from jperm.views import *

urlpatterns = patterns('jperm.views',
                       (r'^rule/$', perm_rules),
                       (r'^perm_rule_add/$', perm_rule_add),
                       (r'^perm_rule_detail/$', perm_rule_detail),
                       (r'^perm_rule_edit/$', perm_rule_edit),
                       (r'^perm_rule_delete/$', perm_rule_delete),
                       (r'^group/$', perm_group_list),
                       (r'^perm_group_edit/$', perm_group_edit),
                       (r'^log/$', log),
                       (r'^sys_user_add/$', sys_user_add),
                       (r'^sys_user_list/$', sys_user_list),
                       (r'^sys_user_del/$', sys_user_del),
                       (r'^sys_user_edit/$', sys_user_edit),
                       )
