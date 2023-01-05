from accounts.const import (
    SecretType, DEFAULT_PASSWORD_RULES
)
from common.utils import gen_key_pair, random_string


class SecretGenerator:
    def __init__(self, secret_strategy, secret_type, password_rules=None):
        self.secret_strategy = secret_strategy
        self.secret_type = secret_type
        self.password_rules = password_rules

    @staticmethod
    def generate_ssh_key():
        private_key, public_key = gen_key_pair()
        return private_key

    def generate_password(self):
        length = int(self.password_rules.get('length', DEFAULT_PASSWORD_RULES['length']))
        return random_string(length, special_char=True)

    def get_secret(self):
        if self.secret_type == SecretType.SSH_KEY:
            secret = self.generate_ssh_key()
        elif self.secret_type == SecretType.PASSWORD:
            secret = self.generate_password()
        else:
            raise ValueError("Secret must be set")
        return secret
