import concurrent.futures
import unittest
from unittest.mock import patch
from types import SimpleNamespace

from django.core.cache import cache
from source_boundary import RedisFixture, load, settings

ns = load('apps/users/utils.py',
          ['incr_failed_count_atomic', 'BlockUtilBase', 'BlockGlobalIpUtilBase',
           'LoginBlockUtil', 'MFABlockUtils', 'LoginIpBlockUtil'],
          {'cache': cache, 'settings': settings, 'ip': SimpleNamespace(contains_ip=lambda *args: False)})


class Counters(RedisFixture, unittest.TestCase):
    def test_concurrent_account_and_mfa_failures(self):
        for name in ['LoginBlockUtil', 'MFABlockUtils']:
            util = ns[name]('CaseUser', '127.0.0.1')
            with concurrent.futures.ThreadPoolExecutor(max_workers=32) as pool:
                list(pool.map(lambda _: util.incr_failed_count(), range(256)))
            self.assertEqual(util.get_failed_count(), 256)
            self.assertTrue(util.is_block())
            self.assertGreater(cache.ttl(util.limit_key), 0)
            self.assertLessEqual(cache.ttl(util.limit_key), util.key_ttl)
            util.clean_failed_count()
            self.assertEqual(util.get_failed_count(), 0)
            self.assertFalse(util.is_block())

    def test_concurrent_ip_failures(self):
        util = ns['LoginIpBlockUtil']('127.0.0.2')
        with concurrent.futures.ThreadPoolExecutor(max_workers=32) as pool:
            list(pool.map(lambda _: util.set_block_if_need(), range(128)))
        self.assertEqual(cache.get(util.limit_key), 128)
        self.assertTrue(util.is_block())

    def test_expiry_between_initialization_and_increment(self):
        original = cache.incr
        calls = []
        def expire_once(key):
            if not calls:
                calls.append(key)
                cache.delete(key)
            return original(key)
        with patch.object(cache, 'incr', side_effect=expire_once):
            self.assertEqual(ns['incr_failed_count_atomic']('expiry', 60), 1)
        with patch.object(cache, 'incr', side_effect=ValueError('missing')):
            with self.assertRaises(ValueError):
                ns['incr_failed_count_atomic']('failure', 60)

    def test_sliding_expiry_and_threshold(self):
        util = ns['LoginBlockUtil']('normal', '127.0.0.1')
        self.assertEqual(util.incr_failed_count(), 6)
        cache.touch(util.limit_key, 2)
        self.assertEqual(util.incr_failed_count(), 5)
        self.assertGreater(cache.ttl(util.limit_key), 2)
        for _ in range(5):
            util.incr_failed_count()
        self.assertTrue(util.is_block())


if __name__ == '__main__':
    unittest.main()
