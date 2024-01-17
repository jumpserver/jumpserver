import urllib3

from urllib3.exceptions import InsecureRequestWarning

from django.core.mail.backends.base import BaseEmailBackend
from django.core.mail.message import sanitize_address
from django.conf import settings
from exchangelib import Account, Credentials, Configuration, DELEGATE
from exchangelib import Mailbox, Message, HTMLBody, FileAttachment
from exchangelib import BaseProtocol, NoVerifyHTTPAdapter
from exchangelib.errors import TransportError


urllib3.disable_warnings(InsecureRequestWarning)
BaseProtocol.HTTP_ADAPTER_CLS = NoVerifyHTTPAdapter


class EmailBackend(BaseEmailBackend):
    def __init__(
        self,
        service_endpoint=None,
        username=None,
        password=None,
        fail_silently=False,
        **kwargs,
    ):
        super().__init__(fail_silently=fail_silently)
        self.service_endpoint = service_endpoint or settings.EMAIL_HOST
        self.username = settings.EMAIL_HOST_USER if username is None else username
        self.password = settings.EMAIL_HOST_PASSWORD if password is None else password
        self._connection = None

    def open(self):
        if self._connection:
            return False

        try:
            config = Configuration(
                service_endpoint=self.service_endpoint, credentials=Credentials(
                    username=self.username, password=self.password
                )
            )
            self._connection = Account(self.username, config=config, access_type=DELEGATE)
            return True
        except TransportError:
            if not self.fail_silently:
                raise

    def close(self):
        self._connection = None

    def send_messages(self, email_messages):
        if not email_messages:
            return 0

        new_conn_created = self.open()
        if not self._connection or new_conn_created is None:
            return 0
        num_sent = 0
        for message in email_messages:
            sent = self._send(message)
            if sent:
                num_sent += 1
        if new_conn_created:
            self.close()
        return num_sent

    def _send(self, email_message):
        if not email_message.recipients():
            return False

        encoding = settings.DEFAULT_CHARSET
        from_email = sanitize_address(email_message.from_email, encoding)
        recipients = [
            Mailbox(email_address=sanitize_address(addr, encoding)) for addr in email_message.recipients()
        ]
        try:
            message_body = email_message.body
            alternatives = email_message.alternatives or []
            attachments = []
            for attachment in email_message.attachments or []:
                name, content, mimetype = attachment
                if isinstance(content, str):
                    content = content.encode(encoding)
                attachments.append(
                    FileAttachment(name=name, content=content, content_type=mimetype)
                )
            for alternative in alternatives:
                if alternative[1] == 'text/html':
                    message_body = HTMLBody(alternative[0])
                    break

            email_message = Message(
                account=self._connection, subject=email_message.subject,
                body=message_body, to_recipients=recipients, sender=from_email,
                attachments=[]
            )
            email_message.attach(attachments)
            email_message.send_and_save()
        except Exception as error:
            if not self.fail_silently:
                raise error
            return False
        return True
