#!/usr/bin/env python3

list_params = [
    {
        "name": "search",
        "in": "query",
        "description": "A search term.",
        "required": False,
        "type": "string"
    },
    {
        "name": "order",
        "in": "query",
        "description": "Which field to use when ordering the results.",
        "required": False,
        "type": "string"
    },
    {
        "name": "limit",
        "in": "query",
        "description": "Number of results to return per page. Default is 10.",
        "required": False,
        "type": "integer"
    },
    {
        "name": "offset",
        "in": "query",
        "description": "The initial index from which to return the results.",
        "required": False,
        "type": "integer"
    },
]

unsupported_resources = [
    "customs", "protocol-settings", "gathered-accounts",
    "account-template-secrets", 'change-secret-records',
    'account-backup-executions', 'change-secret-executions', 
    'change-secret-status', 'gather-account-executions',
    'push-account-executions', 'check-account-executions',
    'integration-apps', 'asset-permissions-users-relations',
    'asset-permissions-user-groups-relations', 'asset-permissions-assets-relations',
    'asset-permissions-nodes-relations', 'terminal-status', 'tasks', 'status',
    'session-sharing-records', 'endpoints', 'endpoint-rules',
    'chatai-prompts', 'leak-passwords', 'super-connection-tokens',
    'system-role-bindings', 'org-role-bindings', 'content-types', 'system-role-permissions',
    'org-role-permissions', 'system-msg-subscriptions',
    'celery-period-tasks', 'task-executions', 'adhocs',
    'user-sessions', 'service-access-logs',
    'applet-publications', 'applet-host-deployments',
    'virtual-app-publications', 'applet-host-accounts', 'applet-host-applets',
    'flows'
]

supported_resources = [
    # User
    'users', 'user-groups', 'users-groups-relations',  
    # Asset
    'assets', 'hosts', 'devices', 'databases', 'webs', 'clouds', 'gpts',
    'ds', 'platforms', 'nodes', 'zones', 'gateways',
    # Account
    'virtual-accounts', 'account-templates',  'account-backups',
    # Automation
    'change-secret-automations',
    'gather-account-automations', 
    'push-account-automations', 
    'check-account-automations',
    'account-risks',
    # Permission
    'asset-permissions',
    # Terminal
    'terminals', 'replay-storages', 'command-storages',  
    # Applet
    'applets', 'applet-hosts', 
    'virtual-apps', 'app-providers', 
    # Ops
    'playbooks', 'variables',  'jobs',
    # Audit
    'ftp-logs', 'login-logs', 'operate-logs', 'password-change-logs', 'job-logs',
    # Tickets
    'tickets', 'comments', 'apply-assets', 'apply-nodes', 
    # Acls
    'login-acls', 'login-asset-acls', 'command-filter-acls',
    'command-groups', 'connect-method-acls', 'data-masking-rules',  
    # RBAC
    'roles', 'role-bindings',
    'system-roles', 'org-roles', 
    # Label
    'labeled-resources',
    'labels', 
]

common_params = [
    {
        "name": "resource",
        "in": "path",
        "description": f"""Resource to query, {supported_resources}
            GET /api/v1/resources/ to get full supported resource.
            if you want to get the resource list, you can set the resource name in the url.
            if you want to create a resource, you can set the resource name in the url.
            if you want to get the resource detail, you can set the resource name and id in the url.
            if you want to update the resource, you can set the resource name and id in the url.
            if you want to delete the resource, you can set the resource name and id in the url.
        """,
        "required": True,
        "type": "string",
        "enum": supported_resources
    },
    {
        "name": "X-JMS-ORG",
        "in": "header",
        "description": "The organization ID to use for the request. Organization is the namespace for resources, if not set, use default org",
        "required": False,
        "type": "string"
    }
]
