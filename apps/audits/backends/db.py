# ~*~ coding: utf-8 ~*~
from django.utils.translation import ugettext_lazy as _

from audits.models import OperateLog


class OperateLogStore(object):
    def __init__(self, config):
        self.model = OperateLog
        self.max_length = 1024
        self.max_length_tip_msg = _(
            'The text content is too long. Use Elasticsearch to store operation logs'
        )

    @staticmethod
    def ping(timeout=None):
        return True

    def save(self, **kwargs):
        log_id = kwargs.get('id', '')
        before = kwargs.get('before') or {}
        after = kwargs.get('after') or {}
        if len(str(before)) > self.max_length:
            before = {_('Tips'): self.max_length_tip_msg}
        if len(str(after)) > self.max_length:
            after = {_('Tips'): self.max_length_tip_msg}

        op_log = self.model.objects.filter(pk=log_id).first()
        if op_log is not None:
            raw_after = op_log.after or {}
            raw_before = op_log.before or {}
            raw_before.update(before)
            raw_after.update(after)
            op_log.before = raw_before
            op_log.after = raw_after
            op_log.save()
        else:
            self.model.objects.create(**kwargs)
