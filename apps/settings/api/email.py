# -*- coding: utf-8 -*-
#

from smtplib import SMTPSenderRefused

from django.conf import settings
from django.core.mail import send_mail
from django.utils.translation import gettext_lazy as _
from rest_framework.views import Response, APIView

from common.tasks import get_email_connection as get_connection
from common.utils import get_logger
from .. import serializers
from ..connection_testing import get_test_config

logger = get_logger(__file__)

__all__ = ['MailTestingAPI']


class MailTestingAPI(APIView):
    serializer_class = serializers.MailTestSerializer
    success_message = _("Test mail sent to {}, please check")
    rbac_perms = {
        'POST': 'settings.change_email'
    }

    def post(self, request):
        config = get_test_config(self.serializer_class, request.data)
        email_host_user = config.get('EMAIL_HOST_USER', '')
        email_from = config.get('EMAIL_FROM')
        email_recipient = config.get('EMAIL_RECIPIENT')
        connection = None
        try:
            subject = settings.EMAIL_SUBJECT_PREFIX or '' + "Test"
            message = _("Test smtp setting")
            email_from = email_from or email_host_user
            email_recipient = email_recipient or email_from
            connection = get_connection(
                protocol=config['EMAIL_PROTOCOL'],
                host=config['EMAIL_HOST'], port=config.get('EMAIL_PORT', 25),
                username=email_host_user, password=config['EMAIL_HOST_PASSWORD'],
                use_tls=config.get('EMAIL_USE_TLS', False),
                use_ssl=config.get('EMAIL_USE_SSL', False),
                timeout=30,
            )
            send_mail(
                subject, message, email_from, [email_recipient],
                connection=connection
            )
        except SMTPSenderRefused as e:
            error = e.smtp_error
            if isinstance(error, bytes):
                for coding in ('gbk', 'utf8'):
                    try:
                        error = error.decode(coding)
                    except UnicodeDecodeError:
                        continue
                    else:
                        break
            logger.error(error)
            hint = _("Sender address refused by the server, "
                     "please check that EMAIL_FROM (sender) matches the SMTP account")
            return Response({"error": hint}, status=400)
        except Exception as e:
            logger.error(e)
            hint = _("Failed to send test mail, please check the mail server configuration")
            return Response({"error": hint}, status=400)
        finally:
            if connection is not None:
                connection.close()
        return Response({"msg": self.success_message.format(email_recipient)})
