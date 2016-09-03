from __future__ import absolute_import
import time

from celery import shared_task
from common import celery_app


@shared_task
def longtime_add(x, y):
    print 'long time task begins'
    # sleep 5 seconds
    time.sleep(5)
    print 'long time task finished'
    return x + y


@celery_app.task(name='hello-world')
def hello():
    print('hello world!')
