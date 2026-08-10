import ssl

from django.conf import settings
from django.core.mail.backends.smtp import EmailBackend as BaseEmailBackend
from django.utils.functional import cached_property


class EmailBackend(BaseEmailBackend):
    @cached_property
    def ssl_context(self):
        context = super().ssl_context
        verify_mode = settings.EMAIL_CERT_VERIFY_MODE

        if verify_mode == 'custom_ca':
            context.load_verify_locations(cadata=settings.EMAIL_CACERT_CONTENT)
        elif verify_mode == 'none':
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE

        return context
