
from .base import BaseType


class DatabaseTypes(BaseType):
    MYSQL = 'mysql', 'MySQL'
    MARIADB = 'mariadb', 'MariaDB'
    POSTGRESQL = 'postgresql', 'PostgreSQL'
    ORACLE = 'oracle', 'Oracle'
    SQLSERVER = 'sqlserver', 'SQLServer'
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
                'gather_facts_enabled': True,
                'gather_accounts_enabled': True,
                'verify_account_enabled': True,
                'change_password_enabled': True,
                'create_account_enabled': True,
            }
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
            cls.MONGODB: [{'name': 'MongoDB'}],
            cls.REDIS: [{'name': 'Redis'}],
        }

