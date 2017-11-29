# ~*~ coding: utf-8 ~*~
import datetime

from django.utils import timezone

from .base import CommandBase


class CommandStore(CommandBase):

    def __init__(self):
        from applications.models import SessionCommand
        self.model = SessionCommand

    def save(self, command):
        """
        保存命令到数据库
        """

        self.model.objects.create(
            user=command["user"], asset=command["asset"],
            system_user=command["system_user"], input=command["input"],
            output=command["output"], session=command["session"],
            timestamp=command["timestamp"]
        )

    def bulk_save(self, commands):
        """
        批量保存命令到数据库, command的顺序和save中一致
        """
        _commands = []
        for c in commands:
            _commands.append(self.model(
                user=c["user"], asset=c["asset"], system_user=c["system_user"],
                input=c["input"], output=c["output"], session=c["session"],
                timestamp=c["timestamp"]
            ))
        return self.model.objects.bulk_create(_commands)

    def filter(self, date_from=None, date_to=None, user=None,
               asset=None, system_user=None, _input=None, session=None):
        filter_kwargs = {}

        if date_from:
            filter_kwargs['timestamp__gte'] = int(date_from.timestamp())
        else:
            week_ago = timezone.now() - datetime.timedelta(days=7)
            filter_kwargs['timestamp__gte'] = int(week_ago.timestamp())
        if date_to:
            filter_kwargs['timestamp__lte'] = int(date_to.timestamp())
        else:
            filter_kwargs['timestamp__lte'] = int(timezone.now().timestamp())
        if user:
            filter_kwargs['user'] = user
        if asset:
            filter_kwargs['asset'] = asset
        if system_user:
            filter_kwargs['system_user'] = system_user
        if _input:
            filter_kwargs['input__icontains'] = _input
        if session:
            filter_kwargs['session'] = session

        queryset = self.model.objects.filter(**filter_kwargs)
        return queryset

    def all(self):
        """返回所有数据"""
        return self.model.objects.iterator()

