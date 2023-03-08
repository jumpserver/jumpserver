from werkzeug.local import Local

thread_local = Local()
encrypted_field_set = {'password'}


def _find(attr):
    return getattr(thread_local, attr, None)


def add_encrypted_field_set(label):
    if label:
        encrypted_field_set.add(str(label))
