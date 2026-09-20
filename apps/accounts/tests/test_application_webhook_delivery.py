import socket
from datetime import timedelta
from unittest.mock import Mock, call, patch

from django.test import SimpleTestCase, override_settings
from django.utils import timezone

from accounts.api.account.application_audit import ApplicationAuditViewSet
from accounts.const import ApplicationEvent, AuditEvent
from accounts.credential_client.audit import record
from accounts.credential_client.events import enqueue
from accounts.credential_client.webhook_delivery import WebhookRequestError, send_webhook
from accounts.models import (
    ApplicationAudit, ApplicationEventAttempt, ApplicationEventDelivery, ApplicationWebhook,
)
from accounts.tasks.application_events import (
    clean_application_records_period, deliver_application_webhook,
    expire_application_event_deliveries,
)
from accounts.tests.base import CredentialTestCase
from common.const.crontab import CRONTAB_AT_AM_THREE
from ops.celery.decorator import get_register_period_tasks


class ApplicationWebhookDeliveryTests(CredentialTestCase):
    def setUp(self):
        super().setUp()
        self.credential.applications.add(self.application)
        self.webhook = ApplicationWebhook.objects.create(
            application=self.application, is_active=True,
            url='https://hooks.example/events', method='POST',
            headers={'Authorization': 'Bearer saved-token'},
            events=list(ApplicationEvent.values),
            body_template={
                'event': '{{ event.code }}',
                'application': '{{ application.name }}',
                'revision': '{{ credential.revision }}',
            },
        )

    def enqueue_event(self, code=ApplicationEvent.CREDENTIAL_PUBLISHED):
        event = record(AuditEvent.CREDENTIAL_PUBLISHED, credential=self.credential)
        with patch(
            'accounts.credential_client.events._dispatch_webhook',
        ) as dispatch, self.captureOnCommitCallbacks(execute=True):
            enqueue(event, code)
        return event, dispatch

    def test_selected_event_is_snapshotted_once_and_dispatched_after_commit(self):
        event, dispatch = self.enqueue_event()
        delivery = ApplicationEventDelivery.objects.get(event=event, webhook=self.webhook)

        self.assertEqual(delivery.method, 'POST')
        self.assertEqual(delivery.url, 'https://hooks.example/events')
        self.assertEqual(delivery.headers, {'Authorization': 'Bearer saved-token'})
        self.assertEqual(delivery.body, {
            'event': 'credential.published', 'application': 'order-service',
            'revision': self.credential.revision,
        })
        self.assertAlmostEqual(
            (delivery.expires_at - delivery.date_created).total_seconds(), 90, delta=2,
        )
        dispatch.assert_called_once_with(delivery.id, self.org.id)

        self.webhook.url = 'https://changed.example/events'
        self.webhook.headers = {'Authorization': 'changed'}
        self.webhook.save(update_fields=['url', 'headers'])
        enqueue(event, ApplicationEvent.CREDENTIAL_PUBLISHED)
        self.assertEqual(ApplicationEventDelivery.objects.filter(event=event, webhook=self.webhook).count(), 1)
        delivery.refresh_from_db()
        self.assertEqual(delivery.url, 'https://hooks.example/events')
        self.assertEqual(delivery.headers, {'Authorization': 'Bearer saved-token'})

    def test_audit_detail_masks_webhook_url_and_headers(self):
        self.webhook.url = 'https://hooks.example/events/private?token=url-secret'
        self.webhook.save(update_fields=['url'])
        _, _ = self.enqueue_event()
        delivery = ApplicationEventDelivery.objects.get(webhook=self.webhook)

        request = self.request(
            'get', f'/api/v1/accounts/application-audits/{delivery.audit_id}/',
        )
        response = ApplicationAuditViewSet.as_view({'get': 'retrieve'})(
            request, pk=delivery.audit_id,
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['notification']['url'], 'https://hooks.example/***')
        content = response.render().content.decode()
        self.assertNotIn('url-secret', content)
        self.assertNotIn('saved-token', content)

    def test_disabled_or_unselected_webhook_is_not_enqueued(self):
        self.webhook.events = [ApplicationEvent.ACCESS_REVOKED]
        self.webhook.save(update_fields=['events'])
        event, dispatch = self.enqueue_event()
        self.assertFalse(ApplicationEventDelivery.objects.filter(event=event, webhook=self.webhook).exists())
        dispatch.assert_not_called()

        self.webhook.events = list(ApplicationEvent.values)
        self.webhook.is_active = False
        self.webhook.save(update_fields=['events', 'is_active'])
        event, dispatch = self.enqueue_event()
        self.assertFalse(ApplicationEventDelivery.objects.filter(event=event, webhook=self.webhook).exists())
        dispatch.assert_not_called()

    def test_invalid_stored_template_does_not_break_event_enqueue(self):
        self.webhook.body_template = {'event': '{{ unknown.field }}'}
        self.webhook.save(update_fields=['body_template'])
        event = record(AuditEvent.CREDENTIAL_PUBLISHED, credential=self.credential)

        with patch('accounts.credential_client.events.logger') as logger:
            enqueue(event, ApplicationEvent.CREDENTIAL_PUBLISHED)

        self.assertFalse(ApplicationEventDelivery.objects.filter(event=event).exists())
        logger.warning.assert_called_once_with(
            'Skipping invalid application webhook %s.', self.webhook.id,
        )

    def test_deleted_webhook_still_delivers_from_snapshot(self):
        event, _ = self.enqueue_event()
        delivery = ApplicationEventDelivery.objects.get(event=event, webhook=self.webhook)
        self.webhook.delete()
        delivery.refresh_from_db()
        self.assertIsNone(delivery.webhook_id)

        with patch(
            'accounts.credential_client.webhook_delivery.send_webhook', return_value=204,
        ) as send:
            deliver_application_webhook(str(delivery.id), delivery.org_id)

        delivery.refresh_from_db()
        self.assertEqual(delivery.status, 'success')
        send.assert_called_once_with(
            'POST', 'https://hooks.example/events',
            {'Authorization': 'Bearer saved-token'}, delivery.body,
            delivery_id=delivery.id, event_id=event.id,
        )

    def test_non_2xx_retries_at_5_and_15_seconds_then_fails(self):
        event, _ = self.enqueue_event()
        delivery = ApplicationEventDelivery.objects.get(event=event, webhook=self.webhook)
        with patch(
            'accounts.credential_client.webhook_delivery.send_webhook', return_value=500,
        ), patch(
            'accounts.tasks.application_events.dispatch_application_webhook',
        ) as dispatch:
            for number in range(1, 4):
                with self.captureOnCommitCallbacks(execute=True):
                    deliver_application_webhook(str(delivery.id), delivery.org_id)
                delivery.refresh_from_db()
                self.assertEqual(delivery.attempts.count(), number)
                if number < 3:
                    ApplicationEventDelivery.objects.filter(id=delivery.id).update(
                        available_at=timezone.now(),
                    )

        self.assertEqual(
            dispatch.call_args_list,
            [call(delivery.id, self.org.id, 5), call(delivery.id, self.org.id, 15)],
        )
        delivery.refresh_from_db()
        delivery.audit.refresh_from_db()
        self.assertEqual(delivery.status, 'failed')
        self.assertEqual(delivery.audit.result, 'failed')
        self.assertEqual(
            list(delivery.attempts.values_list('status_code', flat=True)), [500, 500, 500],
        )

    def test_deadline_and_periodic_recovery(self):
        event, _ = self.enqueue_event()
        delivery = ApplicationEventDelivery.objects.get(event=event, webhook=self.webhook)
        ApplicationEventDelivery.objects.filter(id=delivery.id).update(
            expires_at=timezone.now() - timedelta(seconds=1),
        )
        with patch(
            'accounts.tasks.application_events.dispatch_application_webhook',
        ) as dispatch:
            expire_application_event_deliveries()
        delivery.refresh_from_db()
        self.assertEqual(delivery.status, 'failed')
        dispatch.assert_not_called()

        event, _ = self.enqueue_event()
        delivery = ApplicationEventDelivery.objects.get(event=event, webhook=self.webhook)
        ApplicationEventDelivery.objects.filter(id=delivery.id).update(available_at=timezone.now())
        with patch(
            'accounts.tasks.application_events.dispatch_application_webhook',
        ) as dispatch:
            expire_application_event_deliveries()
        dispatch.assert_called_once_with(delivery.id, str(self.org.id))

    @override_settings(APPLICATION_RECORD_KEEP_DAYS=30)
    def test_periodic_cleanup_removes_only_expired_completed_records(self):
        expired_at = timezone.now() - timedelta(days=31)
        recent = record(AuditEvent.CONFIGURATION_UPDATED, application=self.application)
        expired = record(AuditEvent.CONFIGURATION_UPDATED, application=self.application)
        ApplicationAudit.objects.filter(id=expired.id).update(date_created=expired_at)

        completed_event, _ = self.enqueue_event()
        completed = ApplicationEventDelivery.objects.get(event=completed_event)
        completed.status = 'success'
        completed.save(update_fields=['status'])
        attempt = ApplicationEventAttempt.objects.create(
            delivery=completed, number=1, result='success', status_code=204,
        )

        pending_event, _ = self.enqueue_event()
        pending = ApplicationEventDelivery.objects.get(event=pending_event)
        old_ids = [
            completed_event.id, completed.audit_id,
            pending_event.id, pending.audit_id,
        ]
        ApplicationAudit.objects.filter(id__in=old_ids).update(date_created=expired_at)
        ApplicationEventDelivery.objects.filter(id__in=[completed.id, pending.id]).update(
            date_created=expired_at,
        )
        ApplicationEventAttempt.objects.filter(id=attempt.id).update(date_created=expired_at)

        clean_application_records_period()

        self.assertFalse(ApplicationAudit.objects.filter(id=expired.id).exists())
        self.assertFalse(ApplicationEventDelivery.objects.filter(id=completed.id).exists())
        self.assertFalse(ApplicationEventAttempt.objects.filter(id=attempt.id).exists())
        self.assertFalse(ApplicationAudit.objects.filter(id__in=[completed_event.id, completed.audit_id]).exists())
        self.assertTrue(ApplicationAudit.objects.filter(id=recent.id).exists())
        self.assertTrue(ApplicationEventDelivery.objects.filter(id=pending.id).exists())
        self.assertEqual(
            ApplicationAudit.objects.filter(id__in=[pending_event.id, pending.audit_id]).count(), 2,
        )

    def test_periodic_cleanup_runs_at_three_am(self):
        task_name = 'accounts.tasks.application_events.clean_application_records_period'
        task = next(item[task_name] for item in get_register_period_tasks() if task_name in item)
        self.assertEqual(task['crontab'], CRONTAB_AT_AM_THREE)


class WebhookSenderTests(SimpleTestCase):
    @staticmethod
    def address(ip, port=80):
        family = socket.AF_INET6 if ':' in ip else socket.AF_INET
        return [(family, socket.SOCK_STREAM, 6, '', (ip, port))]

    def test_private_target_is_pinned_and_redirects_are_disabled(self):
        connection = Mock()
        connection.getresponse.return_value = Mock(status=204)
        sock = Mock()
        with patch(
            'accounts.credential_client.webhook_delivery.socket.getaddrinfo',
            return_value=self.address('10.0.0.8'),
        ), patch(
            'accounts.credential_client.webhook_delivery.socket.create_connection',
            return_value=sock,
        ) as create_connection, patch(
            'accounts.credential_client.webhook_delivery.http.client.HTTPConnection',
            return_value=connection,
        ) as connection_class:
            status = send_webhook(
                'POST', 'http://hooks.example/events?source=jms',
                {'Authorization': 'Bearer token'}, {'text': '中文'},
                delivery_id='delivery-id', event_id='event-id',
            )
            connection._create_connection(('hooks.example', 80))

        self.assertEqual(status, 204)
        connection_class.assert_called_once_with('hooks.example', 80, timeout=5)
        create_connection.assert_called_once_with(
            ('10.0.0.8', 80), timeout=3, source_address=None,
        )
        sock.settimeout.assert_called_once_with(5)
        request = connection.request.call_args
        self.assertEqual(request.args[:2], ('POST', '/events?source=jms'))
        self.assertEqual(request.kwargs['body'], '{"text":"中文"}'.encode())
        self.assertEqual(request.kwargs['headers']['Host'], 'hooks.example')
        self.assertEqual(request.kwargs['headers']['X-JMS-Delivery-ID'], 'delivery-id')
        self.assertEqual(request.kwargs['headers']['X-JMS-Event-ID'], 'event-id')

    def test_unsafe_targets_and_reserved_headers_are_rejected(self):
        for address in ('127.0.0.1', '169.254.169.254', '100.100.100.200', '224.0.0.1'):
            with self.subTest(address=address), patch(
                'accounts.credential_client.webhook_delivery.socket.getaddrinfo',
                return_value=self.address(address),
            ), self.assertRaises(WebhookRequestError) as error:
                send_webhook('POST', 'http://hooks.example/events', {}, {})
            self.assertFalse(error.exception.retryable)

        with patch(
            'accounts.credential_client.webhook_delivery.socket.getaddrinfo',
            return_value=self.address('203.0.113.10'),
        ), self.assertRaises(WebhookRequestError):
            send_webhook(
                'POST', 'http://hooks.example/events', {'X-JMS-Event-ID': 'override'}, {},
            )
        with patch(
            'accounts.credential_client.webhook_delivery.socket.getaddrinfo',
            return_value=self.address('203.0.113.10'),
        ), self.assertRaises(WebhookRequestError) as error:
            send_webhook(
                'POST', 'http://hooks.example/events', {}, {'value': '中' * (64 * 1024)},
            )
        self.assertFalse(error.exception.retryable)

    def test_dns_failure_is_retryable(self):
        with patch(
            'accounts.credential_client.webhook_delivery.socket.getaddrinfo',
            side_effect=OSError,
        ), self.assertRaises(WebhookRequestError) as error:
            send_webhook('POST', 'https://hooks.example/events', {}, {})

        self.assertTrue(error.exception.retryable)

    @override_settings(VERIFY_EXTERNAL_SSL=True)
    def test_https_uses_original_hostname_for_sni_and_verification(self):
        connection = Mock()
        connection.getresponse.return_value = Mock(status=200)
        context = Mock()
        with patch(
            'accounts.credential_client.webhook_delivery.socket.getaddrinfo',
            return_value=self.address('8.8.8.8', 443),
        ), patch(
            'accounts.credential_client.webhook_delivery.ssl.create_default_context',
            return_value=context,
        ), patch(
            'accounts.credential_client.webhook_delivery.http.client.HTTPSConnection',
            return_value=connection,
        ) as connection_class:
            send_webhook('POST', 'https://hooks.example/events', {}, {})

        connection_class.assert_called_once_with(
            'hooks.example', 443, timeout=5, context=context,
        )
