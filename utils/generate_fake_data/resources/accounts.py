import random

import forgery_py

from accounts.models import Account
from assets.models import Asset
from .base import FakeDataGenerator


class AccountGenerator(FakeDataGenerator):
    resource = 'account'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.assets = list(list(Asset.objects.all()[:5000]))

    def do_generate(self, batch, batch_size):
        accounts = []
        for i in batch:
            asset = random.choice(self.assets)
            name = forgery_py.internet.user_name(True) + '-' + str(i)
            d = {
                'username': name,
                'name': name,
                'asset': asset,
                'secret': name,
                'secret_type': 'password',
                'is_active': True,
                'privileged': False,
            }
            accounts.append(Account(**d))
        Account.objects.bulk_create(accounts, ignore_conflicts=True)
