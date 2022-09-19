
class HostTypes(ConstrainMixin, ChoicesMixin, models.TextChoices):
    LINUX = 'linux', 'Linux'
    WINDOWS = 'windows', 'Windows'
    UNIX = 'unix', 'Unix'
    OTHER_HOST = 'other', _("Other")

    @staticmethod
    def category_constrains():
        return {
            'domain_enabled': True,
            'su_enabled': True, 'su_method': 'sudo',
            'ping_enabled': True, 'ping_method': 'ping',
            'gather_facts_enabled': True, 'gather_facts_method': 'gather_facts_posix',
            'verify_account_enabled': True, 'verify_account_method': 'verify_account_posix',
            'change_password_enabled': True, 'change_password_method': 'change_password_posix',
            'create_account_enabled': True, 'create_account_method': 'create_account_posix',
            'gather_accounts_enabled': True, 'gather_accounts_method': 'gather_accounts_posix',
            '_protocols': ['ssh', 'telnet'],
        }

    @classmethod
    def platform_constraints(cls):
        return {
            cls.LINUX: {
                '_protocols': ['ssh', 'rdp', 'vnc', 'telnet']
            },
            cls.WINDOWS: {
                'gather_facts_method': 'gather_facts_windows',
                'verify_account_method': 'verify_account_windows',
                'change_password_method': 'change_password_windows',
                'create_account_method': 'create_account_windows',
                'gather_accounts_method': 'gather_accounts_windows',
                '_protocols': ['rdp', 'ssh', 'vnc'],
                'su_enabled': False
            },
            cls.UNIX: {
                '_protocols': ['ssh', 'vnc']
            }
        }