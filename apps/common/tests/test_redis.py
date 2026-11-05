import shutil
import socket
import socketserver
import subprocess
import tempfile
import threading
import time
import unittest
from contextlib import nullcontext
from copy import deepcopy
from queue import Queue
from unittest.mock import patch
from uuid import uuid4

from django.conf import settings
from django.test import override_settings
from django_redis.pool import ConnectionFactory
from redis.exceptions import ConnectionError, TimeoutError

from common.utils.connection import RedisPubSub, get_redis_client
from common.utils.lock import DistributedLock


class BlackholeHandler(socketserver.StreamRequestHandler):
    def handle(self):
        while line := self.rfile.readline():
            args = []
            for _ in range(int(line[1:])):
                size = int(self.rfile.readline()[1:])
                args.append(self.rfile.read(size))
                self.rfile.read(2)
            command = args[0].upper()
            if command in (b'GET', b'INCR'):
                self.server.commands.append(command)
                if len(self.server.commands) == 1:
                    self.server.release.wait(2)
                    return
                self.wfile.write(b':2\r\n')
            elif command == b'PING':
                self.wfile.write(b'+PONG\r\n')
            else:
                self.wfile.write(b'+OK\r\n')


class RedisTimeoutTests(unittest.TestCase):
    def test_timeout_does_not_replay_commands_and_next_call_reconnects(self):
        for command in ('GET', 'INCR'):
            with self.subTest(command=command):
                server = socketserver.ThreadingTCPServer(('127.0.0.1', 0), BlackholeHandler)
                server.commands = []
                server.release = threading.Event()
                thread = threading.Thread(target=server.serve_forever, daemon=True)
                thread.start()
                options = dict(settings.CACHES['default']['OPTIONS'])
                options.update(SOCKET_TIMEOUT=0.1, SOCKET_CONNECT_TIMEOUT=0.1)
                client = ConnectionFactory(options).connect(
                    f'redis://127.0.0.1:{server.server_address[1]}/0'
                )
                try:
                    started = time.monotonic()
                    with self.assertRaises(TimeoutError):
                        client.execute_command(command, 'blackhole-test')
                    self.assertLess(time.monotonic() - started, 1)
                    self.assertEqual(server.commands, [command.encode()])
                    self.assertEqual(client.execute_command(command, 'blackhole-test'), 2)
                    self.assertEqual(len(server.commands), 2)
                finally:
                    client.close()
                    client.connection_pool.disconnect()
                    server.release.set()
                    server.shutdown()
                    server.server_close()
                    thread.join(2)


@unittest.skipUnless(shutil.which('redis-server'), 'redis-server is required')
class RedisBlockingIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tempdir = tempfile.TemporaryDirectory(prefix='jms-redis-')
        cls.addClassCleanup(cls.tempdir.cleanup)
        with socket.socket() as listener:
            listener.bind(('127.0.0.1', 0))
            port = listener.getsockname()[1]
        cls.url = f'redis://127.0.0.1:{port}/0'
        cls.process = subprocess.Popen([
            shutil.which('redis-server'), '--bind', '127.0.0.1', '--port', str(port),
            '--save', '', '--appendonly', 'no', '--dir', cls.tempdir.name,
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        cls.addClassCleanup(cls.stop_server)
        cache_settings = deepcopy(settings.CACHES)
        for alias in ('default', 'blocking'):
            cache_settings[alias]['LOCATION'] = cls.url
            cache_settings[alias]['OPTIONS']['SOCKET_CONNECT_TIMEOUT'] = 0.3
        cache_settings['default']['OPTIONS']['SOCKET_TIMEOUT'] = 0.3
        cls.cache_override = override_settings(CACHES=cache_settings)
        cls.cache_override.enable()
        cls.addClassCleanup(cls.cache_override.disable)
        cls.client = get_redis_client()
        cls.blocking_client = get_redis_client(cache_alias='blocking')
        cls.addClassCleanup(cls.client.connection_pool.disconnect)
        cls.addClassCleanup(cls.blocking_client.connection_pool.disconnect)
        for _ in range(100):
            try:
                cls.client.ping()
                break
            except ConnectionError:
                if cls.process.poll() is not None:
                    raise RuntimeError('Test Redis exited during startup')
                time.sleep(0.02)
        else:
            raise RuntimeError('Test Redis did not start')

    @classmethod
    def stop_server(cls):
        cls.process.terminate()
        cls.process.wait(timeout=5)

    def test_cache_and_blocking_connections_are_isolated(self):
        regular = self.client.connection_pool
        blocking = self.blocking_client.connection_pool
        self.assertIsNot(regular, blocking)
        self.assertEqual(regular.make_connection().socket_timeout, 0.3)
        self.assertIsNone(blocking.make_connection().socket_timeout)
        key = f'test:{uuid4()}'
        self.client.set(key, 'shared-database')
        try:
            self.assertEqual(self.blocking_client.get(key), b'shared-database')
        finally:
            self.client.delete(key)

    def test_lock_waits_past_cache_socket_timeout_for_release(self):
        name = f'test:{uuid4()}'
        owner = DistributedLock(name, expire=10)
        waiter = DistributedLock(name, expire=10)
        self.assertIs(owner._client.connection_pool, self.blocking_client.connection_pool)
        self.assertTrue(owner.acquire(blocking=False))
        timer = threading.Timer(0.7, owner.release)
        timer.start()
        started = time.monotonic()
        acquired = False
        try:
            acquired = waiter.acquire(timeout=2)
            self.assertTrue(acquired)
            self.assertGreaterEqual(time.monotonic() - started, 0.65)
        finally:
            timer.join(2)
            if acquired:
                waiter.release()
            if owner.get_owner_id() == owner.id:
                owner.release()

    def test_lock_acquire_still_honors_its_timeout(self):
        name = f'test:{uuid4()}'
        owner = DistributedLock(name, expire=10)
        waiter = DistributedLock(name, expire=10)
        self.assertTrue(owner.acquire(blocking=False))
        started = time.monotonic()
        try:
            self.assertFalse(waiter.acquire(timeout=1))
            self.assertGreaterEqual(time.monotonic() - started, 0.9)
        finally:
            owner.release()

    def test_idle_subscription_does_not_reconnect_and_receives_message(self):
        messages = Queue()
        completed = threading.Event()
        publisher = RedisPubSub(f'test:{uuid4()}')
        self.assertIs(publisher.redis.connection_pool, self.client.connection_pool)
        with patch.object(publisher, 'resubscribe') as resubscribe:
            with patch('common.utils.connection.safe_db_connection', return_value=nullcontext()):
                subscription = publisher.subscribe(messages.put, complete=completed.set)
                try:
                    time.sleep(1.5)
                    publisher.publish({'test': 'idle'})
                    self.assertEqual(messages.get(timeout=2), {'test': 'idle'})
                    resubscribe.assert_not_called()
                finally:
                    subscription.sub.unsubscribe()
                    self.assertTrue(completed.wait(2))
