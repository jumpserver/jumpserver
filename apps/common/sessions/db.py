from django.contrib.sessions.backends.db import SessionStore as DjangoSessionStore

from . import SessionSaveMixin


class SessionStore(SessionSaveMixin, DjangoSessionStore):
    pass
