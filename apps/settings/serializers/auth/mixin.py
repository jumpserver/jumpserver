from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from ops.mixin import PeriodTaskSerializerMixin
from settings.ldap_tls import LDAPTLSUtil


class LDAPSerializerMixin:
    cert_content_suffixes = ('_CACERT_CONTENT', '_CERT_CONTENT', '_KEY_CONTENT')

    def validate(self, attrs):
        is_periodic = attrs.get(self.periodic_key)
        crontab = attrs.get(self.crontab_key)
        interval = attrs.get(self.interval_key)
        if is_periodic and not any([crontab, interval]):
            msg = _("Require interval or crontab setting")
            raise serializers.ValidationError(msg)
        return super().validate(attrs)

    def _sync_tls_certs_if_needed(self):
        category = getattr(self, 'category', None)
        if not category:
            return
        prefix = f'AUTH_{category.upper()}'
        cert_attrs = [f'{prefix}{suffix}' for suffix in self.cert_content_suffixes]
        if not any(k in self.validated_data for k in cert_attrs):
            return
        tls_util = LDAPTLSUtil(category)
        tls_util.sync_files()
        tls_util.refresh_global_options()

    def post_save(self):
        self._sync_tls_certs_if_needed()
        keys = [self.periodic_key, self.interval_key, self.crontab_key]
        kwargs = {k: self.validated_data[k] for k in keys if k in self.validated_data}
        if not kwargs:
            return
        self.import_task_function(**kwargs)
