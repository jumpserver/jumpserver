from django.core.cache import cache
from django.core.management.base import BaseCommand

from common.utils import signer
from common.utils.crypto import get_aes_crypto
from users.models import User


class Command(BaseCommand):
    help = 'Encrypt existing signed LDAP password cache entries without extending their TTL.'

    def handle(self, *args, **options):
        # Run after all Core workers have been upgraded so old workers cannot
        # write the signed format again. SCAN avoids blocking Redis with KEYS.
        prefix = User.sect_cache_tpl.split('{}')[0]
        cipher = get_aes_crypto(mode='GCM')
        migrated = discarded = 0
        for key in cache.iter_keys(prefix + '*'):
            user_id = key[len(prefix):]
            user = User(id=user_id)
            with cache.lock(f'login-password-{user_id}', expire=10, auto_renewal=True):
                before = cache.get(key)
                if not before or (isinstance(before, str) and before.startswith('aes-gcm:v1:')):
                    continue
                # Migrate even when password caching has since been disabled.
                user._get_cached_password(key, signer, cipher)
                after = cache.get(key)
                if isinstance(after, str) and after.startswith('aes-gcm:v1:'):
                    migrated += 1
                elif after is None:
                    discarded += 1
        self.stdout.write(f'Encrypted entries: {migrated}; invalid/expired entries removed: {discarded}')
