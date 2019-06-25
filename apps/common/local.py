# -*- coding: utf-8 -*-
#
from werkzeug.local import Local

thread_local = Local()


def _find(attr):
    return getattr(thread_local, attr, None)
