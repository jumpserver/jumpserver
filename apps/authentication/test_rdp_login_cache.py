"""Exercise ticket expiry and atomic consumption against an isolated Redis."""
import secrets
import shutil
import subprocess
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import timedelta
from pathlib import Path
from unittest import SkipTest
from unittest.mock import patch
from uuid import uuid4

from django.test import SimpleTestCase
from django.utils import timezone
from redis import Redis
from redis.exceptions import RedisError

from authentication.api.rdp_login import digest
from authentication.services.rdp_login import (
    RDPLoginTicket, RDPLoginTicketCache, TicketCacheUnavailable,
)


class RDPLoginTicketCacheTests(SimpleTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        executable = shutil.which('redis-server')
        if not executable:
            raise SkipTest('redis-server is required for ticket cache integration tests')
        directory = tempfile.TemporaryDirectory(prefix='rdp-cache-', dir='/tmp')
        cls.addClassCleanup(directory.cleanup)
        socket = str(Path(directory.name) / 'redis.sock')
        process = subprocess.Popen(
            [executable, '--port', '0', '--unixsocket', socket,
             '--save', '', '--appendonly', 'no', '--dir', directory.name],
            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )

        def stop():
            process.terminate()
            process.wait(timeout=5)

        cls.addClassCleanup(stop)
        cls.redis = Redis(unix_socket_path=socket, socket_timeout=1)
        cls.addClassCleanup(cls.redis.close)
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            try:
                if cls.redis.ping():
                    break
            except RedisError:
                time.sleep(0.02)
        else:
            raise RuntimeError('isolated Redis did not start')

    def setUp(self):
        self.store = RDPLoginTicketCache()
        client = patch.object(RDPLoginTicketCache, 'client', return_value=self.redis)
        client.start()
        self.addCleanup(client.stop)
        username = 'jlt_' + uuid4().hex[:16]
        self.password = secrets.token_urlsafe(32)
        self.ticket = RDPLoginTicket(
            id=uuid4(), connection_id=uuid4(), connection_token_id=uuid4(),
            org_id=uuid4(), user_id=uuid4(), asset_id=uuid4(), host_id=uuid4(), app_id=uuid4(),
            app_name='weblite', username=username,
            password_hash=digest(username + '\0' + self.password),
            expires_at=timezone.now() + timedelta(minutes=5),
        )

    def test_shared_cache_preserves_binding_and_ttl_without_plaintext_secret(self):
        self.assertTrue(self.store.add(self.ticket))
        other_worker = RDPLoginTicketCache()
        ticket, encoded = other_worker.get(self.ticket.username)
        self.assertEqual(ticket, self.ticket)
        self.assertNotIn(self.password.encode(), encoded)
        self.assertIn(self.ticket.password_hash.encode(), encoded)
        self.assertGreater(self.redis.pttl(self.store.key(ticket.username)), 0)
        self.assertLessEqual(self.redis.pttl(self.store.key(ticket.username)), 300000)

    def test_collision_does_not_overwrite_an_existing_ticket(self):
        self.assertTrue(self.store.add(self.ticket))
        replacement = replace(self.ticket, connection_id=uuid4(), password_hash='another-hash')
        self.assertFalse(self.store.add(replacement))
        self.assertEqual(self.store.get(self.ticket.username)[0], self.ticket)

    def test_only_one_concurrent_worker_can_consume(self):
        self.assertTrue(self.store.add(self.ticket))
        _, encoded = self.store.get(self.ticket.username)

        def consume(_):
            return RDPLoginTicketCache().consume(self.ticket.username, encoded)

        with ThreadPoolExecutor(max_workers=16) as workers:
            results = list(workers.map(consume, range(32)))
        self.assertEqual(sum(results), 1)
        self.assertIsNone(self.store.get(self.ticket.username))

    def test_stale_reader_cannot_delete_a_different_ticket(self):
        self.assertTrue(self.store.add(self.ticket))
        _, old = self.store.get(self.ticket.username)
        self.assertTrue(self.store.consume(self.ticket.username, old))
        replacement = replace(self.ticket, connection_id=uuid4())
        self.assertTrue(self.store.add(replacement))
        self.assertFalse(self.store.consume(self.ticket.username, old))
        self.assertEqual(self.store.get(self.ticket.username)[0], replacement)

    def test_expired_ticket_disappears_and_cannot_be_consumed(self):
        self.assertFalse(self.store.add(replace(self.ticket, expires_at=timezone.now())))
        self.assertTrue(self.store.add(self.ticket))
        _, encoded = self.store.get(self.ticket.username)
        self.redis.pexpire(self.store.key(self.ticket.username), 1)
        deadline = time.monotonic() + 2
        while self.store.get(self.ticket.username) is not None and time.monotonic() < deadline:
            time.sleep(0.01)
        self.assertIsNone(self.store.get(self.ticket.username))
        self.assertFalse(self.store.consume(self.ticket.username, encoded))

    def test_corrupt_cache_and_redis_failure_do_not_authorize(self):
        key = self.store.key(self.ticket.username)
        for value in ['bad-json', '{}', '[]']:
            self.redis.set(key, value, ex=10)
            self.assertIsNone(self.store.get(self.ticket.username))
        with patch.object(RDPLoginTicketCache, 'client', side_effect=RedisError):
            for call in [lambda: self.store.add(self.ticket),
                         lambda: self.store.get(self.ticket.username),
                         lambda: self.store.consume(self.ticket.username, b'old')]:
                with self.assertRaises(TicketCacheUnavailable):
                    call()
