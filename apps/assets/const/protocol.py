from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from common.db.models import ChoicesMixin
from common.decorators import cached_method
from .base import FillType

__all__ = ['Protocol']


class Protocol(ChoicesMixin, models.TextChoices):
    ssh = 'ssh', 'SSH'
    sftp = 'sftp', 'SFTP'
    rdp = 'rdp', 'RDP'
    telnet = 'telnet', 'Telnet'
    vnc = 'vnc', 'VNC'
    winrm = 'winrm', 'WinRM'

    mysql = 'mysql', 'MySQL'
    mariadb = 'mariadb', 'MariaDB'
    oracle = 'oracle', 'Oracle'
    postgresql = 'postgresql', 'PostgreSQL'
    sqlserver = 'sqlserver', 'SQLServer'
    db2 = 'db2', 'DB2'
    clickhouse = 'clickhouse', 'ClickHouse'
    redis = 'redis', 'Redis'
    mongodb = 'mongodb', 'MongoDB'

    k8s = 'k8s', 'K8s'
    http = 'http', 'HTTP(s)'

    chatgpt = 'chatgpt', 'ChatGPT'

    @classmethod
    def device_protocols(cls):
        return {
            cls.ssh: {
                'port': 22,
                'secret_types': ['password', 'ssh_key'],
            },
            cls.sftp: {
                'port': 22,
                'secret_types': ['password', 'ssh_key'],
                'setting': {
                    'sftp_home': {
                        'type': 'str',
                        'default': '/tmp',
                        'label': _('SFTP root'),
                        'help_text': _(
                            'SFTP root directory, Support variable: <br>'
                            '- ${ACCOUNT} The connected account username <br>'
                            '- ${HOME} The home directory of the connected account <br>'
                            '- ${USER} The username of the user'
                        )
                    }
                }
            },
            cls.rdp: {
                'port': 3389,
                'secret_types': ['password'],
                'setting': {
                    'console': {
                        'type': 'bool',
                        'default': False,
                        'label': _('Console'),
                        'help_text': _("Connect to console session")
                    },
                    'security': {
                        'type': 'choice',
                        'choices': [('any', _('Any')), ('rdp', 'RDP'), ('tls', 'TLS'), ('nla', 'NLA')],
                        'default': 'any',
                        'label': _('Security'),
                        'help_text': _("Security layer to use for the connection")
                    },
                    'ad_domain': {
                        'type': 'str',
                        'required': False,
                        'default': '',
                        'label': _('AD domain')
                    }
                }
            },
            cls.vnc: {
                'port': 5900,
                'secret_types': ['password'],
            },
            cls.telnet: {
                'port': 23,
                'secret_types': ['password'],
                'setting': {
                    'username_prompt': {
                        'type': 'str',
                        'default': 'username:|login:',
                        'label': _('Username prompt'),
                        'help_text': _('We will send username when we see this prompt')
                    },
                    'password_prompt': {
                        'type': 'str',
                        'default': 'password:',
                        'label': _('Password prompt'),
                        'help_text': _('We will send password when we see this prompt')
                    },
                    'success_prompt': {
                        'type': 'str',
                        'default': 'success|成功|#|>|\$',
                        'label': _('Success prompt'),
                        'help_text': _('We will consider login success when we see this prompt')
                    }
                }
            },
            cls.winrm: {
                'port': 5985,
                'secret_types': ['password'],
                'setting': {
                    'use_ssl': {
                        'type': 'bool',
                        'default': False,
                        'label': _('Use SSL')
                    },
                }
            },
        }

    @classmethod
    def database_protocols(cls):
        return {
            cls.mysql: {
                'port': 3306,
                'setting': {},
                'required': True,
                'secret_types': ['password'],
            },
            cls.mariadb: {
                'port': 3306,
                'required': True,
                'secret_types': ['password'],
            },
            cls.postgresql: {
                'port': 5432,
                'required': True,
                'secret_types': ['password'],
                'xpack': True
            },
            cls.oracle: {
                'port': 1521,
                'required': True,
                'secret_types': ['password'],
                'xpack': True,
                'setting': {
                    'sysdba': {
                        'type': 'bool',
                        'default': False,
                        'label': _('SYSDBA'),
                        'help_text': _('Connect as SYSDBA')
                    },
                }
            },
            cls.sqlserver: {
                'port': 1433,
                'required': True,
                'secret_types': ['password'],
                'xpack': True,
                'setting': {
                    'version': {
                        'type': 'choice',
                        'choices': [('>=2014', '>= 2014'), ('<2014', '< 2014')],
                        'default': '>=2014',
                        'label': _('Version'),
                        'help_text': _('SQL Server version, Different versions have different connection drivers')
                    }
                }
            },
            cls.db2: {
                'port': 5000,
                'required': True,
                'secret_types': ['password'],
                'xpack': True,
            },
            cls.clickhouse: {
                'port': 9000,
                'required': True,
                'secret_types': ['password'],
                'xpack': True,
            },
            cls.mongodb: {
                'port': 27017,
                'required': True,
                'secret_types': ['password'],
            },
            cls.redis: {
                'port': 6379,
                'required': True,
                'secret_types': ['password'],
                'setting': {
                    'auth_username': {
                        'type': 'bool',
                        'default': False,
                        'label': _('Auth username')
                    },
                }
            },
        }

    @classmethod
    def cloud_protocols(cls):
        return {
            cls.k8s: {
                'port': 443,
                'port_from_addr': True,
                'required': True,
                'secret_types': ['token'],
            },
            cls.http: {
                'port': 80,
                'port_from_addr': True,
                'secret_types': ['password'],
                'setting': {
                    'safe_mode': {
                        'type': 'bool',
                        'default': False,
                        'label': _('Safe mode'),
                        'help_text': _(
                            'When safe mode is enabled, some operations will be disabled, such as: '
                            'New tab, right click, visit other website, etc.'
                        )
                    },
                    'autofill': {
                        'label': _('Autofill'),
                        'type': 'choice',
                        'choices': FillType.choices,
                        'default': 'basic',
                    },
                    'username_selector': {
                        'type': 'str',
                        'default': 'name=username',
                        'label': _('Username selector')
                    },
                    'password_selector': {
                        'type': 'str',
                        'default': 'name=password',
                        'label': _('Password selector')
                    },
                    'submit_selector': {
                        'type': 'str',
                        'default': 'type=submit',
                        'label': _('Submit selector')
                    },
                    'script': {
                        'type': 'text',
                        'default': [],
                        'label': _('Script'),
                    }
                }
            },
        }

    @classmethod
    def gpt_protocols(cls):
        protocols = {
            cls.chatgpt: {
                'port': 443,
                'required': True,
                'port_from_addr': True,
                'secret_types': ['api_key'],
                'setting': {
                    'api_mode': {
                        'type': 'choice',
                        'default': 'gpt-3.5-turbo',
                        'label': _('API mode'),
                        'choices': [
                            ('gpt-3.5-turbo', 'GPT-3.5 Turbo'),
                            ('gpt-3.5-turbo-16k', 'GPT-3.5 Turbo 16K'),
                        ]
                    }
                }
            }
        }
        if settings.XPACK_LICENSE_IS_VALID:
            choices = protocols[cls.chatgpt]['setting']['api_mode']['choices']
            choices.extend([
                ('gpt-4', 'GPT-4'),
                ('gpt-4-32k', 'GPT-4 32K'),
            ])
        return protocols

    @classmethod
    @cached_method(ttl=600)
    def settings(cls):
        return {
            **cls.device_protocols(),
            **cls.database_protocols(),
            **cls.cloud_protocols(),
            **cls.gpt_protocols(),
        }

    @classmethod
    @cached_method(ttl=600)
    def protocols(cls):
        protocols = []
        xpack_enabled = settings.XPACK_ENABLED
        for protocol, config in cls.settings().items():
            if not xpack_enabled and config.get('xpack', False):
                continue
            protocols.append(protocol)
        return protocols

    @classmethod
    @cached_method(ttl=600)
    def xpack_protocols(cls):
        return [
            protocol for protocol, config in cls.settings().items()
            if config.get('xpack', False)
        ]

    @classmethod
    def protocol_secret_types(cls):
        configs = cls.settings()
        return {
            protocol: configs[protocol]['secret_types'] or ['password']
            for protocol in configs
        }
