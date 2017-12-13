# -*- coding: utf-8 -*-
#
from django.dispatch import Signal

on_app_ready = Signal()
on_system_user_auth_changed = Signal(providing_args=['system_user'])
