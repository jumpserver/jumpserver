from ansible_collections.community.mongodb.plugins.module_utils.mongodb_common import (
    MongoClient,
    rename_ssl_option_for_pymongo4,
    ssl_connection_options,
)


def _apply_connection_options(connection_params, module, tls_enabled):
    for item in module.params.get('connection_options') or []:
        if isinstance(item, dict):
            options = item.items()
        elif isinstance(item, str) and '=' in item:
            key, value = item.split('=', 1)
            options = [(key, value)]
        else:
            raise ValueError(
                'Invalid MongoDB connection option: %s' % item
            )
        for key, value in options:
            # PyMongo rejects TLS-only options when TLS is disabled. Keep
            # generic options such as server-selection/connect timeouts active
            # regardless of whether the asset uses TLS.
            if (
                    not tls_enabled
                    and str(key).lower().startswith(('tls', 'ssl'))
            ):
                continue
            connection_params[key] = value
    return connection_params


def get_authenticated_mongodb_client(module, direct_connection=False):
    params = module.params
    connection_params = {
        'host': params['login_host'],
        'port': params['login_port'],
    }
    if direct_connection:
        connection_params['directConnection'] = True

    if params.get('ssl'):
        connection_params = ssl_connection_options(
            connection_params, module
        )
        connection_params = rename_ssl_option_for_pymongo4(
            connection_params
        )
    else:
        connection_params = _apply_connection_options(
            connection_params, module, tls_enabled=False
        )

    replica_set = params.get('replica_set')
    if replica_set:
        connection_params['replicaSet'] = replica_set

    username = params.get('login_user')
    password = params.get('login_password')
    auth_mechanism = params.get('auth_mechanism')
    x509_auth = auth_mechanism == 'MONGODB-X509'
    if username and (password is not None or x509_auth):
        connection_params['username'] = username
        if password is not None:
            connection_params['password'] = password
        connection_params['authSource'] = params['login_database']
    elif username or password:
        module.fail_json(
            msg='Both login_user and login_password are required'
        )

    return MongoClient(**connection_params)
