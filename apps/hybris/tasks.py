# ~*~ coding: utf-8 ~*~
from celery import shared_task
import json
from ops.tasks import run_AdHoc


@shared_task
def submit_template_task(assets):
    print(11)
