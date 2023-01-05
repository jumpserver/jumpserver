from accounts.const import (
    SecretType, SecretStrategy, DEFAULT_PASSWORD_RULES
)
from common.utils import gen_key_pair, random_string


class SecretGenerator:
    def __init__(self, secret_strategy, secret_type, password_rules=None):
        self.secret_strategy = secret_strategy
        self.secret_type = secret_type
        self.password_rules = password_rules
        self._ssh_key_generated = None
        self._password_generated = None

    @staticmethod
    def generate_ssh_key():
        private_key, public_key = gen_key_pair()
        return private_key

    def generate_password(self):
        length = int(self.password_rules.get('length', DEFAULT_PASSWORD_RULES['length']))
        return random_string(length, special_char=True)

    def get_ssh_key(self):
        if self.secret_strategy == SecretStrategy.random_one:
            if not self._ssh_key_generated:
                self._ssh_key_generated = self.generate_ssh_key()
            return self._ssh_key_generated
        else:
            return self.generate_ssh_key()

    def get_password(self):
        if self.secret_strategy == SecretStrategy.random_one:
            if not self._password_generated:
                self._password_generated = self.generate_password()
            return self._password_generated
        else:
            return self.generate_password()

    def get_secret(self):
        if self.secret_type == SecretType.SSH_KEY:
            secret = self.get_ssh_key()
        elif self.secret_type == SecretType.PASSWORD:
            secret = self.get_password()
        else:
            raise ValueError("Secret must be set")
        return secret
