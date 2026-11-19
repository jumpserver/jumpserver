"""Opt-in PostgreSQL storage regression on an ISOLATED test database only."""
import copy
import os
import unittest
import uuid
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace
from unittest.mock import patch

from django.db import connections, models, transaction
from django.test.utils import isolate_apps

from terminal.backends.command.db import CommandStore
from terminal.backends.command.models import AbstractSessionCommand


@unittest.skipUnless(os.getenv('MAGNUS_RECEIPT_TEST_PG_PORT'), 'requires isolated receipt-test PostgreSQL')
class ReceiptORMTests(unittest.TestCase):
    @isolate_apps()
    def test_concurrent_retries_and_transactional_conflict(self):
        # No migrations, dev database writes or existing tables. The test
        # database must be explicitly supplied; never reuse business databases.
        alias = 'magnus_receipt_fixture'
        config = copy.deepcopy(connections['default'].settings_dict)
        config.update(
            ENGINE='django.db.backends.postgresql', HOST='127.0.0.1',
            PORT=os.environ['MAGNUS_RECEIPT_TEST_PG_PORT'],
            NAME='postgres', USER='postgres', PASSWORD='', OPTIONS={},
        )
        connections.databases[alias] = config

        class Fixture(AbstractSessionCommand):
            objects = models.Manager()

            class Meta:
                app_label = 'receipt_test'
                db_table = 'magnus_receipt_fixture'

        connection = connections[alias]
        with connection.schema_editor() as schema:
            schema.create_model(Fixture)
        original_atomic = transaction.atomic
        store = CommandStore.__new__(CommandStore)
        store.model = SimpleNamespace(objects=Fixture.objects.db_manager(alias))
        command = dict(
            id=uuid.uuid4(), session=str(uuid.uuid4()), org_id='00000000-0000-0000-0000-000000000002',
            user='test', asset='test-db', account='test', input='SELECT 42',
            output='42', timestamp=1793865600, risk_level=0,
        )

        def save(_):
            try:
                return store.bulk_save([command])
            finally:
                connections[alias].close()

        try:
            with patch('terminal.backends.command.db.transaction.atomic', side_effect=lambda *args, **kwargs: original_atomic(using=alias)):
                with ThreadPoolExecutor(max_workers=8) as pool:
                    self.assertTrue(all(pool.map(save, range(16))))
                self.assertEqual(Fixture.objects.using(alias).count(), 1)
                self.assertTrue(store.bulk_save([{**command, 'id': uuid.uuid4()}]))
                self.assertEqual(Fixture.objects.using(alias).count(), 2)
                new_id = uuid.uuid4()
                self.assertFalse(store.bulk_save([
                    {**command, 'id': new_id}, {**command, 'input': 'SELECT 99'},
                ]))
                self.assertFalse(Fixture.objects.using(alias).filter(id=new_id).exists())
        finally:
            with connection.schema_editor() as schema:
                schema.delete_model(Fixture)
            connection.close()
            del connections[alias]
            del connections.databases[alias]
