"""Synchronous receipts for component command uploads, not legacy uploads."""
from importlib import import_module

from django.core.exceptions import ObjectDoesNotExist
from rest_framework.exceptions import APIException, PermissionDenied

from common.utils import get_logger
from terminal.backends import TYPE_ENGINE_MAPPING

logger = get_logger(__name__)


class ReceiptStorageUnavailable(APIException):
    status_code = 503
    default_detail = 'Command storage cannot confirm durable audit receipts'
    default_code = 'audit_storage_unavailable'


class ComponentCommandReceipt:
    def __init__(self, user, server_store):
        # Wisp signs CallAPI with its component service account. Never accept a
        # terminal/storage identifier from request data, headers or query args.
        if not (user.is_authenticated and user.is_service_account and user.is_active):
            raise PermissionDenied('Audit receipts require a component service account')
        try:
            terminal = user.terminal
        except ObjectDoesNotExist:
            raise PermissionDenied('Component terminal is unavailable')
        if terminal is None or terminal.is_deleted:
            raise PermissionDenied('Component terminal is unavailable')
        storage = terminal.get_command_storage()
        self.server_store = server_store
        self.storage = storage
        # Match Terminal.get_command_storage_config / the legacy uploader:
        # a missing configuration resolves to the server backend.
        self.selected = {
            'name': terminal.command_storage,
            'type': storage.type if storage else 'server',
        }

    @staticmethod
    def _supports_receipts(store):
        if not getattr(store, 'supports_idempotent_receipts', False):
            raise ReceiptStorageUnavailable()

    @classmethod
    def _save(cls, store, commands):
        cls._supports_receipts(store)
        # An empty batch is a non-writing capability probe.
        if commands and not store.bulk_save(commands):
            raise ReceiptStorageUnavailable()

    def save(self, commands):
        selected_type = self.selected['type']
        actual, fallback = self.selected, False
        disposition = 'stored'
        if selected_type == 'null':
            # Explicit policy acknowledgement, NOT a claim of persistence.
            disposition = 'disabled'
        elif selected_type == 'server':
            self._save(self.server_store, commands)
        elif selected_type in TYPE_ENGINE_MAPPING:
            try:
                engine = import_module(TYPE_ENGINE_MAPPING[selected_type])
                # valid_config expands INDEX to today's date. Use the raw
                # config so retries continue to use the event's stable day.
                store = engine.CommandStore(self.storage.config)
                self._save(store, commands)
            except Exception as exc:
                # Preserve Wisp's existing non-server -> server fallback.
                # Never log configuration/credentials/SQL from the exception.
                logger.warning('Component command storage failed; trying server (%s)', type(exc).__name__)
                actual, fallback = {'name': 'default', 'type': 'server'}, True
                self._save(self.server_store, commands)
        else:
            raise ReceiptStorageUnavailable()
        return {
            'audit_protocol': 1,
            'routing': 'component',
            'event_ids': [str(command['id']) for command in commands],
            'disposition': disposition,
            'selected_storage': self.selected,
            'storage': actual,
            'fallback': fallback,
        }
