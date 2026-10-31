"""Stable authorization effects, independent of Koko tool names and drivers."""
import re
from typing import NamedTuple

from rest_framework.exceptions import ValidationError

from perms.const import ActionChoices


EXECUTION_MODES = frozenset(('shell', 'pipeline', 'database', 'files'))
FILE_FIELDS = ('path', 'destination', 'size', 'sha256', 'limit', 'content', 'overwrite', 'timeout_seconds')


class ActionPolicy(NamedTuple):
    modes: frozenset
    fields: tuple
    permission: int


COMMAND_MODES = frozenset(('shell', 'pipeline', 'database'))
FILE_MODES = frozenset(('files',))
ACTION_POLICIES = {
    'execute_command': ActionPolicy(COMMAND_MODES, ('command', 'prepared_command', 'cwd', 'env', 'timeout_seconds'), ActionChoices.connect),
    'open_terminal': ActionPolicy(COMMAND_MODES, ('timeout_seconds',), ActionChoices.connect),
    'file_list': ActionPolicy(FILE_MODES, FILE_FIELDS + ('cursor',), ActionChoices.connect),
    **{kind: ActionPolicy(FILE_MODES, FILE_FIELDS, permission) for kind, permission in (
        ('file_stat', ActionChoices.connect),
        ('file_read', ActionChoices.download), ('file_download', ActionChoices.download),
        ('file_write', ActionChoices.upload), ('file_upload', ActionChoices.upload),
        ('file_mkdir', ActionChoices.upload), ('file_remove', ActionChoices.delete),
        ('file_rename', ActionChoices.upload | ActionChoices.delete),
    )},
}


def allowed_actions(mode, permissions):
    if not ActionChoices.contains(permissions, ActionChoices.connect):
        return []
    return sorted(kind for kind, policy in ACTION_POLICIES.items()
                  if mode in policy.modes and ActionChoices.contains(permissions, policy.permission))


def node_capabilities(value):
    """Validate declarations received only through the authenticated component API."""
    if (not isinstance(value, dict) or set(value) != {'version', 'protocols'}
            or type(value['version']) is not int or value['version'] != 1):
        raise ValidationError('Unsupported Agent capability version')
    protocols = value['protocols']
    if not isinstance(protocols, dict) or not 1 <= len(protocols) <= 32:
        raise ValidationError('Invalid Agent protocol capabilities')
    for protocol, mode in protocols.items():
        if (not isinstance(protocol, str) or not re.fullmatch(r'[a-z0-9][a-z0-9_.+-]{0,15}', protocol)
                or not isinstance(mode, str) or mode not in EXECUTION_MODES):
            raise ValidationError('Invalid Agent protocol capability')
    return {'version': 1, 'protocols': dict(protocols)}


def context_protocols(context):
    return context['capabilities']['protocols']


def execution_mode(requested):
    mode = requested.get('execution_mode')
    if not isinstance(mode, str) or mode not in EXECUTION_MODES:
        raise ValidationError('Unsupported Agent execution mode')
    return mode
