"""Shared source bundle rules for Core and standalone client releases."""
from pathlib import Path

from django.conf import settings
from rest_framework.exceptions import NotFound

from accounts.clients.distribution import SOURCE_FILES, source_archive as build_source_archive


def source_archive(language):
    if language not in SOURCE_FILES:
        raise NotFound()
    root = Path(settings.APPS_DIR) / 'accounts' / 'clients'
    try:
        return build_source_archive(language, root)
    except ValueError as error:
        raise NotFound() from error
