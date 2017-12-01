# ~*~ coding: utf-8 ~*~

from .base import RecordBase
from audits.models import RecordLog


class RecordStore(RecordBase):
    model = RecordLog
    queryset = []

    def save(self, proxy_log_id, output, timestamp):
        return self.model.objects.create(
            proxy_log_id=proxy_log_id, output=output, timestamp=timestamp
        )

    def filter(self, date_from_ts=None, proxy_log_id=''):
        filter_kwargs = {}

        if date_from_ts:
            filter_kwargs['timestamp__gte'] = date_from_ts
        if proxy_log_id:
            filter_kwargs['proxy_log_id'] = proxy_log_id

        if filter_kwargs:
            self.queryset = self.model.objects.filter(**filter_kwargs)
        return self.queryset

    def all(self):
        """返回所有数据"""
        return self.model.objects.all()

