"""Load a real source boundary without booting production apps or databases.

These checks isolate collaborators explicitly; they are not deployment tests.
Run with the repository Python dependencies and SECURITY_TEST_TMP set to a
disposable directory. The Redis fixture disables TCP, persistence and daemon mode.
"""
import ast
import hashlib
import os
from pathlib import Path
import subprocess
import time

from django.conf import settings

ROOT = Path(__file__).resolve().parents[2]
TEMP = Path(os.environ['SECURITY_TEST_TMP'])
TEMP.mkdir(parents=True, exist_ok=True)
# macOS Unix socket paths must be short. The link still stores the socket in
# the caller's disposable directory, never in a production Redis instance.
SHORT_TEMP = Path('/tmp') / ('osm-redis-' + hashlib.sha256(str(TEMP).encode()).hexdigest()[:12])
if not SHORT_TEMP.is_symlink():
    SHORT_TEMP.symlink_to(TEMP, target_is_directory=True)
SOCKET = SHORT_TEMP / 'redis.sock'
if not settings.configured:
    settings.configure(
        SECRET_KEY='disposable-security-regression-key', USE_I18N=False,
        SECURITY_LOGIN_LIMIT_COUNT=7, SECURITY_LOGIN_LIMIT_TIME=1,
        SECURITY_LOGIN_IP_LIMIT_COUNT=7, SECURITY_LOGIN_IP_LIMIT_TIME=1,
        SECURITY_LOGIN_IP_WHITE_LIST=[], SECURITY_LOGIN_IP_BLACK_LIST=[],
        CACHE_LOGIN_PASSWORD_ENABLED=True, CACHE_LOGIN_PASSWORD_TTL=60,
        SECURITY_ACCOUNT_SECRET_READ=True, SECURITY_VIEW_AUTH_NEED_MFA=True,
        SECURITY_MFA_VERIFY_TTL=60,
        CACHES={'default': {
            'BACKEND': 'redis_lock.django_cache.RedisCache',
            'LOCATION': 'unix://' + str(SOCKET) + '?db=0',
            'OPTIONS': {'CLIENT_CLASS': 'django_redis.client.DefaultClient'},
        }},
    )


def load(path, names, namespace, members=None):
    tree = ast.parse((ROOT / path).read_text())
    body = [node for node in tree.body if isinstance(node, (ast.ClassDef, ast.FunctionDef))
            and node.name in names]
    if members:
        for node in body:
            if isinstance(node, ast.ClassDef):
                node.body = [item for item in node.body if isinstance(item, ast.FunctionDef)
                             and item.name in members]
    exec(compile(ast.fix_missing_locations(ast.Module(body=body, type_ignores=[])),
                 str(ROOT / path), 'exec'), namespace)
    return namespace


class RedisFixture:
    @classmethod
    def setUpClass(cls):
        cls.redis = subprocess.Popen([
            '/opt/homebrew/bin/redis-server', '--port', '0', '--unixsocket', str(SOCKET),
            '--unixsocketperm', '700', '--save', '', '--appendonly', 'no',
            '--dir', str(TEMP),
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        from django.core.cache import cache
        for _ in range(100):
            try:
                cache.get('fixture-ready')
                return
            except Exception:
                time.sleep(0.02)
        cls.redis.terminate()
        raise RuntimeError('disposable Redis did not start')

    @classmethod
    def tearDownClass(cls):
        from django.core.cache import cache
        cache.close()
        cls.redis.terminate()
        cls.redis.wait(timeout=5)

    def setUp(self):
        from django.core.cache import cache
        cache.clear()  # This fixture only connects to its private Unix socket.
