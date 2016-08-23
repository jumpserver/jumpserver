from celery import Celery
from django.conf import settings
from time import sleep

app = Celery('ops', broker=settings.BROKER_URL)


@app.task()
def UploadTask(message):

    # Update the state. The meta data is available in task.info dicttionary
    # The meta data is useful to store relevant information to the task
    # Here we are storing the upload progress in the meta.

    UploadTask.update_state(state='PROGRESS', meta={'progress': 0})
    sleep(30)
    UploadTask.update_state(state='PROGRESS', meta={'progress': 30})
    sleep(30)
    return message


def get_task_status(task_id):

    # If you have a task_id, this is how you query that task
    task = UploadTask.AsyncResult(task_id)

    status = task.status
    progress = 0

    if status == u'SUCCESS':
        progress = 100
    elif status == u'FAILURE':
        progress = 0
    elif status == 'PROGRESS':
        progress = task.info['progress']

    return {'status': status, 'progress': progress}