from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import Mock, patch

from accounts.api.account.application import IntegrationApplicationViewSet
from accounts.api.account.credential import CredentialClientViewSet
from accounts.clients.python.jms_pam.common.credential import Credential
from accounts.clients.python.jms_pam.common.profile.client_profile import ClientProfile
from accounts.clients.python.jms_pam.credential.v1.credential_client import (
    CredentialClient,
)
from accounts.credential_client import commands
from accounts.credential_client.manager import CredentialClientManager
from accounts.models import (
    ApplicationCommand,
    CredentialClientInstance,
    IntegrationApplication,
)
from accounts.tests.base import CredentialTestCase
from django.db import transaction
from django.test import SimpleTestCase
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError


class ApplicationCommandTests(CredentialTestCase):
    def setUp(self):
        super().setUp()
        self.client = CredentialClientInstance.objects.create(
            application=self.application,
            instance_id='sdk-one', type='sdk', protocol_version=1,
        )
        self.other_client = CredentialClientInstance.objects.create(
            application=self.application,
            instance_id='sdk-two', type='sdk', protocol_version=1,
        )

    def send(self, event=commands.RESTART, clients=None, **extra):
        data = {
            'event': event, 'client_ids': clients or [self.client.id],
            'timeout_minutes': 30, **extra,
        }
        return commands.send(self.application, data, self.admin.name)

    def test_selected_recipients_are_frozen_and_published_after_commit(self):
        layer = SimpleNamespace()
        async def group_send(*args):
            layer.sent = args
        layer.group_send = group_send
        with patch('accounts.credential_client.commands.get_channel_layer', return_value=layer):
            with self.captureOnCommitCallbacks(execute=True):
                command = self.send()
                self.assertFalse(hasattr(layer, 'sent'))
        message = layer.sent[1]
        self.assertEqual(message['recipient_ids'], [str(self.client.id)])
        self.assertEqual(message['payload']['command_id'], str(command.id))
        command.refresh_from_db()
        self.assertEqual(command.recipients[0]['publish_result'], 'published')
        self.assertEqual(command.recipients[0]['status'], 'pending')
        self.assertEqual(commands.pending(self.other_client), [])
        self.assertEqual(len(commands.pending(self.client)), 1)

    def test_receipt_is_not_success_and_claim_is_idempotent(self):
        command = self.send()
        self.assertTrue(commands.receive(self.client, command.source_event_id))
        command.refresh_from_db()
        self.assertEqual(command.recipients[0]['status'], 'received')
        self.assertTrue(commands.report(self.client, command.id, 'running')['accepted'])
        self.assertFalse(commands.report(self.client, command.id, 'running')['accepted'])
        self.assertTrue(commands.report(self.client, command.id, 'success')['accepted'])
        self.assertFalse(commands.report(self.client, command.id, 'running')['accepted'])
        self.assertFalse(commands.report(self.client, command.id, 'failed')['accepted'])
        self.assertEqual(commands.pending(self.client), [])

    def test_unselected_instance_cannot_claim_or_report(self):
        command = self.send()
        with self.assertRaises(NotFound):
            commands.report(self.other_client, command.id, 'running')
        with self.assertRaises(NotFound):
            commands.receive(self.other_client, command.source_event_id)
        with self.assertRaises(ValidationError):
            commands.report(self.client, command.id, 'success')

    def test_expired_command_is_not_executed_or_replayed(self):
        command = self.send()
        with patch('accounts.credential_client.commands.timezone.now', return_value=command.expires_at + timedelta(seconds=1)):
            self.assertEqual(commands.pending(self.client), [])
            self.assertEqual(commands.report(self.client, command.id, 'running'), {'accepted': False, 'status': 'timeout'})
            self.assertEqual(commands.detail(command)['recipients'][0]['status'], 'timeout')

    def test_switch_requests_current_published_account_without_changing_policy(self):
        command = self.send(commands.SWITCH, credential_id=self.credential.id)
        self.assertEqual(command.payload['account_id'], str(self.primary.id))
        self.assertEqual(command.payload['revision'], self.credential.revision)
        self.credential.refresh_from_db()
        self.assertEqual(self.credential.status, 'idle')
        self.assertEqual(self.credential.active_account_id, self.primary.id)
        self.assertFalse(self.credential.rotation_records.exists())
        commands.report(self.client, command.id, 'running')
        manager = CredentialClientManager(self.application, instance_id=self.client.instance_id)
        manager.fetch('', '127.0.0.1', account_id=self.primary.id)
        from accounts.models import CredentialClientStatus
        state = CredentialClientStatus.objects.get(client=self.client, binding__credential=self.credential)
        self.assertEqual(state.applied_revision, 0)
        from accounts.credential_client.event_results import report
        self.assertTrue(report(self.client, command.source_event_id)['accepted'])
        state.refresh_from_db()
        self.assertEqual(state.applied_revision, command.payload['revision'])
        self.assertEqual(state.applied_account_id, self.primary.id)

    def test_outdated_switch_request_is_rejected_before_execution(self):
        command = self.send(commands.SWITCH, credential_id=self.credential.id)
        self.credential.revision += 1
        self.credential.save(update_fields=['revision'])
        self.assertEqual(commands.report(self.client, command.id, 'running'), {'accepted': False, 'status': 'failed'})
        command.refresh_from_db()
        self.assertEqual(command.recipients[0]['error_code'], 'superseded')

    def test_wrong_application_disabled_or_unsupported_targets_are_rejected(self):
        app = IntegrationApplication.objects.create(name='Other app')
        outsider = CredentialClientInstance.objects.create(application=app, instance_id='other')
        with self.assertRaises(ValidationError):
            self.send(clients=[outsider.id])
        self.client.is_active = False
        self.client.save()
        with self.assertRaises(ValidationError):
            self.send()
        agent = CredentialClientInstance.objects.create(application=self.application, instance_id='agent', type='agent')
        with self.assertRaises(ValidationError):
            self.send(clients=[agent.id])
        agent.restart_supported = True
        agent.save(update_fields=['restart_supported'])
        self.assertEqual(self.send(clients=[agent.id]).event, commands.RESTART)

    def test_failed_stream_delivery_remains_pollable(self):
        with patch('accounts.credential_client.commands.get_channel_layer', side_effect=RuntimeError('Unavailable')):
            with self.captureOnCommitCallbacks(execute=True):
                command = self.send()
        command.refresh_from_db()
        self.assertEqual(command.recipients[0]['publish_result'], 'failed')
        self.assertEqual(len(commands.pending(self.client)), 1)

    def test_disabling_application_blocks_existing_client_claim_and_receipt(self):
        command = self.send()
        IntegrationApplication.objects.filter(id=self.application.id).update(is_active=False)
        for operation in (
            lambda: commands.report(self.client, command.id, 'running'),
            lambda: commands.receive(self.client, command.source_event_id),
            lambda: commands.pending(self.client),
        ):
            with self.assertRaises(PermissionDenied):
                operation()
        command.refresh_from_db()
        self.assertEqual(command.recipients[0]['status'], 'pending')

    def test_switch_request_requires_policy_change_permission(self):
        view = IntegrationApplicationViewSet.as_view({'post': 'send_event'})
        with patch.object(self.admin, 'has_perm', side_effect=lambda permission, *args: permission == 'accounts.change_integrationapplication'):
            with transaction.atomic():
                response = view(self.request('post', '/', {
                    'event': commands.SWITCH, 'credential_id': str(self.credential.id),
                    'client_ids': [str(self.client.id)],
                }), pk=self.application.id)
        self.assertEqual(response.status_code, 403, response.data)
        self.assertFalse(ApplicationCommand.objects.exists())

    def test_admin_send_and_history_and_client_poll_result_endpoints(self):
        send_view = IntegrationApplicationViewSet.as_view({'post': 'send_event'})
        response = send_view(self.request('post', '/', {
            'event': commands.RESTART, 'client_ids': [str(self.client.id)],
        }), pk=self.application.id)
        self.assertEqual(response.status_code, 201, response.data)
        command_id = response.data['command_id']
        history = IntegrationApplicationViewSet.as_view({'get': 'manual_events'})
        self.assertEqual(history(self.request('get', '/'), pk=self.application.id).data['count'], 1)
        poll = CredentialClientViewSet.as_view({'get': 'commands'})
        response = poll(self.request('get', '/', {'instance_id': self.client.instance_id}, user=self.application))
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data['commands'][0]['command_id'], command_id)
        result = CredentialClientViewSet.as_view({'post': 'command_result'})
        for status in ('running', 'success'):
            response = result(self.request('post', '/', {
                'instance_id': self.client.instance_id, 'command_id': command_id, 'status': status,
            }, user=self.application))
            self.assertEqual(response.status_code, 200, response.data)
            self.assertTrue(response.data['accepted'])
        self.assertEqual(ApplicationCommand.objects.count(), 1)

    def test_unsupported_event_and_invalid_timeout_are_rejected(self):
        view = IntegrationApplicationViewSet.as_view({'post': 'send_event'})
        for extra in ({'event': 'rotation.completed'}, {'timeout_minutes': 0}):
            with transaction.atomic():
                response = view(self.request('post', '/', {
                    'event': commands.RESTART, 'client_ids': [str(self.client.id)], **extra,
                }), pk=self.application.id)
            self.assertEqual(response.status_code, 400, response.data)
        self.assertFalse(ApplicationCommand.objects.exists())


class ApplicationCommandSDKTests(SimpleTestCase):
    def setUp(self):
        self.client = CredentialClient(Credential('app', 'secret'), 'sdk', ClientProfile(endpoint='https://testserver'))
        self.addCleanup(self.client.close)

    def test_duplicate_request_does_not_execute_handler_twice(self):
        handler = Mock()
        self.client.ReportApplicationCommandResult = Mock(side_effect=[
            SimpleNamespace(Accepted=True, Status='running'), SimpleNamespace(Accepted=True, Status='running'), SimpleNamespace(Accepted=False, Status='running'),
        ])
        event = {'command_id': 'command'}
        self.client.ExecuteApplicationCommand(event, handler)
        self.client.ExecuteApplicationCommand(event, handler)
        handler.assert_called_once_with(event)

    def test_handler_failure_reports_failed_result(self):
        self.client.ReportApplicationCommandResult = Mock(return_value=SimpleNamespace(Accepted=True, Status='running'))
        with self.assertRaises(RuntimeError):
            self.client.ExecuteApplicationCommand({'command_id': 'command'}, Mock(side_effect=RuntimeError('failed')))
        result = self.client.ReportApplicationCommandResult.call_args.args[0]
        self.assertEqual(result.Status, 'failed')
        self.assertEqual(result.ErrorCode, 'execution_failed')
