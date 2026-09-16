"""Shared SDK/Agent listener. JumpServer owns retry scheduling; delivery is at-least-once."""
import threading
import uuid

from .common.exception import JumpServerPAMSDKException
from .credential.v1 import models


class DeliveryError(Exception):
    def __init__(self, reason, status_code=None):
        self.reason, self.status_code = reason, status_code
        super().__init__(reason)


class EventWorker(threading.Thread):
    def __init__(self, remote, handler, interval=5):
        super().__init__(name='jms-pam-events', daemon=True)
        self.remote, self.handler, self.interval = remote, handler, interval
        self.stopping = threading.Event()
        self.last_error = None
        self.pending_report = None

    @staticmethod
    def report_request(report):
        names = {
            'attempt_id': 'AttemptId', 'result': 'Result',
            'status_code': 'StatusCode', 'reason': 'Reason',
        }
        return models.ReportEventRequest(**{
            names[key]: value for key, value in report.items()
        })

    def deliver(self, event):
        payload = {key: value for key, value in event.items() if key not in ('attempt_id', 'delivery_id')}
        report = {'attempt_id': event['attempt_id'], 'result': 'success'}
        try:
            status_code = self.handler(payload)
            if self.remote.source == 'jms-pam-agent':
                report['status_code'] = status_code
        except DeliveryError as error:
            report.update(result='failed', reason=error.reason, status_code=error.status_code)
        except Exception:
            report.update(result='failed', reason='callback_failed')
        self.pending_report = report

    def step(self):
        if self.pending_report:
            self.remote.ReportEvent(self.report_request(self.pending_report))
            self.pending_report = None
        response = self.remote.PollEvents(models.PollEventsRequest())
        if not response.Enabled:
            self.stopping.set()
            return
        for item in response.Events:
            if self.stopping.is_set():
                break
            event = item._serialize()
            self.deliver(event)
            # Retain the report on network failure; do not immediately re-invoke the handler.
            self.remote.ReportEvent(self.report_request(self.pending_report))
            self.pending_report = None

    def run(self):
        subscribed = False
        try:
            while not self.stopping.is_set():
                try:
                    if not subscribed:
                        request = models.SubscribeEventsRequest(Enabled=True)
                        subscribed = self.remote.SubscribeEvents(request).Enabled
                        if not subscribed:
                            break
                    self.step()
                    self.last_error = None
                except JumpServerPAMSDKException as error:
                    self.last_error = error
                    if error.status_code in (401, 403):
                        # No privileged exception for disabled clients. This is a local observation.
                        try:
                            self.handler({
                                'event_id': str(uuid.uuid4()), 'event': 'access.stopped',
                                'instance_id': self.remote.instance_id, 'origin': 'client',
                            })
                        except Exception:
                            pass
                        break
                except (ValueError, KeyError) as error:
                    self.last_error = error
                self.stopping.wait(self.interval)
        finally:
            if subscribed:
                try:
                    self.remote.SubscribeEvents(models.SubscribeEventsRequest(Enabled=False))
                except JumpServerPAMSDKException:
                    pass
            self.remote.close()

    def close(self):
        self.stopping.set()
        if threading.current_thread() is not self and self.is_alive():
            self.join(timeout=15)
