from werkzeug.local import Local

from django.utils import translation


thread_local = Local()
encrypted_field_set = {'password', 'secret'}


def _find(attr):
    return getattr(thread_local, attr, None)


def add_encrypted_field_set(label):
    if label:
        with translation.override('en'):
            encrypted_field_set.add(str(label))
