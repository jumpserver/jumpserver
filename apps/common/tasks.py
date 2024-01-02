import os

from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail, EmailMultiAlternatives, get_connection
from django.utils.translation import gettext_lazy as _
import jms_storage

from .utils import get_logger

logger = get_logger(__file__)


def get_email_connection(**kwargs):
    email_backend_map = {
        'smtp': 'django.core.mail.backends.smtp.EmailBackend',
        'exchange': 'jumpserver.rewriting.exchange.EmailBackend'
    }
    return get_connection(
        backend=email_backend_map.get(settings.EMAIL_PROTOCOL), **kwargs
    )


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

    args = tuple(args)
    try:
        return send_mail(connection=get_email_connection(), *args, **kwargs)
    except Exception as e:
        logger.error("Sending mail error: {}".format(e))


@shared_task(verbose_name=_("Send email attachment"), activity_callback=task_activity_callback)
def send_mail_attachment_async(subject, message, recipient_list, attachment_list=None):
    if attachment_list is None:
        attachment_list = []
    from_email = settings.EMAIL_FROM or settings.EMAIL_HOST_USER
    subject = (settings.EMAIL_SUBJECT_PREFIX or '') + subject
    email = EmailMultiAlternatives(
        subject=subject,
        body=message,
        from_email=from_email,
        to=recipient_list,
        connection=get_email_connection(),
    )
    for attachment in attachment_list:
        email.attach_file(attachment)
        os.remove(attachment)
    try:
        return email.send()
    except Exception as e:
        logger.error("Sending mail attachment error: {}".format(e))


@shared_task(verbose_name=_('Upload session replay to external storage'))
def upload_backup_to_obj_storage(recipient, upload_file):
    logger.info(f'Start upload file : {upload_file}')
    remote_path = os.path.join('account_backup', os.path.basename(upload_file))
    storage = jms_storage.get_object_storage(recipient.config)
    ok, err = storage.upload(src=upload_file, target=remote_path)
    if not ok:
        logger.error(f'upload {upload_file} failed, error: {err}')
        return
    try:
        os.remove(upload_file)
    except Exception as e:
        print(f'remove upload file : {upload_file} error: {e}')
