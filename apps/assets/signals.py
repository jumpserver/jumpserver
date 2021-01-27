# -*- coding: utf-8 -*-
#

from django.dispatch import Signal


org_asset_tree_change = Signal(providing_args=['action', 'org_id'])
