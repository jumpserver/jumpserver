
class WebTypes(ConstrainMixin, ChoicesMixin, models.TextChoices):
    WEBSITE = 'website', _('General website')

    def category_constrains(self):
        return {
            'domain_enabled': False,
            'su_enabled': False,
            'ping_enabled': False,
            'gather_facts_enabled': False,
            'verify_account_enabled': False,
            'change_password_enabled': False,
            'create_account_enabled': False,
            'gather_accounts_enabled': False,
            '_protocols': ['http', 'https']
        }