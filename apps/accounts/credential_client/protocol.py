"""Stable wire compatibility, independent of SDK and local file versions."""

SUPPORTED_PROTOCOL_VERSIONS = (1,)
SUPPORTED_AGENT_CONFIG_SCHEMA_VERSIONS = (1,)

# Capability names are additive. They describe server features, not account
# authorization or permission to execute a command on a particular instance.
SERVER_CAPABILITIES = (
    'account_lookup', 'account_list', 'credential_events', 'event_results',
    'agent_sync', 'application_commands', 'metadata', 'application_status',
)


def supports_versions(protocol_version, config_schema_version, *, is_agent):
    return protocol_version in SUPPORTED_PROTOCOL_VERSIONS and (
        not is_agent or config_schema_version in SUPPORTED_AGENT_CONFIG_SCHEMA_VERSIONS
    )


def supported_versions():
    return {
        'supported_protocol_versions': list(SUPPORTED_PROTOCOL_VERSIONS),
        'supported_agent_config_schema_versions': list(SUPPORTED_AGENT_CONFIG_SCHEMA_VERSIONS),
    }
