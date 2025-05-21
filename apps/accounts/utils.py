import copy

from django.conf import settings
from django.core.cache import cache
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
            "length": rules["length"],
            "lower": rules["lowercase"],
            "upper": rules["uppercase"],
            "digit": rules["digit"],
            "special_char": rules["symbol"],
            "exclude_chars": rules.get("exclude_symbols", ""),
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
    """校验 Ansible 不支持的特殊字符"""
    if password.startswith("{{") and password.endswith("}}"):
        raise serializers.ValidationError(
            _(
                "If the password starts with {{` and ends with }} `, then the password is not allowed."
            )
        )


def validate_ssh_key(ssh_key, passphrase=None):
    valid = validate_ssh_private_key(ssh_key, password=passphrase)
    if not valid:
        raise serializers.ValidationError(_("private key invalid or passphrase error"))
    return parse_ssh_private_key_str(ssh_key, passphrase)


class AccountSecretTaskStatus:

    def __init__(
            self,
            prefix='queue:change_secret:',
            debounce_key='debounce:change_secret:task',
            debounce_timeout=10,
            queue_status_timeout=35,
            default_timeout=3600,
            delayed_task_countdown=20,
    ):
        self.prefix = prefix
        self.debounce_key = debounce_key
        self.debounce_timeout = debounce_timeout
        self.queue_status_timeout = queue_status_timeout
        self.default_timeout = default_timeout
        self.delayed_task_countdown = delayed_task_countdown
        self.enabled = getattr(settings, 'CHANGE_SECRET_AFTER_SESSION_END', False)

    def _key(self, identifier):
        return f"{self.prefix}{identifier}"

    @property
    def account_ids(self):
        for key in cache.iter_keys(f"{self.prefix}*"):
            yield key.split(':')[-1]

    def is_debounced(self):
        return cache.add(self.debounce_key, True, self.debounce_timeout)

    def get_queue_key(self, identifier):
        return self._key(identifier)

    def set_status(
            self,
            identifier,
            status,
            timeout=None,
            metadata=None,
            use_add=False
    ):
        if not self.enabled:
            return

        key = self._key(identifier)
        data = {"status": status}
        if metadata:
            data.update(metadata)

        if use_add:
            return cache.set(key, data, timeout or self.queue_status_timeout)

        cache.set(key, data, timeout or self.default_timeout)

    def get(self, identifier):
        return cache.get(self._key(identifier), {})

    def get_status(self, identifier):
        if not self.enabled:
            return

        record = cache.get(self._key(identifier), {})
        return record.get("status")

    def get_ttl(self, identifier):
        return cache.ttl(self._key(identifier))

    def clear(self, identifier):
        if not self.enabled:
            return

        cache.delete(self._key(identifier))


account_secret_task_status = AccountSecretTaskStatus()
