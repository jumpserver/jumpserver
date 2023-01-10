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
        before_limit, after_limit = None, None
        log_id = kwargs.get('id', '')
        before = kwargs.get('before') or {}
        after = kwargs.get('after') or {}
        if len(str(before)) > self.max_length:
            before_limit = {str(_('Tips')): self.max_length_tip_msg}
        if len(str(after)) > self.max_length:
            after_limit = {str(_('Tips')): self.max_length_tip_msg}

        op_log = self.model.objects.filter(pk=log_id).first()
        if op_log is not None:
            op_log_before = op_log.before or {}
            op_log_after = op_log.after or {}
            if not before_limit:
                before.update(op_log_before)
            if not after_limit:
                after.update(op_log_after)
        else:
            op_log = self.model(**kwargs)

        op_log.before = before_limit if before_limit else before
        op_log.after = after_limit if after_limit else after
        op_log.save()
