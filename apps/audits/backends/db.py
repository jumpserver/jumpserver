# ~*~ coding: utf-8 ~*~
from django.utils.translation import gettext_lazy as _

from audits.models import OperateLog
from perms.const import ActionChoices


class OperateLogStore(object):
    # 用不可见字符分割前后数据，节省存储-> diff: {'key': 'before\0after'}
    SEP = '\0'

    def __init__(self, config):
        self.model = OperateLog
        self.max_length = 2048
        self.max_length_tip_msg = _(
            'The text content is too long. Use Elasticsearch to store operation logs'
        )

    @staticmethod
    def ping(timeout=None):
        return True

    @classmethod
    def convert_before_after_to_diff(cls, before, after):
        if not isinstance(before, dict):
            before = dict()
        if not isinstance(after, dict):
            after = dict()

        diff = dict()
        keys = set(before.keys()) | set(after.keys())
        for k in keys:
            before_value = before.get(k, '')
            after_value = after.get(k, '')
            diff[k] = '%s%s%s' % (before_value, cls.SEP, after_value)
        return diff

    @classmethod
    def convert_diff_to_before_after(cls, diff):
        before, after = dict(), dict()
        if not diff:
            return before, after

        for k, v in diff.items():
            before_value, after_value = v.split(cls.SEP, 1)
            before[k], after[k] = before_value, after_value
        return before, after

    @staticmethod
    def _get_special_handler(resource_type):
        # 根据资源类型，处理特殊字段
        resource_map = {
            'Asset permission': lambda k, v: ActionChoices.display(int(v)) if k == 'Actions' else v
        }
        return resource_map.get(resource_type, lambda k, v: v)

    @classmethod
    def convert_diff_friendly(cls, op_log):
        diff_list = list()
        handler = cls._get_special_handler(op_log.resource_type)
        for k, v in op_log.diff.items():
            before, after = v.split(cls.SEP, 1)
            diff_list.append({
                'field': _(k),
                'before': handler(k, before) if before else _('empty'),
                'after': handler(k, after) if after else _('empty'),
            })
        return diff_list

    def save(self, **kwargs):
        log_id = kwargs.get('id', None)
        before = kwargs.pop('before') or {}
        after = kwargs.pop('after') or {}

        op_log = self.model.objects.filter(pk=log_id).first()
        if op_log is not None:
            op_log_diff = op_log.diff or {}
            op_before, op_after = self.convert_diff_to_before_after(op_log_diff)
            before.update(op_before)
            after.update(op_after)
        else:
            # 限制长度 128 OperateLog.resource.field.max_length, 避免存储失败
            max_length = 128
            resource = kwargs.get('resource', '')
            if resource and isinstance(resource, str):
                kwargs['resource'] = resource[:max_length]
            op_log = self.model(**kwargs)

        diff = self.convert_before_after_to_diff(before, after)
        if len(str(diff)) > self.max_length:
            limit = {str(_('Tips')): self.max_length_tip_msg}
            diff = self.convert_before_after_to_diff(limit, limit)

        setattr(op_log, 'LOCKING_ORG', op_log.org_id)
        op_log.diff = diff
        op_log.save()
