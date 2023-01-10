from logging import StreamHandler
from threading import get_ident

from celery import current_task
from celery.signals import task_prerun, task_postrun
from django.conf import settings
from kombu import Connection, Exchange, Queue, Producer
from kombu.mixins import ConsumerMixin

from .utils import get_celery_task_log_path
from ..const import CELERY_LOG_MAGIC_MARK

routing_key = 'celery_log'
celery_log_exchange = Exchange('celery_log_exchange', type='direct')
celery_log_queue = [Queue('celery_log', celery_log_exchange, routing_key=routing_key)]


class CeleryLoggerConsumer(ConsumerMixin):
    def __init__(self):
        self.connection = Connection(settings.CELERY_LOG_BROKER_URL)

    def get_consumers(self, Consumer, channel):
        return [Consumer(queues=celery_log_queue,
                         accept=['pickle', 'json'],
                         callbacks=[self.process_task])
                ]

    def handle_task_start(self, task_id, message):
        pass

    def handle_task_end(self, task_id, message):
        pass

    def handle_task_log(self, task_id, msg, message):
        pass

    def process_task(self, body, message):
        action = body.get('action')
        task_id = body.get('task_id')
        msg = body.get('msg')
        if action == CeleryLoggerProducer.ACTION_TASK_LOG:
            self.handle_task_log(task_id, msg, message)
        elif action == CeleryLoggerProducer.ACTION_TASK_START:
            self.handle_task_start(task_id, message)
        elif action == CeleryLoggerProducer.ACTION_TASK_END:
            self.handle_task_end(task_id, message)


class CeleryLoggerProducer:
    ACTION_TASK_START, ACTION_TASK_LOG, ACTION_TASK_END = range(3)

    def __init__(self):
        self.connection = Connection(settings.CELERY_LOG_BROKER_URL)

    @property
    def producer(self):
        return Producer(self.connection)

    def publish(self, payload):
        self.producer.publish(
            payload, serializer='json', exchange=celery_log_exchange,
            declare=[celery_log_exchange], routing_key=routing_key
        )

    def log(self, task_id, msg):
        payload = {'task_id': task_id, 'msg': msg, 'action': self.ACTION_TASK_LOG}
        return self.publish(payload)

    def read(self):
        pass

    def flush(self):
        pass

    def task_end(self, task_id):
        payload = {'task_id': task_id, 'action': self.ACTION_TASK_END}
        return self.publish(payload)

    def task_start(self, task_id):
        payload = {'task_id': task_id, 'action': self.ACTION_TASK_START}
        return self.publish(payload)


class CeleryTaskLoggerHandler(StreamHandler):
    terminator = '\r\n'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        task_prerun.connect(self.on_task_start)
        task_postrun.connect(self.on_start_end)

    @staticmethod
    def get_current_task_id():
        if not current_task:
            return
        task_id = current_task.request.root_id
        return task_id

    def on_task_start(self, sender, task_id, **kwargs):
        return self.handle_task_start(task_id)

    def on_start_end(self, sender, task_id, **kwargs):
        return self.handle_task_end(task_id)

    def after_task_publish(self, sender, body, **kwargs):
        pass

    def emit(self, record):
        task_id = self.get_current_task_id()
        if not task_id:
            return
        try:
            self.write_task_log(task_id, record)
            self.flush()
        except Exception:
            self.handleError(record)

    def write_task_log(self, task_id, msg):
        pass

    def handle_task_start(self, task_id):
        pass

    def handle_task_end(self, task_id):
        pass


class CeleryThreadingLoggerHandler(CeleryTaskLoggerHandler):
    @staticmethod
    def get_current_thread_id():
        return str(get_ident())

    def emit(self, record):
        thread_id = self.get_current_thread_id()
        try:
            self.write_thread_task_log(thread_id, record)
            self.flush()
        except ValueError:
            self.handleError(record)

    def write_thread_task_log(self, thread_id, msg):
        pass

    def handle_task_start(self, task_id):
        pass

    def handle_task_end(self, task_id):
        pass

    def handleError(self, record) -> None:
        pass


class CeleryTaskMQLoggerHandler(CeleryTaskLoggerHandler):
    def __init__(self):
        self.producer = CeleryLoggerProducer()
        super().__init__(stream=None)

    def write_task_log(self, task_id, record):
        msg = self.format(record)
        self.producer.log(task_id, msg)

    def flush(self):
        self.producer.flush()


class CeleryTaskFileHandler(CeleryTaskLoggerHandler):
    def __init__(self, *args, **kwargs):
        self.f = None
        super().__init__(*args, **kwargs)

    def emit(self, record):
        msg = self.format(record)
        if not self.f or self.f.closed:
            return
        self.f.write(msg)
        self.f.write(self.terminator)
        self.flush()

    def flush(self):
        self.f and self.f.flush()

    def handle_task_start(self, task_id):
        log_path = get_celery_task_log_path(task_id)
        self.f = open(log_path, 'a')

    def handle_task_end(self, task_id):
        self.f and self.f.close()


class CeleryThreadTaskFileHandler(CeleryThreadingLoggerHandler):
    def __init__(self, *args, **kwargs):
        self.thread_id_fd_mapper = {}
        self.task_id_thread_id_mapper = {}
        super().__init__(*args, **kwargs)

    def write_thread_task_log(self, thread_id, record):
        f = self.thread_id_fd_mapper.get(thread_id, None)
        if not f:
            raise ValueError('Not found thread task file')
        msg = self.format(record)
        f.write(msg.encode())
        f.write(self.terminator.encode())
        f.flush()

    def flush(self):
        for f in self.thread_id_fd_mapper.values():
            f.flush()

    def handle_task_start(self, task_id):
        log_path = get_celery_task_log_path(task_id)
        thread_id = self.get_current_thread_id()
        self.task_id_thread_id_mapper[task_id] = thread_id
        f = open(log_path, 'ab')
        self.thread_id_fd_mapper[thread_id] = f

    def handle_task_end(self, task_id):
        ident_id = self.task_id_thread_id_mapper.get(task_id, '')
        f = self.thread_id_fd_mapper.pop(ident_id, None)
        if f and not f.closed:
            f.write(CELERY_LOG_MAGIC_MARK)
            f.close()
        self.task_id_thread_id_mapper.pop(task_id, None)
