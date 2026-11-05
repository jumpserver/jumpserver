import copy
import uuid
from contextlib import nullcontext
from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase
from rest_framework.request import Request
from rest_framework.test import APIRequestFactory

from terminal.api.session.command import CommandViewSet
from terminal.backends.command.db import CommandStore
from terminal.serializers.command import SessionCommandReceiptSerializer, SessionCommandSerializer


class ReceiptTests(SimpleTestCase):
    def setUp(self):
        self.command = dict(
            id=str(uuid.uuid4()), session=str(uuid.uuid4()), org_id='',
            user='test', asset='test-db', account='test', input='SELECT 42',
            output='42', timestamp=1793865600, risk_level=0,
        )

    def test_only_receipt_serializer_accepts_a_stable_id(self):
        serializer = SessionCommandReceiptSerializer(data=self.command)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(str(serializer.validated_data['id']), self.command['id'])
        legacy = SessionCommandSerializer(data=self.command)
        self.assertTrue(legacy.is_valid(), legacy.errors)
        self.assertNotIn('id', legacy.validated_data)
        command = {k: v for k, v in self.command.items() if k != 'id'}
        self.assertFalse(SessionCommandReceiptSerializer(data=command).is_valid())

    def test_retry_uses_unique_id_and_different_content_is_not_overwritten(self):
        rows = {}

        def get_or_create(id, defaults):
            if id in rows:
                return rows[id], False
            rows[id] = SimpleNamespace(**defaults)
            return rows[id], True

        manager = SimpleNamespace(get_or_create=get_or_create)
        store = CommandStore.__new__(CommandStore)
        store.model = SimpleNamespace(objects=manager)
        with patch('terminal.backends.command.db.transaction.atomic', side_effect=lambda: nullcontext()):
            self.assertTrue(store.bulk_save([self.command]))
            self.assertTrue(store.bulk_save([self.command]))
            self.assertEqual(len(rows), 1)
            changed = {**self.command, 'input': 'SELECT 99'}
            self.assertFalse(store.bulk_save([changed]))
            self.assertEqual(next(iter(rows.values())).input, 'SELECT 42')
            another_execution = {**self.command, 'id': str(uuid.uuid4())}
            self.assertTrue(store.bulk_save([another_execution]))
            self.assertEqual(len(rows), 2)

    def test_endpoint_requires_storage_commit_and_returns_exact_ids(self):
        view = CommandViewSet()
        # Invoke create directly: authentication/RBAC are unchanged by this fix.
        view.action_map = {'post': 'create'}
        view.command_store = SimpleNamespace(
            supports_idempotent_receipts=True, bulk_save=lambda commands: True,
        )
        request = Request(APIRequestFactory().post(
            '/', [self.command], format='json', HTTP_X_JMS_AUDIT_PROTOCOL='1',
        ), parsers=CommandViewSet.parser_classes)
        # APIView normally instantiates parsers during initialize_request.
        request = view.initialize_request(request._request)
        response = view.create(request)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data, {'audit_protocol': 1, 'event_ids': [self.command['id']]})
        view.command_store.bulk_save = lambda commands: False
        self.assertEqual(view.create(request).status_code, 500)
        view.command_store.supports_idempotent_receipts = False
        self.assertEqual(view.create(request).status_code, 503)

    def test_elasticsearch_retry_uses_stable_document_id(self):
        from terminal.backends.command.es import CommandStore as ESCommandStore
        backend = ESCommandStore.__new__(ESCommandStore)
        backend.index, backend.doc_type, backend.es = 'commands', 'command', object()
        backend.is_index_by_date = False
        backend.make_data = lambda command: copy.deepcopy(command)
        with patch('terminal.backends.command.es.bulk', return_value=(1, [])) as bulk:
            backend.bulk_save([self.command])
        self.assertEqual(bulk.call_args.args[1][0]['_id'], self.command['id'])
        backend.is_index_by_date, backend.index_prefix = True, 'commands'
        backend._ensure_receipt_index = lambda index: None
        with patch('terminal.backends.command.es.bulk', return_value=(1, [])) as bulk:
            backend.bulk_save([self.command])
            before = bulk.call_args.args[1][0]['_index']
            backend.index = 'commands-a-different-upload-day'
            backend.bulk_save([self.command])
            self.assertEqual(bulk.call_args.args[1][0]['_index'], before)
