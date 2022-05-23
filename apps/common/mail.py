from functools import wraps

from django.utils.translation import ugettext_lazy as _
from django.core.mail import EmailMultiAlternatives as DJEmailMultiAlternatives
from django.core.mail import send_mail as dj_send_mail
from html2text import HTML2Text

from audits.models import TaskLog


def write_log(d_type='function'):
    def outer(func):
        @wraps(func)
        def inner(*args, **kwargs):
            if d_type == 'class':
                self = args[0]
                message = getattr(self, 'body', '')
                recipient = getattr(self, 'to', [])
            else:
                message = args[1]
                recipient = args[3]

            h = HTML2Text()
            message = h.handle(message)

            event = '%s: %s\r\n%s: %s' % (
                _("Recipient"), ','.join(recipient),
                _("Body"), message
            )
            t = TaskLog.objects.create(
                type=TaskLog.EMAIL,  event=event
            )
            try:
                ret = func(*args, **kwargs)
            except Exception as e:
                t.result = str(e)
                t.is_success = False
                ret = None
            else:
                t.result = _("Success")
                t.is_success = True
            t.save()
            return ret
        return inner
    return outer


class EmailMultiAlternatives(DJEmailMultiAlternatives):
    @write_log(d_type='class')
    def send(self, fail_silently=False):
        resp = super().send(fail_silently)
        return resp


@write_log()
def send_mail(*args, **kwargs):
    resp = dj_send_mail(*args, **kwargs)
    return resp
