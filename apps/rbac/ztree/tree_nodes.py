from django.utils.translation import gettext_lazy as _

permission_tree_nodes = {
    # 节点
    'root': {
        'name': _('All permissions'),
    },
    'view': {
        'name': _("View menu")
    },
    'view_console': {
        'name': _('Console view'),
    },
    'user_management': {
        'name': _('User management')
    },
    'user_list': {
        'name': _('User list')
    },
    'view_workspace': {
        'name': _('Workspace view')
    },
    'view_audit': {
        'name': _("Audit view")
    },
    'asset_perm': {
        'name': _('Asset permission')
    },
    'session_audits': {
        'name': _('Session audits')
    },
    'session_record': {
        'name': _('Online/Offline Session record')
    },
    'asset_management': {
        'name': _('Asset management')
    },
    'asset_list': {
        'name': _('Asset list')
    },
    'my_asset': {
        'name': _('My assets')
    },
    'my_app': {
        'name': _('My application')
    },
    'bulk_command': {
        'name': _('Bulk command')
    },
    'system_setting': {
        'name': _('System setting')
    },
    'ticket': {
        'name': _('Ticket system')
    },
    'help': {
        'name': _('Help')
    },
    'api_permission': {
        'name': _('API permission')
    },
    'app_management': {
        'name': _('Application management')
    },
    'account_management': {
        'name': _('Account management'),
    },
    'perm_management': {
        'name': _('Permission management'),
    },
    'access_control': {
        'name': _('Access control'),
    },
    'job_center': {
        'name': _('Job center'),
    },
    'session_audit': {
        'name': _('Session audit')
    },
    'log_audit': {
        'name': _('Log audit')
    },
    'user_group_list': {
        'name': _('User group')
    },
    'role_list': {
        'name': _('Role list')
    },
    'app_perm': {
        'name': _('Application permission')
    },
    'user_login_acl': {
        'name': _('User login acl')
    },
    'user_group_detail': {
        'name': _('Detail')
    },
    'permission_list': {
        'name': _('Permission list')
    },
    'node_tree': {
        'name': _('Node tree')
    },
    'cloud_sync': {
        'name': _('Cloud sync')
    },
    'sync_instance_task_list': {
        'name': _('Sync instance task list')
    },
    'account_list': {
        'name': _('Account list')
    },
    'system_user': {
        'name': _('Common/Admin User')
    },
    'system_user_asset_list': {
        'name': _('Asset list'),
    },
    'system_user_account_list': {
        'name': _('Account list')
    },
    'command_filter': {
        'name': _('Command filter')
    },
    'command_filter_rule': {
        'name': _('Command filter rule')
    },
    'platform_list': {
        'name': _('Platform list')
    },
    'label_management': {
        'name': _('Label management')
    },
    'remote_app': {
        'name': _('Remote application')
    },
    'db_app': {
        'name': _('Database application')
    },
    'k8s_app': {
        'name': _('Kubernetes')
    },
    'asset_account': {
        'name': _('Asset account')
    },
    'application_account': {
        'name': _('Application account')
    },
    'gather_user': {
        'name': _('Gathered user')
    },
    'gather_user_list': {
        'name': _('Gathered user list')
    },
    'gather_user_task_list': {
        'name': _('Gathered user task list')
    },
    'change_auth_plan': {
        'name': _('Change auth plan')
    },
    'asset_change_auth_plan': {
        'name': _('Asset change auth plan')
    },
    'app_change_auth_plan': {
        'name': _('Application change auth plan')
    },
    'account_backup': {
        'name': _('Account backup')
    },
    'asset_permission': {
        'name': _('Asset permission')
    },
    'app_permission': {
        'name': _('Application permission')
    },
    'asset_login': {
        'name': _('Asset login')
    },
    'task_list': {
        'name': _('Task list')
    },
    'command_record': {
        'name': _('Command record')
    },
    'file_transfer': {
        'name': _('File transfer')
    },
    'my_remote_app': {
        'name': _('Remote App')
    },
    'my_db_app': {
        'name': _('Database application')
    },
    'my_k8s_app': {
        'name': _('Kubernetes')
    },
    'terminal_setting': {
        'name': _('Terminal setting')
    },
    'terminal_management': {
        'name': _('Terminal management')
    },
    'command_storage': {
        'name': _('Command storage')
    },
    'replay_storage': {
        'name': _('Replay storage')
    },
    'org_management': {
        'name': _('Organization management')
    },
    'license': {
        'name': _('License')
    },

    # 权限
    'rbac.view_permission': {
        'name': _('View all permission')
    },
    'domain_list': {
        'name': _('Domain list')
    },
    'gateway_list': {
        'name': _('Gateway list')
    },
    'org_role': {
        'name': _('Organization role')
    },
    'system_role': {
        'name': _('System role')
    },
    'xpack.add_gatherusertaskexecution': {
        'name': _('Run gather user task')
    },
    'xpack.add_changeauthplanexecution': {
        'name': _('Run asset change auth plan')
    },
    'xpack.add_applicationchangeauthplanexecution': {
        'name': _('Run application change auth plan')
    },
    'assets.add_accountbackupplanexecution': {
        'name': _('Run account backup plan')
    },
    'ops.add_adhocexecution': {
        'name': _('Run task')
    },
    'ops.view_adhoc': {
        'name': _('View task version')
    },
    'ops.view_adhocexecution': {
        'name': _('View execution history')
    },
    'ops.add_commandexecution': {
        'name': _('Bulk command')
    },
    'notifications.view_sitemessage': {
        'name': _('Site message')
    },
    'notifications.change_systemmsgsubscription': {
        'name': _('Message subscription')
    },
    'terminal.view_status': {
        'name': _('Component monitor')
    },
    'tickets.view_ticket': {
        'name': _('View my/assigned ticket')
    },
    'tickets.add_ticket': {
        'name': _('Create asset/application ticket')
    },
    'tickets.change_ticket': {
        'name': _('Change/close ticket')
    },
    'assets.match_asset': {
        'name': _('View some of the assets searched')
    },
    'rbac.view_workspace': {
        'checked': True,
        'chkDisabled': True,
    },
    'rbac.view_overview': {
        'name': _('Overview'),
        'checked': True,
        'chkDisabled': True,
    }
}
