from unittest.mock import patch

from django.db import connection, transaction
from django.test import SimpleTestCase

from accounts.api.account.application import IntegrationApplicationViewSet
from accounts.const import ApplicationEvent
from accounts.models import ApplicationWebhook, IntegrationApplication
from accounts.tests.base import CredentialTestCase
from accounts.webhooks import (
    MAX_TEMPLATE_BYTES, WebhookValidationError, render_webhook_template,
    validate_webhook_headers, validate_webhook_template, validate_webhook_url,
)
from audits.const import MODELS_NEED_RECORD
from orgs.models import Organization
from orgs.utils import tmp_to_org
from users.models import User


class ApplicationWebhookTemplateTests(SimpleTestCase):
    def test_renderer_allows_only_named_fields_and_preserves_exact_value_type(self):
        template = {
            'revision': '{{ credential.revision }}',
            'message': '{{ event.code }} revision {{ credential.revision }}',
            'missing': '{{ rotation.id }}',
        }
        context = {
            'event': {'code': 'credential.published'},
            'credential': {'revision': 3},
            'rotation': {'id': None},
        }

        self.assertEqual(render_webhook_template(template, context), {
            'revision': 3,
            'message': 'credential.published revision 3',
            'missing': None,
        })

        for invalid in (
            {'{{ event.code }}': 'dynamic key'},
            {'value': '{{ event.code|upper }}'},
            {'value': '{{ event.unknown }}'},
            {'value': '{{{ event.code }}'},
            {'value': '{{ event.code }}}'},
            {'value': '{% if event.code %}x{% endif %}'},
            {'value': '{# hidden #}'},
        ):
            with self.subTest(invalid=invalid), self.assertRaises(WebhookValidationError):
                validate_webhook_template(invalid)

        nested = {}
        child = nested
        for _ in range(17):
            child['nested'] = {}
            child = child['nested']
        with self.assertRaises(WebhookValidationError):
            validate_webhook_template(nested)
        with self.assertRaises(WebhookValidationError):
            validate_webhook_template({'value': 'x' * MAX_TEMPLATE_BYTES})
        with self.assertRaises(WebhookValidationError):
            render_webhook_template(
                {'value': '{{ event.summary }}{{ event.summary }}'},
                {'event': {'summary': 'x' * (MAX_TEMPLATE_BYTES // 2)}},
            )

    def test_url_and_headers_reject_request_smuggling_and_unsafe_targets(self):
        self.assertEqual(validate_webhook_url('https://10.0.0.8/hook'), 'https://10.0.0.8/hook')
        for url in (
            'http://127.0.0.1/hook',
            'http://10.0.0.8:0/hook',
            'http://169.254.169.254/latest/meta-data',
            'http://100.100.100.200/latest/meta-data',
            'http://[fd00:ec2::254]/latest/meta-data',
        ):
            with self.subTest(url=url), self.assertRaises(WebhookValidationError):
                validate_webhook_url(url)
        for headers in (
            {'Host': 'internal'},
            {'X-Forwarded-For': '127.0.0.1'},
            {'X-HTTP-Method-Override': 'DELETE'},
            {'X-JMS-Event-ID': 'forged'},
            {'X-Target': 'one', 'x-target': 'two'},
            {'Authorization': 'Bearer ok\r\nX-Forged: yes'},
            {'Authorization': 'Bearer\x00secret'},
            {'Authorization': 'Bearer 中文'},
            {'Authorization': '{{ event.id }}'},
        ):
            with self.subTest(headers=headers), self.assertRaises(WebhookValidationError):
                validate_webhook_headers(headers)


class ApplicationWebhookConfigAPITests(CredentialTestCase):
    webhook_path = '/api/v1/accounts/integration-applications/{}/webhook/'

    def call_webhook(self, method, data=None):
        action = 'webhook' if method == 'get' else 'update_webhook'
        view = IntegrationApplicationViewSet.as_view({method: action})
        request = self.request(
            method, self.webhook_path.format(self.application.id), data,
        )
        with transaction.atomic():
            return view(request, pk=self.application.id)

    def test_get_defaults_without_creating_configuration(self):
        response = self.call_webhook('get')

        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.data['id'])
        self.assertFalse(response.data['is_active'])
        self.assertEqual(response.data['method'], 'POST')
        self.assertEqual(response.data['events'], list(ApplicationEvent.values))
        self.assertNotIn('url', response.data)
        self.assertNotIn('headers', response.data)
        self.assertEqual(
            set(response.data['template_variables'][0]),
            {'name', 'label', 'default'},
        )
        self.assertFalse(ApplicationWebhook.objects.exists())

    def test_sensitive_configuration_is_excluded_from_global_operate_logs(self):
        self.assertNotIn('ApplicationWebhook', MODELS_NEED_RECORD)

    def test_invalid_patch_does_not_persist_default_row(self):
        response = self.call_webhook('patch', {'is_active': True})

        self.assertEqual(response.status_code, 400)
        self.assertFalse(ApplicationWebhook.objects.exists())

    def test_configuration_is_unique_rbac_protected_and_org_scoped(self):
        ApplicationWebhook.objects.create(application=self.application)
        self.assertTrue(ApplicationWebhook._meta.get_field('application').unique)

        user = User.objects.create(username='webhook-no-permission', name='No permission')
        view = IntegrationApplicationViewSet.as_view({'get': 'webhook'})
        with transaction.atomic():
            response = view(
                self.request(
                    'get', self.webhook_path.format(self.application.id), user=user,
                ),
                pk=self.application.id,
            )
        self.assertEqual(response.status_code, 403)

        other_org = Organization.objects.create(name='Webhook isolated org')
        with tmp_to_org(other_org):
            other_application = IntegrationApplication.objects.create(
                name='isolated-application', secret='isolated-secret',
            )
        with transaction.atomic():
            response = view(
                self.request('get', self.webhook_path.format(other_application.id)),
                pk=other_application.id,
            )
        self.assertEqual(response.status_code, 404)

    def test_patch_encrypts_secrets_masks_response_and_omission_retains_values(self):
        payload = {
            'is_active': True,
            'url': 'https://8.8.8.8/hooks/private-token',
            'method': 'PATCH',
            'headers': {'Authorization': 'Bearer private-header'},
            'events': ['rotation.failed'],
            'body_template': {'text': '{{ event.code }}: {{ application.name }}'},
        }
        response = self.call_webhook('patch', payload)

        self.assertEqual(response.status_code, 200)
        self.assertNotIn('url', response.data)
        self.assertNotIn('headers', response.data)
        self.assertEqual(response.data['url_display'], 'https://8.8.8.8/***')
        self.assertEqual(response.data['header_names'], ['Authorization'])
        webhook = ApplicationWebhook.objects.get(application=self.application)
        self.assertEqual(webhook.url, payload['url'])
        self.assertEqual(webhook.headers, payload['headers'])
        with connection.cursor() as cursor:
            cursor.execute(
                'SELECT url, headers FROM accounts_applicationwebhook WHERE id = %s',
                [str(webhook.id)],
            )
            raw_url, raw_headers = cursor.fetchone()
        self.assertNotIn('private-token', raw_url)
        self.assertNotIn('private-header', raw_headers)

        response = self.call_webhook('patch', {'method': 'POST'})
        self.assertEqual(response.status_code, 200)
        webhook.refresh_from_db()
        self.assertEqual(webhook.url, payload['url'])
        self.assertEqual(webhook.headers, payload['headers'])

    def test_preview_and_test_use_unsaved_configuration(self):
        preview = IntegrationApplicationViewSet.as_view({'post': 'webhook_preview'})
        request = self.request('post', self.webhook_path.format(self.application.id) + 'preview/', {
            'event': 'credential.published',
            'body_template': {
                'event': '{{ event.code }}',
                'revision': '{{ credential.revision }}',
            },
        })
        response = preview(request, pk=self.application.id)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['body']['event'], 'credential.published')
        self.assertEqual(response.data['body']['revision'], 1)

        test = IntegrationApplicationViewSet.as_view({'post': 'webhook_test'})
        request = self.request('post', self.webhook_path.format(self.application.id) + 'test/', {
            'url': 'https://8.8.8.8/hook',
            'method': 'POST',
            'headers': {'X-Target': 'test'},
            'events': ['credential.published'],
            'event': 'credential.published',
            'body_template': {'event': '{{ event.code }}'},
        })
        with patch(
            'accounts.credential_client.webhook_delivery.send_webhook', return_value=204,
        ) as sender:
            response = test(request, pk=self.application.id)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, {'success': True, 'status_code': 204, 'reason': ''})
        self.assertEqual(sender.call_args.args[3], {'event': 'credential.published'})
        self.assertFalse(ApplicationWebhook.objects.exists())
