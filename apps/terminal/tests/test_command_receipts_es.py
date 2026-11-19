"""Opt-in real ES integration; uses and removes only uniquely named test indices."""
import os
import unittest
import uuid
from types import SimpleNamespace

from terminal.backends.command.receipt import ComponentCommandReceipt
from terminal.backends.command.es import CommandStore as ESCommandStore


@unittest.skipUnless(os.getenv('MAGNUS_RECEIPT_TEST_ES_HOST'), 'requires receipt-test Elasticsearch')
class ReceiptESTests(unittest.TestCase):
    def test_component_selected_es_retries_and_stable_day(self):
        prefix = 'magnus-receipt-test-' + uuid.uuid4().hex
        command = dict(
            id=str(uuid.uuid4()), session=str(uuid.uuid4()), org_id='',
            user='receipt-test', asset='test-only', account='test-only',
            input='SELECT 42', output='42', timestamp=1704067200, risk_level=0,
        )
        for dated in (False, True):
            index = prefix + ('-dated' if dated else '-fixed')
            config = {
                'TYPE': 'es', 'HOSTS': [os.environ['MAGNUS_RECEIPT_TEST_ES_HOST']],
                'INDEX': index, 'INDEX_BY_DATE': dated,
                'OTHER': {'http_auth': (
                    os.environ.get('MAGNUS_RECEIPT_TEST_ES_USER', ''),
                    os.environ.get('MAGNUS_RECEIPT_TEST_ES_PASSWORD', ''),
                )},
            }
            target_index = index + '-2024-01-01' if dated else index
            backend = ESCommandStore(config)
            storage = SimpleNamespace(type='es', config=config)
            terminal = SimpleNamespace(
                command_storage=index, is_deleted=False,
                get_command_storage=lambda: storage,
            )
            user = SimpleNamespace(
                is_authenticated=True, is_active=True, is_service_account=True, terminal=terminal,
            )
            server = SimpleNamespace(
                supports_idempotent_receipts=True,
                bulk_save=lambda commands: self.fail('Unexpected fallback to server'),
            )
            try:
                for _ in range(2):
                    receipt = ComponentCommandReceipt(user, server).save([command])
                    self.assertFalse(receipt['fallback'])
                    self.assertEqual(receipt['storage']['name'], index)
                    self.assertEqual(receipt['event_ids'], [command['id']])
                backend.es.indices.refresh(index=target_index)
                self.assertEqual(backend.es.count(index=target_index)['count'], 1)
                self.assertEqual(backend.es.get(index=target_index, id=command['id'])['_source']['output'], '42')
                ComponentCommandReceipt(user, server).save([{**command, 'id': str(uuid.uuid4())}])
                backend.es.indices.refresh(index=target_index)
                self.assertEqual(backend.es.count(index=target_index)['count'], 2)
            finally:
                # Exact target only; never delete a wildcard or business index.
                backend.es.indices.delete(index=target_index, ignore_unavailable=True)
                backend.es.close()
