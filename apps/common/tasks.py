import os

from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail, EmailMultiAlternatives
from django.utils.translation import gettext_lazy as _

from .utils import get_logger

logger = get_logger(__file__)


def task_activity_callback(self, subject, message, recipient_list, *args, **kwargs):
    from users.models import User
    email_list = recipient_list
    resource_ids = list(User.objects.filter(email__in=email_list).values_list('id', flat=True))
    return resource_ids,


@shared_task(verbose_name=_("Send email"), activity_callback=task_activity_callback)
def send_mail_async(*args, **kwargs):
    """ Using celery to send email async

    You can use it as django send_mail function

    Example:
    send_mail_sync.delay(subject, message, from_mail, recipient_list, fail_silently=False, html_message=None)

    Also, you can ignore the from_mail, unlike django send_mail, from_email is not a required args:

    Example:
    send_mail_sync.delay(subject, message, recipient_list, fail_silently=False, html_message=None)
    """
    if len(args) == 3:
        args = list(args)
        args[0] = (settings.EMAIL_SUBJECT_PREFIX or '') + args[0]
        from_email = settings.EMAIL_FROM or settings.EMAIL_HOST_USER
        args.insert(2, from_email)

    args[3] = [mail for mail in args[3] if mail != 'admin@mycomany.com']
    args = tuple(args)

    try:
        return send_mail(*args, **kwargs)
    except Exception as e:
        logger.error("Sending mail error: {}".format(e))


@shared_task(verbose_name=_("Send email attachment"), activity_callback=task_activity_callback)
def send_mail_attachment_async(subject, message, recipient_list, attachment_list=None):
    if attachment_list is None:
        attachment_list = []
    from_email = settings.EMAIL_FROM or settings.EMAIL_HOST_USER
    subject = (settings.EMAIL_SUBJECT_PREFIX or '') + subject
    recipient_list = [mail for mail in recipient_list if mail != 'admin@mycomany.com']
    email = EmailMultiAlternatives(
        subject=subject,
        body=message,
        from_email=from_email,
        to=recipient_list
    )
    for attachment in attachment_list:
        email.attach_file(attachment)
        os.remove(attachment)
    try:
        return email.send()
    except Exception as e:
        logger.error("Sending mail attachment error: {}".format(e))
