

class DeviceTypes(ConstrainMixin, ChoicesMixin, models.TextChoices):
    GENERAL = 'general', _("General device")
    SWITCH = 'switch', _("Switch")
    ROUTER = 'router', _("Router")
    FIREWALL = 'firewall', _("Firewall")

    @classmethod
    def category_constrains(cls):
        return {
            'domain_enabled': True,
            'brand_enabled': True,
            'brands': [
                ('huawei', 'Huawei'),
                ('cisco', 'Cisco'),
                ('juniper', 'Juniper'),
                ('h3c', 'H3C'),
                ('dell', 'Dell'),
                ('other', 'Other'),
            ],
            'su_enabled': False,
            'ping_enabled': True, 'ping_method': 'ping',
            'gather_facts_enabled': False,
            'verify_account_enabled': False,
            'change_password_enabled': False,
            'create_account_enabled': False,
            'gather_accounts_enabled': False,
            '_protocols': ['ssh', 'telnet']
        }
