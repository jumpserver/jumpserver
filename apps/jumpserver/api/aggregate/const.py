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

common_params = [
    {
        "name": "resource",
        "in": "path",
        "description": """Resource to query, e.g.  users, assets, permissions, acls, user-groups, policies, nodes, hosts, 
        devices, clouds, webs, databases,
        gpts, ds, customs, platforms, zones, gateways, protocol-settings, labels, virtual-accounts,
        gathered-accounts, account-templates, account-template-secrets, account-backups, account-backup-executions,
        change-secret-automations, change-secret-executions, change-secret-records, gather-account-automations,
        gather-account-executions, push-account-automations, push-account-executions, push-account-records,
        check-account-automations, check-account-executions, account-risks, integration-apps, asset-permissions,
        zones, gateways, virtual-accounts, gathered-accounts, account-templates, account-template-secrets,, 
        GET /api/v1/resources/ to get full supported resource.
    """,
        "required": True,
        "type": "string"
    },
    {
        "name": "X-JMS-ORG",
        "in": "header",
        "description": "The organization ID to use for the request. Organization is the namespace for resources, if not set, use default org",
        "required": False,
        "type": "string"
    }
]
