import copy
import uuid
from contextlib import nullcontext
from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.test import SimpleTestCase
from rest_framework.exceptions import PermissionDenied
from rest_framework.test import APIRequestFactory, force_authenticate

from terminal.api.session.command import CommandViewSet
from terminal.backends.command.db import CommandStore
from terminal.backends.command.receipt import ComponentCommandReceipt, ReceiptStorageUnavailable
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
        view.action_map = {'post': 'create'}
        view.command_store = SimpleNamespace(
            supports_idempotent_receipts=True, bulk_save=lambda commands: True,
        )
        request = APIRequestFactory().post(
            '/', [self.command], format='json', HTTP_X_JMS_AUDIT_PROTOCOL='1',
        )
        user = component_user()
        force_authenticate(request, user=user)
        request = view.initialize_request(request)
        response = view.create(request)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['event_ids'], [self.command['id']])
        self.assertEqual(response.data['routing'], 'component')
        self.assertEqual(response.data['storage'], {'type': 'server', 'name': 'component-commands'})
        view.command_store.bulk_save = lambda commands: False
        with self.assertRaises(ReceiptStorageUnavailable):
            view.create(request)
        view.command_store.supports_idempotent_receipts = False
        with self.assertRaises(ReceiptStorageUnavailable):
            view.create(request)

    def test_legacy_upload_contract_does_not_require_a_component_or_receipts(self):
        view = CommandViewSet()
        view.action_map = {'post': 'create'}
        view.command_store = SimpleNamespace(bulk_save=Mock(return_value=True))
        request = view.initialize_request(APIRequestFactory().post('/', [self.command], format='json'))
        with patch('terminal.api.session.command.ComponentCommandReceipt') as route:
            response = view.create(request)
        self.assertEqual((response.status_code, response.data), (201, 'ok'))
        route.assert_not_called()
        self.assertNotIn('id', view.command_store.bulk_save.call_args.args[0][0])

    def test_receipt_ignores_untrusted_storage_selectors(self):
        view = CommandViewSet()
        view.action_map = {'post': 'create'}
        view.command_store = Mock()
        request = APIRequestFactory().post(
            '/?command_storage_id=other-component',
            [{**self.command, 'command_storage': 'other-component'}], format='json',
            HTTP_X_JMS_AUDIT_PROTOCOL='1', HTTP_X_JMS_TERMINAL='other-component',
        )
        force_authenticate(request, user=component_user('null'))
        response = view.create(view.initialize_request(request))
        self.assertEqual(response.data['storage'], {'name': 'component-commands', 'type': 'null'})
        self.assertEqual(response.data['disposition'], 'disabled')
        view.command_store.bulk_save.assert_not_called()

    def test_elasticsearch_retry_uses_stable_document_id(self):
        from terminal.backends.command.es import CommandStore as ESCommandStore
        backend = ESCommandStore.__new__(ESCommandStore)
        backend.index, backend.doc_type, backend.es = 'commands', 'command', object()
        from common.plugins.es import ESClientV7
        backend.client = ESClientV7.__new__(ESClientV7)
        backend.is_index_by_date = False
        backend._ensure_receipt_index = lambda index: None
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


def component_user(storage_type='server', **kwargs):
    storage = SimpleNamespace(type=storage_type, config={'TYPE': storage_type, 'INDEX': 'component-index'})
    terminal = SimpleNamespace(
        command_storage='component-commands', is_deleted=False,
        get_command_storage=Mock(return_value=storage),
    )
    return SimpleNamespace(
        is_authenticated=True, is_service_account=True, is_active=True,
        terminal=terminal, **kwargs,
    )


class ComponentRoutingTests(SimpleTestCase):
    def setUp(self):
        self.server = SimpleNamespace(supports_idempotent_receipts=True, bulk_save=Mock(return_value=True))
        self.commands = [{'id': uuid.uuid4()}]

    def test_server_and_missing_config_match_legacy_selection(self):
        user = component_user()
        delivery = ComponentCommandReceipt(user, self.server)
        receipt = delivery.save(self.commands)
        self.assertFalse(receipt['fallback'])
        self.assertEqual(receipt['disposition'], 'stored')
        self.server.bulk_save.assert_called_once_with(self.commands)
        user.terminal.get_command_storage.return_value = None
        self.assertEqual(ComponentCommandReceipt(user, self.server).save([])['storage']['type'], 'server')

    def test_probe_does_not_write(self):
        ComponentCommandReceipt(component_user(), self.server).save([])
        self.server.bulk_save.assert_not_called()

    def test_null_is_explicit_policy_ack_and_never_writes_or_falls_back(self):
        user = component_user('null')
        for commands in ([], self.commands, self.commands):
            receipt = ComponentCommandReceipt(user, self.server).save(commands)
            self.assertEqual(receipt['disposition'], 'disabled')
            self.assertEqual(receipt['event_ids'], [str(c['id']) for c in commands])
            self.assertFalse(receipt['fallback'])
        self.server.bulk_save.assert_not_called()

    def test_es_uses_only_components_raw_config(self):
        user = component_user('es')
        self.server.supports_idempotent_receipts = False
        backend = SimpleNamespace(supports_idempotent_receipts=True, bulk_save=Mock(return_value=True))
        engine = SimpleNamespace(CommandStore=Mock(return_value=backend))
        with patch('terminal.backends.command.receipt.import_module', return_value=engine):
            delivery = ComponentCommandReceipt(user, self.server)
            delivery.save([])
            backend.bulk_save.assert_not_called()
            receipt = delivery.save(self.commands)
        engine.CommandStore.assert_called_with(user.terminal.get_command_storage().config)
        self.assertEqual(receipt['storage']['type'], 'es')
        self.assertFalse(receipt['fallback'])
        backend.bulk_save.assert_called_once_with(self.commands)
        self.server.bulk_save.assert_not_called()

    def test_es_failure_falls_back_but_ack_names_actual_storage(self):
        backend = SimpleNamespace(supports_idempotent_receipts=True, bulk_save=Mock(return_value=False))
        engine = SimpleNamespace(CommandStore=Mock(return_value=backend))
        with patch('terminal.backends.command.receipt.import_module', return_value=engine):
            receipt = ComponentCommandReceipt(component_user('es'), self.server).save(self.commands)
        self.assertTrue(receipt['fallback'])
        self.assertEqual(receipt['selected_storage']['type'], 'es')
        self.assertEqual(receipt['storage'], {'name': 'default', 'type': 'server'})
        self.server.bulk_save.assert_called_once_with(self.commands)

    def test_both_stores_failing_never_acknowledges(self):
        self.server.bulk_save.return_value = False
        with patch('terminal.backends.command.receipt.import_module', side_effect=RuntimeError('credentials must not be logged')):
            with self.assertLogs('jumpserver.terminal.backends.command.receipt', level='WARNING') as logs:
                with self.assertRaises(ReceiptStorageUnavailable):
                    ComponentCommandReceipt(component_user('es'), self.server).save(self.commands)
        self.assertNotIn('credentials must not be logged', ''.join(logs.output))

    def test_unsupported_backend_never_acknowledges(self):
        with self.assertRaises(ReceiptStorageUnavailable):
            ComponentCommandReceipt(component_user('unknown'), self.server).save([])
        self.server.bulk_save.assert_not_called()

    def test_only_authenticated_live_component_can_request_routing(self):
        for field in ('is_authenticated', 'is_service_account', 'is_active'):
            user = component_user()
            setattr(user, field, False)
            with self.assertRaises(PermissionDenied):
                ComponentCommandReceipt(user, self.server)
        user = component_user()
        user.terminal.is_deleted = True
        with self.assertRaises(PermissionDenied):
            ComponentCommandReceipt(user, self.server)
        user.terminal = None
        with self.assertRaises(PermissionDenied):
            ComponentCommandReceipt(user, self.server)

    def test_es_receipt_bulk_uses_matching_client_and_checks_partial_errors(self):
        from common.plugins.es import ESClientV6, ESClientV7, ESClientV8
        from terminal.backends.command.es import CommandStore as ESCommandStore
        for client_class, helper in ((ESClientV6, 'bulk'), (ESClientV7, 'bulk'), (ESClientV8, 'bulk8')):
            backend = ESCommandStore.__new__(ESCommandStore)
            backend.client = client_class.__new__(client_class)
            backend.index, backend.doc_type, backend.es = 'commands', 'command', object()
            backend.is_index_by_date = False
            backend._ensure_receipt_index = Mock()
            backend.make_data = copy.deepcopy
            with patch('terminal.backends.command.es.' + helper, return_value=(1, [])) as bulk:
                self.assertTrue(backend.bulk_save(self.commands))
                action = bulk.call_args.args[1][0]
                self.assertEqual('_type' in action, client_class is ESClientV6)
                bulk.return_value = (0, [{'error': 'injected'}])
                self.assertFalse(backend.bulk_save(self.commands, raise_on_error=False))
