import copy

from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from accounts.const import SecretType, DEFAULT_PASSWORD_RULES
from common.utils import ssh_key_gen, random_string
from common.utils import validate_ssh_private_key, parse_ssh_private_key_str


class SecretGenerator:
    def __init__(self, secret_strategy, secret_type, password_rules=None):
        self.secret_strategy = secret_strategy
        self.secret_type = secret_type
        self.password_rules = password_rules

    @staticmethod
    def generate_ssh_key():
        private_key, __ = ssh_key_gen()
        return private_key

    def generate_password(self):
        password_rules = self.password_rules
        if not password_rules or not isinstance(password_rules, dict):
            password_rules = {}
        rules = copy.deepcopy(DEFAULT_PASSWORD_RULES)
        rules.update(password_rules)
        rules = {
            'length': rules['length'],
            'lower': rules['lowercase'],
            'upper': rules['uppercase'],
            'digit': rules['digit'],
            'special_char': rules['symbol'],
            'exclude_chars': rules.get('exclude_symbols', ''),
        }
        return random_string(**rules)

    def get_secret(self):
        if self.secret_type == SecretType.SSH_KEY:
            secret = self.generate_ssh_key()
        elif self.secret_type == SecretType.PASSWORD:
            secret = self.generate_password()
        else:
            raise ValueError("Secret must be set")
        return secret


def validate_password_for_ansible(password):
    """ 校验 Ansible 不支持的特殊字符 """
    if password.startswith('{{') and password.endswith('}}'):
        raise serializers.ValidationError(
            _('If the password starts with {{` and ends with }} `, then the password is not allowed.')
        )


def validate_ssh_key(ssh_key, passphrase=None):
    valid = validate_ssh_private_key(ssh_key, password=passphrase)
    if not valid:
        raise serializers.ValidationError(_("private key invalid or passphrase error"))
    return parse_ssh_private_key_str(ssh_key, passphrase)
