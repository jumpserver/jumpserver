# -*- coding: utf-8 -*-
#

from django.dispatch import Signal

django_ready = Signal()
ldap_auth_enable = Signal(providing_args=["enabled"])
