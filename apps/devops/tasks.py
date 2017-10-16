# ~*~ coding: utf-8 ~*~
from celery import shared_task
import json
from ops.tasks import run_AdHoc


@shared_task
def ansible_install_role(role_name):
    print(112)
