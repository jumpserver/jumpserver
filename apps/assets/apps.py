from __future__ import unicode_literals
from django.utils.translation import ugettext as _

from django.apps import AppConfig


class AssetsConfig(AppConfig):
    name = 'assets'
    verbose_name = 'Fancy Title'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def ready(self):
        super().ready()
        from . import signals_handler
