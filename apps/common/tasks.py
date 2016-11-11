from __future__ import absolute_import

import os
from celery import shared_task
from celery.schedules import crontab
from django.core.mail import send_mail
# from django.conf import settings
# from common import celery_app


from celery import Celery

# set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'jumpserver.settings')

from django.conf import settings

app = Celery('jumpserver')

# Using a string here means the worker will not have to
# pickle the object when using Windows.
app.config_from_object('django.conf:settings')
app.autodiscover_tasks(lambda: [app_config.split('.')[0] for app_config in settings.INSTALLED_APPS])


@app.task
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
        args.insert(2, settings.EMAIL_HOST_USER)
        args = tuple(args)

    send_mail(*args, **kwargs)


# @celery_app.task
# def test(arg):
#     print(arg)


# celery_app.conf.beat_schedule = {
#     'add-every-30-seconds': {
#         'task': 'common.test',
#         'schedule': crontab(minute='*/1'),
#         'args': ('nihao',)
#     }
# }
