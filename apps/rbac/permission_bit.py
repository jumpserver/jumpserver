from django.utils.translation import ugettext_lazy as _

# Permissions Bits List

only_system_admin_permissions_bits = {
    'delete_user': 'Delete user',
    'add_role': 'Create role',
    'change_role': 'Update role',
    'delete_role': 'Delete role',
    'view_role': 'View role',
    'view_permission': 'View all permission bit',
    'add_organization': 'Create organization',
    'change_organization': 'Update organization',
    'delete_organization': 'Delete organization',
    'view_organization': 'View organization',
    'change_license': 'Update license',
    'change_interface': 'Update interface',
    'change_setting': 'Update system setting',
    'view_setting': 'View system setting',
}

_org_admin_permissions_bits = {
    'add_user': 'Create user',
    'change_user': 'Update user',
    'remove_user': 'Remove user',
    'view_user': 'View user',
    'add_usergroup': 'Create user group',
    'change_usergroup': 'Update user group',
    'delete_usergroup': 'Delete user group',
    'view_usergroup': 'View user group',
    'add_accesskey': 'Add access key',
    'delete_accesskey': 'Delete access key',
    'view_accesskey': 'View access key',
    'add_privatetoken': 'Create private token',
    'add_ssotoken': 'Create SSO token',
    'add_loginacl': 'Create user login rules',
    'change_loginacl': 'Update user login rules',
    'delete_loginacl': 'Delete user login rules',
    'view_loginacl': 'View user login rules',
    'add_loginassetacl': 'Create login asset access control',
    'change_loginassetacl': 'Update login asset access control',
    'delete_loginassetacl': 'Delete login asset access control',
    'view_loginassetacl': 'View login asset access control',
    'add_rolebinding': 'Create User role binding',
    'change_rolebinding': 'Update user role binding',
    'view_rolebinding': 'View user role binding',
    'delete_rolebinding': 'Delete user role binding',
    'add_organizationmember': 'Add organization member',
    'remove_organizationmember': 'Remove organization member',
    'view_organizationmember': 'View organization member',
    'add_node': 'Create node',
    'change_node': 'Update node',
    'delete_node': 'Delete node',
    'view_node': 'View node',
    'add_asset': 'Create asset',
    'change_asset': 'Update asset',
    'delete_asset': 'Delete asset',
    'view_asset': 'View asset',
    'add_favoriteasset': 'Add favorite asset',
    'add_assetuser': 'Create asset user',
    'change_assetuser': 'Update asset user',
    'delete_assetuser': 'Delete asset user',
    'view_assetuser': 'View asset user',
    'add_adminuser': 'Create admin user',
    'change_adminuser': 'Update admin user',
    'delete_adminuser': 'Delete admin user',
    'view_adminuser': 'View admin user',
    'add_systemuser': 'Create system user',
    'change_systemuser': 'Update system user',
    'delete_systemuser': 'Delete system user',
    'view_systemuser': 'View system user',
    'add_label': 'Create label',
    'change_label': 'Update label',
    'delete_label': 'Delete label',
    'view_label': 'View label',
    'add_domain': 'Create domain',
    'change_domain': 'Update domain',
    'delete_domain': 'Delete domain',
    'view_domain': 'View domain',
    'add_gateway': 'Create gateway',
    'change_gateway': 'Update gateway',
    'delete_gateway': 'Delete gateway',
    'view_gateway': 'View gateway',
    'add_commandfilter': 'Create command filter',
    'change_commandfilter': 'Update command filter',
    'delete_commandfilter': 'Delete command filter',
    'view_commandfilter': 'View command filter',
    'add_commandfilterrule': 'Create command filter rule',
    'change_commandfilterrule': 'Update command filter rule',
    'delete_commandfilterrule': 'Delete command filter rule',
    'view_commandfilterrule': 'View command filter rule',
    'add_platform': 'Create platform',
    'change_platform': 'Update platform',
    'delete_platform': 'Delete platform',
    'view_platform': 'View platform',
    'add_application': 'Create application',
    'change_application': 'Update application',
    'delete_application': 'Delete application',
    'view_application': 'View application',
    'add_assetpermission': 'Create asset permission',
    'change_assetpermission': 'Update asset permission',
    'delete_assetpermission': 'Delete asset permission',
    'view_assetpermission': 'View asset permission',
    'add_applicationpermission': 'Create application permission',
    'change_applicationpermission': 'Update application permission',
    'delete_applicationpermission': 'Delete application permission',
    'view_applicationpermission': 'View application permission',
    'add_session': 'Create session',
    'change_session': 'Update session',
    'delete_session': 'Delete session',
    'view_session': 'View session',
    'add_command': 'Create command',
    'view_command': 'View command',
    'add_status': 'Create system status',
    'change_terminal': 'Update terminal',
    'delete_terminal': 'Delete terminal',
    'view_terminal': 'View terminal',
    'add_commandstorage': 'Create command storage',
    'change_commandstorage': 'Update command storage',
    'delete_commandstorage': 'Delete command storage',
    'view_commandstorage': 'View command storage',
    'add_replaystorage': 'Create replay storage',
    'change_replaystorage': 'Update replay storage',
    'delete_replaystorage': 'Delete replay storage',
    'view_replaystorage': 'View replay storage',
    'terminate_session': 'Terminate session',
    'add_commandexecution': 'Execute batch command',
    'add_ticket': 'Create ticket',
    'change_ticket': 'Update ticket',
    'delete_ticket': 'Delete ticket',
    'view_ticket': 'View ticket',
    'add_comment': 'Create comment',
    'view_comment': 'View comment',
    'change_gathereduser': 'Update gathered user',
    'delete_gathereduser': 'Delete gathered user',
    'view_gathereduser': 'View gathered user',
    'add_gatherusertask': 'Create gather user task',
    'change_gatherusertask': 'Update gather user task',
    'delete_gatherusertask': 'Delete gather user task',
    'view_gatherusertask': 'View gather user task',
    'add_account': 'Create account',
    'change_account': 'Update account',
    'delete_account': 'Delete account',
    'view_account': 'View account',
    'add_syncinstancetask': 'Create Synchronization instance task',
    'change_syncinstancetask': 'Update Synchronization instance task',
    'delete_syncinstancetask': 'Delete Synchronization instance task',
    'view_syncinstancetask': 'View Synchronization instance task',
    'view_syncinstancedetail': 'View Synchronization instance detail',
    'add_changeauthplan': 'Create change authentication plan',
    'change_changeauthplan': 'Update change authentication plan',
    'delete_changeauthplan': 'Delete change authentication plan',
    'view_changeauthplan': 'Update change authentication plan',
}

auditor_permissions_bits = {
    'add_ftplog': 'Create FTP log',
    'view_ftplog': 'View FTP log',
    'view_operatelog': 'View operate log',
    'add_passwordchangelog': 'Create password change log',
    'view_passwordchangelog': 'View password change log',
    'add_userloginlog': 'Create user login log',
    'view_userloginlog': 'View user login log',
}

user_permissions_bits = {
    'view_my_asset': 'View my asset',
    'view_my_application': 'View my application',
    'execute_batch_command': 'Execute batch command',
}

other_only_system_admin_permissions_bits = {

}
_other_org_admin_permissions_bits = {

}
other_auditor_permissions_bits = {

}
other_user_permissions_bits = {

}

other_org_admin_permissions_bits = {}
other_org_admin_permissions_bits.update(_other_org_admin_permissions_bits)
other_org_admin_permissions_bits.update(other_auditor_permissions_bits)
other_org_admin_permissions_bits.update(other_user_permissions_bits)

org_admin_permissions_bits = {}
org_admin_permissions_bits.update(_org_admin_permissions_bits)
org_admin_permissions_bits.update(other_org_admin_permissions_bits)
org_admin_permissions_bits.update(auditor_permissions_bits)
org_admin_permissions_bits.update(user_permissions_bits)


system_admin_permissions_bits = {}
system_admin_permissions_bits.update(only_system_admin_permissions_bits)
system_admin_permissions_bits.update(other_only_system_admin_permissions_bits)
system_admin_permissions_bits.update(org_admin_permissions_bits)


permissions_bits_map = {
    'system_admin': list(system_admin_permissions_bits.keys()),
    'org_admin': list(org_admin_permissions_bits.keys()),
    'system_auditor': list(auditor_permissions_bits.keys()),
    'org_auditor': list(auditor_permissions_bits.keys()),
    'user': list(user_permissions_bits.keys()),
}

scope_system_permissions_bits = permissions_bits_map['system_admin']
scope_org_permissions_bits = permissions_bits_map['org_admin']
