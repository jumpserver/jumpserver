from django.db.models import TextChoices
from django.utils.translation import gettext_lazy as _


class Connectivity(TextChoices):
    UNKNOWN = '-', _('Unknown')
    NA = 'na', _('N/A')
    OK = 'ok', _('OK')
    ERR = 'err', _('Error')
    AUTH_ERR = 'auth_err', _('Authentication error')
    SUDO_ERR = 'sudo_err', _('Sudo permission error')
    PASSWORD_ERR = 'password_err', _('Invalid password error')
    OPENSSH_KEY_ERR = 'openssh_key_err', _('OpenSSH key error')
    NTLM_ERR = 'ntlm__err', _('NTLM credentials rejected error')
    CREATE_DIR_ERR = 'create_dir_err', _('Create directory error')


class AutomationTypes(TextChoices):
    ping = 'ping', _('Ping')
    ping_gateway = 'ping_gateway', _('Ping gateway')
    gather_facts = 'gather_facts', _('Gather facts')

    @classmethod
    def get_type_model(cls, tp):
        from assets.models import (
            PingAutomation, GatherFactsAutomation,
        )
        type_model_dict = {
            cls.ping: PingAutomation,
            cls.gather_facts: GatherFactsAutomation,
        }
        return type_model_dict.get(tp)
