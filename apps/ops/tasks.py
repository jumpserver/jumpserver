# coding: utf-8
from celery import shared_task

from .utils import run_adhoc


def rerun_task():
    pass


@shared_task
def run_add_hoc_and_record_async(adhoc, **options):
    return run_adhoc(adhoc, **options)
