import re

from werkzeug.local import Local


thread_local = Local()
exclude_encrypted_fields = ('secret_type', 'secret_strategy', 'password_rules')
similar_encrypted_pattern = re.compile(
    'password|secret|token|passphrase|private|key|cert', re.IGNORECASE
)


def _find(attr):
    return getattr(thread_local, attr, None)
