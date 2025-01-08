from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from ops.mixin import PeriodTaskSerializerMixin


class LDAPSerializerMixin:
    def validate(self, attrs):
        is_periodic = attrs.get(self.periodic_key)
        crontab = attrs.get(self.crontab_key)
        interval = attrs.get(self.interval_key)
        if is_periodic and not any([crontab, interval]):
            msg = _("Require interval or crontab setting")
            raise serializers.ValidationError(msg)
        return super().validate(attrs)

    def post_save(self):
        keys = [self.periodic_key, self.interval_key, self.crontab_key]
        kwargs = {k: self.validated_data[k] for k in keys if k in self.validated_data}
        if not kwargs:
            return
        self.import_task_function(**kwargs)
