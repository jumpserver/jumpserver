# ~*~ coding: utf-8 ~*~
import datetime

from django.db import transaction
from django.db.utils import OperationalError
from django.utils import timezone

from common.utils.common import pretty_string
from common.utils import get_logger
from .base import CommandBase

logger = get_logger(__name__)


class CommandStore(CommandBase):
    supports_idempotent_receipts = True

    def __init__(self, params):
        from terminal.models import Command
        self.model = Command

    def save(self, command):
        """
        保存命令到数据库
        """
        cmd_input = pretty_string(command['input'])
        self.model.objects.create(
            user=command["user"], asset=command["asset"],
            account=command["account"], input=cmd_input,
            output=command["output"], session=command["session"],
            risk_level=command.get("risk_level", 0), org_id=command["org_id"],
            timestamp=command["timestamp"]
        )

    def bulk_save(self, commands):
        """
        批量保存命令到数据库, command的顺序和save中一致
        """
        if commands and all(c.get('id') for c in commands):
            return self._save_receipts(commands)
        _commands = []
        for c in commands:
            cmd_input = pretty_string(c['input'])
            cmd_output = pretty_string(c['output'], max_length=1024)
            _commands.append(self.model(
                user=c["user"], asset=c["asset"], account=c["account"],
                input=cmd_input, output=cmd_output, session=c["session"],
                risk_level=c.get("risk_level", 0), org_id=c["org_id"],
                timestamp=c["timestamp"]
            ))
        error = False
        try:
            with transaction.atomic():
                self.model.objects.bulk_create(_commands)
        except OperationalError:
            error = True
        except:
            return False

        if not error:
            return True
        for command in _commands:
            try:
                with transaction.atomic():
                    command.save()
            except OperationalError:
                command.output = str(command.output.encode())
                command.save()
        return True

    def _save_receipts(self, commands):
        # get_or_create resolves concurrent retries against the existing UUID
        # primary key. Do not ignore arbitrary integrity errors or overwrite a
        # different event which happens to supply the same id.
        try:
            with transaction.atomic():
                for command in commands:
                    values = {key: command[key] for key in (
                        'user', 'asset', 'account', 'session', 'org_id', 'timestamp'
                    )}
                    values.update(
                        input=pretty_string(command['input']),
                        output=pretty_string(command['output'], max_length=1024),
                        risk_level=command.get('risk_level', 0),
                    )
                    obj, created = self.model.objects.get_or_create(id=command['id'], defaults=values)
                    if not created and any(getattr(obj, key) != value for key, value in values.items()):
                        raise ValueError('Audit event id reused with different content')
            return True
        except Exception as exc:
            logger.error('Durable audit receipt save failed (%s)', type(exc).__name__)
            return False

    @staticmethod
    def make_filter_kwargs(
            date_from=None, date_to=None,
            user=None, asset=None, account=None,
            input=None, session=None, risk_level=None, org_id=None):
        filter_kwargs = {}
        date_from_default = timezone.now() - datetime.timedelta(days=7)
        date_to_default = timezone.now()

        if not date_from and not session:
            date_from = date_from_default
        if not date_to and not session:
            date_to = date_to_default
        if date_from is not None:
            if isinstance(date_from, datetime.datetime):
                date_from = date_from.timestamp()
            filter_kwargs['timestamp__gte'] = int(date_from)
        if date_to is not None:
            if isinstance(date_to, datetime.datetime):
                date_to = date_to.timestamp()
            filter_kwargs['timestamp__lte'] = int(date_to)

        if user:
            filter_kwargs["user__startswith"] = user
        if asset:
            filter_kwargs['asset'] = asset
        if account:
            filter_kwargs['account'] = account
        if input:
            filter_kwargs['input__icontains'] = input
        if session:
            filter_kwargs['session'] = session
        if org_id is not None:
            filter_kwargs['org_id'] = org_id
        if risk_level is not None:
            filter_kwargs['risk_level'] = risk_level
        return filter_kwargs

    def filter(self, date_from=None, date_to=None,
               user=None, asset=None, account=None,
               input=None, session=None, risk_level=None, org_id=None):
        filter_kwargs = self.make_filter_kwargs(
            date_from=date_from, date_to=date_to, user=user,
            asset=asset, account=account, input=input,
            session=session, risk_level=risk_level, org_id=org_id,
        )
        queryset = self.model.objects.filter(**filter_kwargs)
        return queryset

    def count(self, date_from=None, date_to=None,
              user=None, asset=None, account=None,
              input=None, session=None):
        filter_kwargs = self.make_filter_kwargs(
            date_from=date_from, date_to=date_to, user=user,
            asset=asset, account=account, input=input,
            session=session,
        )
        count = self.model.objects.filter(**filter_kwargs).count()
        return count


