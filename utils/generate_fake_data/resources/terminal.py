from .base import FakeDataGenerator
from users.models import *
from assets.models import *
from terminal.models import *
import forgery_py
import random


class CommandGenerator(FakeDataGenerator):
    resource = 'command'

    def do_generate(self, batch, batch_size):
        Command.generate_fake(len(batch), self.org)


class SessionGenerator(FakeDataGenerator):
    resource = 'session'
    users: list
    assets: list
    system_users: list

    def pre_generate(self):
        self.users = list(User.objects.all())
        self.assets = list(Asset.objects.all())
        self.system_users = list(SystemUser.objects.all())

    def do_generate(self, batch, batch_size):
        user = random.choice(self.users)
        asset = random.choice(self.assets)
        system_user = random.choice(self.system_users)

        objects = []

        now = timezone.now()
        timedelta = list(range(30))
        for i in batch:
            delta = random.choice(timedelta)
            date_start = now - timezone.timedelta(days=delta, seconds=delta * 60)
            date_end = date_start + timezone.timedelta(seconds=delta * 60)
            data = dict(
                user=user.name,
                user_id=user.id,
                asset=asset.hostname,
                asset_id=asset.id,
                system_user=system_user.name,
                system_user_id=system_user.id,
                org_id=self.org.id,
                date_start=date_start,
                date_end=date_end,
                is_finished=True
            )
            objects.append(Session(**data))
        creates = Session.objects.bulk_create(objects, ignore_conflicts=True)

