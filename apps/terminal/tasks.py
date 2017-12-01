# -*- coding: utf-8 -*-
#

from celery import shared_task


# Todo: 定期清理上报history
@shared_task
def clean_terminal_history():
    pass
