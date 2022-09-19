

class ConstrainMixin:
    def get_constrains(self):
        pass

    def _get_category_constrains(self) -> dict:
        raise NotImplementedError

    def _get_protocol_constrains(self) -> dict:
        raise NotImplementedError

    def _get_automation_constrains(self) -> dict:
        raise NotImplementedError

    @classmethod
    def platform_constraints(cls):
        return {
            'domain_enabled': False,
            'su_enabled': False,
            'brand_enabled': False,
            'ping_enabled': False,
            'gather_facts_enabled': False,
            'change_password_enabled': False,
            'verify_account_enabled': False,
            'create_account_enabled': False,
            'gather_accounts_enabled': False,
            '_protocols': []
        }

