from .base import BaseType


class DatabaseTypes(BaseType):
    MYSQL = 'mysql', 'MySQL'
    MARIADB = 'mariadb', 'MariaDB'
    POSTGRESQL = 'postgresql', 'PostgreSQL'
    ORACLE = 'oracle', 'Oracle'
    SQLSERVER = 'sqlserver', 'SQLServer'
    DB2 = 'db2', 'DB2'
    CLICKHOUSE = 'clickhouse', 'ClickHouse'
    MONGODB = 'mongodb', 'MongoDB'
    REDIS = 'redis', 'Redis'

    @classmethod
    def _get_base_constrains(cls) -> dict:
        return {
            '*': {
                'charset_enabled': False,
                'domain_enabled': True,
                'su_enabled': False,
            }
        }

    @classmethod
    def _get_automation_constrains(cls) -> dict:
        constrains = {
            '*': {
                'ansible_enabled': True,
                'ansible_config': {
                    'ansible_connection': 'local',
                },
                'ping_enabled': True,
                'gather_facts_enabled': False,
                'gather_accounts_enabled': True,
                'verify_account_enabled': True,
                'change_secret_enabled': True,
                'push_account_enabled': True,
            },
            cls.REDIS: {
                'ansible_enabled': False,
                'ping_enabled': False,
                'gather_facts_enabled': False,
                'gather_accounts_enabled': False,
                'verify_account_enabled': False,
                'change_secret_enabled': False,
                'push_account_enabled': False,
            },
            cls.DB2: {
                'ansible_enabled': False,
                'ping_enabled': False,
                'gather_facts_enabled': False,
                'gather_accounts_enabled': False,
                'verify_account_enabled': False,
                'change_secret_enabled': False,
                'push_account_enabled': False,
            },
            cls.CLICKHOUSE: {
                'ansible_enabled': False,
                'ping_enabled': False,
                'gather_facts_enabled': False,
                'gather_accounts_enabled': False,
                'verify_account_enabled': False,
                'change_secret_enabled': False,
                'push_account_enabled': False,
            },
        }
        return constrains

    @classmethod
    def _get_protocol_constrains(cls) -> dict:
        return {
            '*': {
                'choices': '__self__',
            }
        }

    @classmethod
    def internal_platforms(cls):
        return {
            cls.MYSQL: [{'name': 'MySQL'}],
            cls.MARIADB: [{'name': 'MariaDB'}],
            cls.POSTGRESQL: [{'name': 'PostgreSQL'}],
            cls.ORACLE: [{'name': 'Oracle'}],
            cls.SQLSERVER: [{'name': 'SQLServer'}],
            cls.DB2: [{'name': 'DB2'}],
            cls.CLICKHOUSE: [{'name': 'ClickHouse'}],
            cls.MONGODB: [{'name': 'MongoDB'}],
            cls.REDIS: [
                {
                    'name': 'Redis',
                    'protocols_setting': {
                        'redis': {'auth_username': False}
                    }
                },
                {
                    'name': 'Redis6+',
                    'protocols_setting': {
                        'redis': {'auth_username': True}
                    }
                }
            ]
        }

    @classmethod
    def get_community_types(cls):
        return [
            cls.MYSQL, cls.MARIADB, cls.MONGODB, cls.REDIS
        ]
