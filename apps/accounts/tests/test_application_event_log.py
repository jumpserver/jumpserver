from datetime import timedelta
from uuid import uuid4

from django.utils import timezone
from orgs.models import Organization
from orgs.utils import tmp_to_org
from users.models import User

from accounts.api.account.application_event_log import ApplicationEventLogViewSet
from accounts.const import ApplicationEvent
from accounts.credential_client.audit import record
from accounts.models import (
    ApplicationAudit, ApplicationCommand, ApplicationEventDelivery,
    CredentialRotationEvent, IntegrationApplication,
)
from accounts.tests.base import CredentialTestCase


class ApplicationEventLogTests(CredentialTestCase):
    def notification(self, code='app.scope.updated', recipients=None, applications=None):
        source = record('configuration_updated', application=self.application,
                        applications=applications or [self.application])
        CredentialRotationEvent.objects.create(
            source_event_id=source.id, event=code, sequence=1,
            recipients=recipients or [], org_id=self.org.id,
        )
        return source

    def get(self, params=None, pk=None, user=None):
        view = ApplicationEventLogViewSet.as_view({'get': 'retrieve' if pk else 'list'})
        request = self.request('get', '/application-event-logs/', {'limit': 100, **(params or {})}, user)
        return view(request, **({'pk': pk} if pk else {}))

    def test_activity_is_retained_but_event_log_uses_actual_protocol_types(self):
        activity = record('configuration_updated', application=self.application)
        source = self.notification()
        response = self.get()
        self.assertEqual(response.status_code, 200, response.data)
        rows = {row['id']: row for row in response.data['results']}
        self.assertNotIn(str(activity.id), rows)
        self.assertTrue(ApplicationAudit.objects.filter(id=activity.id).exists())
        self.assertEqual(rows[str(source.id)]['event'], 'app.scope.updated')
        self.assertNotIn('configuration_updated', {row['event'] for row in rows.values()})

    def test_manual_commands_and_notifications_share_stable_pagination(self):
        source = self.notification()
        audit = record('command_requested', application=self.application, applications=[self.application])
        ApplicationCommand.objects.create(
            application=self.application, source_event=audit, event='app.restart.requested',
            expires_at=timezone.now() + timedelta(minutes=5), org_id=self.org.id,
            recipients=[{'id': str(uuid4()), 'instance_id': 'manual', 'type': 'sdk',
                         'status': 'pending', 'received_at': None, 'publish_result': 'pending'}],
        )
        first, second = self.get({'limit': 1}), self.get({'limit': 1, 'offset': 1})
        self.assertEqual(first.data['results'][0]['id'], str(audit.id))
        self.assertEqual(first.data['results'][0]['event'], 'app.restart.requested')
        self.assertEqual(first.data['results'][0]['event_source'], 'manual')
        self.assertEqual(second.data['results'][0]['id'], str(source.id))
        self.assertEqual(first.data['count'], second.data['count'])

    def test_filters_target_protocol_codes_instead_of_activity_codes(self):
        source = self.notification()
        response = self.get({'event__in': 'app.scope.updated,credential.switch.published'})
        self.assertIn(str(source.id), {row['id'] for row in response.data['results']})
        self.assertTrue(all(row['event'] in ('app.scope.updated', 'credential.switch.published')
                            for row in response.data['results']))
        self.assertEqual(self.get({'event': 'configuration_updated'}).status_code, 400)
        self.assertEqual(self.get({'application': 'invalid'}).status_code, 400)

    def test_org_isolation_applies_to_list_and_detail(self):
        other = Organization.objects.create(name='Event log other org')
        with tmp_to_org(other):
            audit = ApplicationAudit.objects.create(event='configuration_updated')
            CredentialRotationEvent.objects.create(source_event_id=audit.id, event='app.scope.updated', sequence=1)
        rows = self.get().data['results']
        self.assertNotIn(str(audit.id), {row['id'] for row in rows})
        self.assertEqual(self.get(pk=audit.id).status_code, 404)

    def test_log_permission_is_required(self):
        user = User.objects.create_user(username='event-log-outsider', password='password')
        self.assertEqual(self.get(user=user).status_code, 403)

    def test_application_filter_does_not_leak_other_recipients(self):
        sibling = IntegrationApplication.objects.create(name='sibling', secret='private')
        recipients = [{
            'id': str(uuid4()), 'instance_id': app.name, 'type': 'sdk', 'status': 'pending',
            'application': {'id': str(app.id), 'name': app.name},
            'received_at': None, 'publish_result': 'pending',
        } for app in (self.application, sibling)]
        source = self.notification(recipients=recipients, applications=[self.application, sibling])
        response = self.get({'application': str(self.application.id)})
        row = next(row for row in response.data['results'] if row['id'] == str(source.id))
        self.assertEqual([item['application']['id'] for item in row['recipients']], [str(self.application.id)])

    def test_failure_review_and_webhook_results_are_visible_without_webhook_secrets(self):
        failure = {'id': str(uuid4()), 'review_required': True, 'error_code': 'application_check_failed'}
        source = self.notification(code=ApplicationEvent.CREDENTIAL_SWITCH_PUBLISHED, recipients=[{
            'id': str(uuid4()), 'instance_id': 'recovered', 'type': 'sdk', 'status': 'success',
            'application': {'id': str(self.application.id), 'name': self.application.name},
            'received_at': timezone.now().isoformat(), 'publish_result': 'published',
            'failure_review': failure,
        }])
        delivery_audit = record('notification', application=self.application)
        ApplicationEventDelivery.objects.create(
            event=source, audit=delivery_audit, code=ApplicationEvent.CREDENTIAL_SWITCH_PUBLISHED,
            url='https://example.invalid/hook?token=never-expose', method='POST',
            headers={'Authorization': 'never-expose'}, body={'secret': 'never-expose'},
            status='success', expires_at=timezone.now() + timedelta(minutes=1), org_id=self.org.id,
        )
        response = self.get(pk=source.id)
        self.assertEqual(response.status_code, 200, response.data)
        self.assertTrue(response.data['recipients'][0]['failure_review']['review_required'])
        self.assertEqual(response.data['webhooks'][0]['status'], 'success')
        self.assertNotIn('never-expose', str(response.data))
