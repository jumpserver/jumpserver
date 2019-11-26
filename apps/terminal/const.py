# -*- coding: utf-8 -*-
#

ASSETS_CACHE_KEY = "terminal__session__assets"
USERS_CACHE_KEY = "terminal__session__users"
SYSTEM_USER_CACHE_KEY = "terminal__session__system_users"


# Replay Storage

REPLAY_STORAGE_TYPE_SERVER = 'server'
REPLAY_STORAGE_TYPE_S3 = 's3'
REPLAY_STORAGE_TYPE_OSS = 'oss'
REPLAY_STORAGE_TYPE_AZURE = 'azure'

REPLAY_STORAGE_TYPE_SERVER_FIELDS = []
REPLAY_STORAGE_TYPE_S3_FIELDS = [
    {'name': 's3_bucket'},
    {'name': 's3_access_key', 'write_only': True},
    {'name': 's3_secret_key', 'write_only': True},
    {'name': 's3_endpoint'}
]
REPLAY_STORAGE_TYPE_OSS_FIELDS = [
    {'name': 'oss_bucket'},
    {'name': 'oss_access_key', 'write_only': True},
    {'name': 'oss_secret_key', 'write_only': True},
    {'name': 'oss_endpoint'}
]
REPLAY_STORAGE_TYPE_AZURE_FIELDS = [
    {'name': 'azure_container_name'},
    {'name': 'azure_account_name'},
    {'name': 'azure_account_key', 'write_only': True},
    {'name': 'azure_endpoint_suffix'}
]

REPLAY_STORAGE_TYPE_MAP_FIELDS = {
    REPLAY_STORAGE_TYPE_SERVER: REPLAY_STORAGE_TYPE_SERVER_FIELDS,
    REPLAY_STORAGE_TYPE_S3: REPLAY_STORAGE_TYPE_S3_FIELDS,
    REPLAY_STORAGE_TYPE_OSS: REPLAY_STORAGE_TYPE_OSS_FIELDS,
    REPLAY_STORAGE_TYPE_AZURE: REPLAY_STORAGE_TYPE_AZURE_FIELDS
}


# Command Storage

COMMAND_STORAGE_TYPE_SERVER = 'server'
COMMAND_STORAGE_TYPE_ES = 'es'

COMMAND_STORAGE_TYPE_SERVER_FIELDS = []
COMMAND_STORAGE_TYPE_ES_FIELDS = [
    {'name': 'es_hosts'},
    {'name': 'es_index'},
    {'name': 'es_doc_type'}
]

COMMAND_STORAGE_TYPE_MAP_FIELDS = {
    COMMAND_STORAGE_TYPE_SERVER: COMMAND_STORAGE_TYPE_SERVER_FIELDS,
    COMMAND_STORAGE_TYPE_ES: COMMAND_STORAGE_TYPE_ES_FIELDS,
}
