from django.core.mail import send_mail
from django.conf import settings
from celery import shared_task
from .utils import get_logger


logger = get_logger(__file__)


@shared_task
def send_mail_async(*args, **kwargs):
    """ Using celery to send email async

    You can use it as django send_mail function

    Example:
    send_mail_sync.delay(subject, message, from_mail, recipient_list, fail_silently=False, html_message=None)

    Also you can ignore the from_mail, unlike django send_mail, from_email is not a require args:

    Example:
    send_mail_sync.delay(subject, message, recipient_list, fail_silently=False, html_message=None)
    """
    if len(args) == 3:
        args = list(args)
        args[0] = settings.EMAIL_SUBJECT_PREFIX + args[0]
        email_from = settings.EMAIL_FROM or settings.EMAIL_HOST_USER
        args.insert(2, email_from)
        args = tuple(args)

    try:
        send_mail(*args, **kwargs)
    except Exception as e:
        logger.error("Sending mail error: {}".format(e))
