from django.utils.translation import gettext_lazy as _

permission_tree_nodes = {
    'root': {
        'name': _('All permissions'),
        # 'id': '',
        # 'pId': '',
        # 'open': True,
        # 'title': _('All permissions'),
        # 'isParent': True,
        # 'chkDisabled': False,
        # 'iconSkin': 'file',
        # 'checked': False,
        # 'meta': {
        #     'type': 'perm'
        # }
    },
    'view': {
        'name': _("View menu")
    },
    'view_console': {
        'name': _('Console view')
    },
    'view_workspace': {
        'name': _('Workspace view')
    },
    'view_audit': {
        'name': _("Audits view")
    },
    'session_audits': {
        'name': _('Session audits')
    },
    'session_record': {
        'name': _('Session record')
    },
    'asset_management': {
        'name': _('Asset management')
    },
    'user_management': {
        'name': _('User management')
    },
    'site_message': {
        'name': _('Site message')
    },
    'user_list': {
        'name': _('User list')
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
    'user_detail': {
        'name': _('User detail')
    },
    'asset_perm': {
        'name': _('Asset permission')
    },
    'app_perm': {
        'name': _('Application permission')
    },
    'user_login_acl': {
        'name': _('User login acl')
    },
    'user_group_detail': {
        'name': _('User group detail')
    }
}
