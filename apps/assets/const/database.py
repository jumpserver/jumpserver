

class DatabaseTypes(ConstrainMixin, ChoicesMixin, models.TextChoices):
    MYSQL = 'mysql', 'MySQL'
    MARIADB = 'mariadb', 'MariaDB'
    POSTGRESQL = 'postgresql', 'PostgreSQL'
    ORACLE = 'oracle', 'Oracle'
    SQLSERVER = 'sqlserver', 'SQLServer'
    MONGODB = 'mongodb', 'MongoDB'
    REDIS = 'redis', 'Redis'

    def category_constrains(self):
        return {
            'domain_enabled': True,
            'su_enabled': False,
            'gather_facts_enabled': True,
            'verify_account_enabled': True,
            'change_password_enabled': True,
            'create_account_enabled': True,
            'gather_accounts_enabled': True,
            '_protocols': []
        }

    @classmethod
    def platform_constraints(cls):
        meta = {}
        for name, label in cls.choices:
            meta[name] = {
                '_protocols': [name],
                'gather_facts_method': f'gather_facts_{name}',
                'verify_account_method': f'verify_account_{name}',
                'change_password_method': f'change_password_{name}',
                'create_account_method': f'create_account_{name}',
                'gather_accounts_method': f'gather_accounts_{name}',
            }
        return meta
