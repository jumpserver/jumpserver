# coding: utf-8
from celery import shared_task
from django.core import serializers


def rerun_task():
    pass


@shared_task
def run_task(tasks_json):
    for task in serializers.deserialize('json', tasks_json):
        task.object.run()
