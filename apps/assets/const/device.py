from django.utils.translation import gettext_lazy as _

from .base import BaseType


class DeviceTypes(BaseType):
    CISCO = 'cisco', _("Cisco")
    HUAWEI = 'huawei', _("Huawei")
    H3C = 'h3c', _("H3C")
    JUNIPER = 'juniper', _("Juniper")
    TP_LINK = 'tp_link', _("TP-Link")
    GENERAL = 'general', _("General")
    SWITCH = 'switch', _("Switch")
    ROUTER = 'router', _("Router")
    FIREWALL = 'firewall', _("Firewall")

    @classmethod
    def _get_base_constrains(cls) -> dict:
        return {
            '*': {
                'charset_enabled': False,
                'gateway_enabled': True,
                'ds_enabled': False,
                'su_enabled': True,
                'su_methods': ['enable', 'super', 'super_level']
            }
        }

    @classmethod
    def _get_protocol_constrains(cls) -> dict:
        return {
            '*': {
                'choices': ['ssh', 'telnet', 'sftp']
            }
        }

    @classmethod
    def _get_automation_constrains(cls) -> dict:
        return {
            '*': {
                'ansible_enabled': True,
                'ansible_config': {
                    'ansible_connection': 'local'
                },
                'ping_enabled': True,
                'gather_facts_enabled': False,
                'gather_accounts_enabled': False,
                'verify_account_enabled': True,
                'change_secret_enabled': True,
                'push_account_enabled': False,
                'remove_account_enabled': False,
            }
        }

    @classmethod
    def internal_platforms(cls):
        return {
            cls.GENERAL: [{'name': 'General'}, {'name': 'Cisco'}, {'name': 'Huawei'}, {'name': 'H3C'}],
            cls.SWITCH: [],
            cls.ROUTER: [],
            cls.FIREWALL: []
        }

    @classmethod
    def get_community_types(cls):
        return [
            cls.GENERAL, cls.SWITCH, cls.ROUTER, cls.FIREWALL
        ]
