from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

__all__ = ['HmacVerifySerializerMixin']


class HmacVerifySerializerMixin(serializers.Serializer):
    hmac_model_class = None
    encrypt_value = serializers.SerializerMethodField(read_only=True, label=_('Encrypt value'))
    hmac_verify = serializers.SerializerMethodField(read_only=True, label=_('HMAC verify'))

    def _get_hmac_context(self, obj):
        from common.utils.verify_hmac import hmac_handler
        return hmac_handler.get_hmac_context(self.hmac_model_class, obj)

    def get_encrypt_value(self, obj):
        ctx = self._get_hmac_context(obj)
        return ctx.get('encrypt_value', '')

    def get_hmac_verify(self, obj):
        ctx = self._get_hmac_context(obj)
        return ctx.get('hmac_verify')
