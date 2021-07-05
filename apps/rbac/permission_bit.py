from django.utils.translation import ugettext_lazy as _

# permission bit list

system_admin_role_name = 'system_admin'

permissions_bits = {
    'user': {
        'delete_user': _('Delete user')
    },
    'rbac': {
        'role': {
            'add_role': _('Create role'),
            'change_role': _('Update role'),
            'delete_role': _('Delete role'),
            'view_role': _('View role'),
        },
        'permission': {
            'view_permission': _('View all permission bit'),
        }
    },
    'orgs': {
        'org': {
            'add_organization': _('Create organization'),
            'change_organization': _('Update organization'),
            'delete_organization': _('Delete organization'),
            'view_organization': _('View organization')
        }
    },
    'xpack': {
        'license': {
            'change_license': _('Update license'),
        },
        'interface': {
            'change_interface': _('Update interface')
        }
    },
    'settings': {
        'change_setting': _('Update system setting'),
        'view_setting': _('View system setting')
    },
    'other': {

    }
}

organization_permissions_bits = {
    'users': {
        'user': {
            'add_user': _('Create user'),
            'change_user': _('Update user'),
            'remove_user': _('Remove user'),
            'view_user': _('View user'),
        },
        'user_group': {
            'add_usergroup': _('Create user group'),
            'change_usergroup': _('Update user group'),
            'delete_usergroup': _('Delete user group'),
            'view_usergroup': _('View user group')
        },
    },
    'authentication': {
        'access_key': {
            'add_accesskey': _('Add access key'),
            'delete_accesskey': _('Delete access key'),
            'view_accesskey': _('View access key'),
        },
        'private_token': {
            'add_privatetoken': _('Create private token'),
        },
        'sso_token': {
            'add_ssotoken': _('Create SSO token')
        }
    },
    'acls': {
        'login_acl': {
            'add_loginacl': _('Create user login rules'),
            'change_loginacl': _('Update user login rules'),
            'delete_loginacl': _('Delete user login rules'),
            'view_loginacl': _('View user login rules'),
        },
        'login_asset_acl': {
            'add_loginassetacl': _('Create login asset access control'),
            'change_loginassetacl': _('Update login asset access control'),
            'delete_loginassetacl': _('Delete login asset access control'),
            'view_loginassetacl': _('View login asset access control'),
        }
    },
    'rbac': {
        'role_binding': {
            'add_rolebinding': _('Create User role binding'),
            'change_rolebinding': _('Update user role binding'),
            'view_rolebinding': _('View user role binding'),
            'delete_rolebinding': _('Delete user role binding')
        }
    },
    'orgs': {
        'org_member': {
            'add_organizationmember': _('Add organization member'),
            'remove_organizationmember': _('Remove organization member'),
            'view_organizationmember': _('View organization member'),
        }
    },
    'assets': {
        'node': {
            'add_node': _('Create node'),
            'change_node': _('Update node'),
            'delete_node': _('Delete node'),
            'view_node': _('View node'),
        },
        'asset': {
            'add_asset': _('Create asset'),
            'change_asset': _('Update asset'),
            'delete_asset': _('Delete asset'),
            'view_asset': _('View asset'),
        },
        'favorite_asset': {
            'add_favoriteasset': _('Add favorite asset'),
        },
        'asset_user': {
            'add_assetuser': _('Create asset user'),
            'change_assetuser': _('Update asset user'),
            'delete_assetuser': _('Delete asset user'),
            'view_assetuser': _('View asset user'),
        },
        'admin_user': {
            'add_adminuser': _('Create admin user'),
            'change_adminuser': _('Update admin user'),
            'delete_adminuser': _('Delete admin user'),
            'view_adminuser': _('View admin user'),
        },
        'system_user': {
            'add_systemuser': _('Create system user'),
            'change_systemuser': _('Update system user'),
            'delete_systemuser': _('Delete system user'),
            'view_systemuser': _('View system user'),
        },
        'label': {
            'add_label': _('Create label'),
            'change_label': _('Update label'),
            'delete_label': _('Delete label'),
            'view_label': _('View label'),
        },
        'domain': {
            'add_domain': _('Create domain'),
            'change_domain': _('Update domain'),
            'delete_domain': _('Delete domain'),
            'view_domain': _('View domain'),
        },
        'gateway': {
            'add_gateway': _('Create gateway'),
            'change_gateway': _('Update gateway'),
            'delete_gateway': _('Delete gateway'),
            'view_gateway': _('View gateway'),
        },
        'command_filter': {
            'add_commandfilter': _('Create command filter'),
            'change_commandfilter': _('Update command filter'),
            'delete_commandfilter': _('Delete command filter'),
            'view_commandfilter': _('View command filter'),
            'add_commandfilterrule': _('Create command filter rule'),
            'change_commandfilterrule': _('Update command filter rule'),
            'delete_commandfilterrule': _('Delete command filter rule'),
            'view_commandfilterrule': _('View command filter rule'),
        },
        'platform': {
            'add_platform': _('Create platform'),
            'change_platform': _('Update platform'),
            'delete_platform': _('Delete platform'),
            'view_platform': _('View platform')
        }
    },
    'application': {
        'add_application': _('Create application'),
        'change_application': _('Update application'),
        'delete_application': _('Delete application'),
        'view_application': _('View application')
    },
    'perms': {
        'asset_permission': {
            'add_assetpermission': _('Create asset permission'),
            'change_assetpermission': _('Update asset permission'),
            'delete_assetpermission': _('Delete asset permission'),
            'view_assetpermission': _('View asset permission'),
        },
        'application_permission': {
            'add_applicationpermission': _('Create application permission'),
            'change_applicationpermission': _('Update application permission'),
            'delete_applicationpermission': _('Delete application permission'),
            'view_applicationpermission': _('View application permission'),
        }
    },
    'terminal': {
        'session': {
            'add_session': _('Create session'),
            'change_session': _('Update session'),
            'delete_session': _('Delete session'),
            'view_session': _('View session'),
        },
        'command': {
            'add_command': _('Create command'),
            'view_command': _('View command'),
        },
        'status': {
            'add_status': _('Create system status'),
        },
        'terminal': {
            'change_terminal': _('Update terminal'),
            'delete_terminal': _('Delete terminal'),
            'view_terminal': _('View terminal'),
        },
        'command_storage': {
            'add_commandstorage': _('Create command storage'),
            'change_commandstorage': _('Update command storage'),
            'delete_commandstorage': _('Delete command storage'),
            'view_commandstorage': _('View command storage'),
        },
        'replay_storage': {
            'add_replaystorage': _('Create replay storage'),
            'change_replaystorage': _('Update replay storage'),
            'delete_replaystorage': _('Delete replay storage'),
            'view_replaystorage': _('View replay storage'),
        },
        'other': {
            'terminate_session': _('Terminate session')
        }
    },
    'ops': {
        'command_execution': {
            'add_commandexecution': _('Execute batch command'),
        }
    },
    'tickets': {
        'ticket': {
            'add_ticket': _('Create ticket'),
            'change_ticket': _('Update ticket'),
            'delete_ticket': _('Delete ticket'),
            'view_ticket': _('View ticket'),
        },
        'comment': {
            'add_comment': _('Create comment'),
            'view_comment': _('View comment'),
        }
    },
    'xpack': {
        'gathered_user': {
            'change_gathereduser': _('Update gathered user'),
            'delete_gathereduser': _('Delete gathered user'),
            'view_gathereduser': _('View gathered user'),
            'add_gatherusertask': _('Create gather user task'),
            'change_gatherusertask': _('Update gather user task'),
            'delete_gatherusertask': _('Delete gather user task'),
            'view_gatherusertask': _('View gather user task'),
        },
        'cloud': {
            'add_account': _('Create account'),
            'change_account': _('Update account'),
            'delete_account': _('Delete account'),
            'view_account': _('View account'),
            'add_syncinstancetask': _('Create Synchronization instance task'),
            'change_syncinstancetask': _('Update Synchronization instance task'),
            'delete_syncinstancetask': _('Delete Synchronization instance task'),
            'view_syncinstancetask': _('View Synchronization instance task'),
            'view_syncinstancedetail': _('View Synchronization instance detail'),
        },
        'change_auth_plan': {
            'add_changeauthplan': _('Create change authentication plan'),
            'change_changeauthplan': _('Update change authentication plan'),
            'delete_changeauthplan': _('Delete change authentication plan'),
            'view_changeauthplan': _('Update change authentication plan'),
        }
    },
    'other': {
    }
}

auditor_permissions_bits = {
    'audits': {
        'ftp_log': {
            'add_ftplog': _('Create FTP log'),
            'view_ftplog': _('View FTP log'),
        },
        'operate_log': {
            'view_operatelog': _('View operate log'),
        },
        'password_change_log': {
            'add_passwordchangelog': _('Create password change log'),
            'view_passwordchangelog': _('View password change log'),
        },
        'user_login_log': {
            'add_userloginlog': _('Create user login log'),
            'view_userloginlog': _('View user login log'),
        }
    }
}

user_permissions_bits = {
    'asset': {
        'view_my_asset': _('View my asset'),
    },
    'application': {
        'view_my_application': _('View my application'),
    },
    'execute_batch_command': {
        'execute_batch_command': _('Execute batch command'),
    }
}

system_permissions_bits = {

}


permissions_bits_map = {
    'system_admin': system_permissions_bits,
    'organization_admin': organization_permissions_bits,
    'system_auditor': auditor_permissions_bits,
    'organization_auditor': auditor_permissions_bits,
    'user': user_permissions_bits,
}

