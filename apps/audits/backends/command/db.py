# ~*~ coding: utf-8 ~*~

from .base import CommandBase
from audits.models import CommandLog


class CommandStore(CommandBase):
    model = CommandLog
    queryset = []

    def save(self, proxy_log_id, user, asset, system_user,
             command_no, command, output, timestamp):
        self.model.objects.create(
            proxy_log_id=proxy_log_id, user=user, asset=asset,
            system_user=system_user, command_no=command_no,
            command=command, output=output, timestamp=timestamp
        )

    def filter(self, date_from_ts=None, date_to_ts=None, user='',
               asset='', system_user='', command='', proxy_log_id=0):
        filter_kwargs = {}

        if date_from_ts:
            filter_kwargs['timestamp__gte'] = date_from_ts
        if date_to_ts:
            filter_kwargs['timestamp__lte'] = date_to_ts
        if user:
            filter_kwargs['user'] = user
        if asset:
            filter_kwargs['asset'] = asset
        if system_user:
            filter_kwargs['system_user'] = system_user
        if command:
            filter_kwargs['command__icontains'] = command
        if proxy_log_id:
            filter_kwargs['proxy_log_id'] = proxy_log_id

        if filter_kwargs:
            self.queryset = self.model.objects.filter(**filter_kwargs)
        return self.queryset

    def all(self):
        """返回所有数据"""
        return self.model.objects.iterator()

