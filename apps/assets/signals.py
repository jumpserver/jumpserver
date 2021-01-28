# -*- coding: utf-8 -*-
#

from django.dispatch import Signal


tree_destroy_signal = Signal(providing_args=['org_id'])
