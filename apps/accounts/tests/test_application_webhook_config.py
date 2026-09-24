from unittest.mock import patch

from django.db import connection, transaction
from django.test import SimpleTestCase
from django.urls import Resolver404, resolve

from accounts.api.account.application import ApplicationWebhookViewSet
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
    def test_preview_endpoint_is_not_exposed(self):
        with self.assertRaises(Resolver404):
            resolve(
                '/api/v1/accounts/application-webhooks/'
                '00000000-0000-0000-0000-000000000001/preview/'
            )

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
    webhook_path = '/api/v1/accounts/application-webhooks/'

    def create_webhook(self, **overrides):
        data = {
            'name': 'Operations notifications',
            'applications': [str(self.application.id)],
            'is_active': True,
            'url': 'https://8.8.8.8/hooks/private-token',
            'method': 'POST',
            'headers': {'Authorization': 'Bearer private-header'},
            'events': [ApplicationEvent.CREDENTIAL_UPDATED],
            'body_template': {'event': '{{ event.code }}'},
        }
        data.update(overrides)
        view = ApplicationWebhookViewSet.as_view({'post': 'create'})
        with transaction.atomic():
            return view(self.request('post', self.webhook_path, data))

    def test_metadata_exposes_shared_events_and_template_variables(self):
        view = ApplicationWebhookViewSet.as_view({'get': 'metadata'})
        response = view(self.request('get', self.webhook_path + 'metadata/'))
        self.assertEqual(response.status_code, 200)
        self.assertIn(ApplicationEvent.CREDENTIAL_UPDATED, {
            item['value'] for item in response.data['event_options']
        })
        self.assertEqual(set(response.data['template_variables'][0]), {'name', 'label', 'default'})

    def test_sensitive_configuration_is_excluded_from_global_operate_logs(self):
        self.assertNotIn('ApplicationWebhook', MODELS_NEED_RECORD)

    def test_applications_and_active_url_are_required(self):
        response = self.create_webhook(applications=[])
        self.assertEqual(response.status_code, 400)
        self.assertFalse(ApplicationWebhook.objects.exists())
        response = self.create_webhook(url='')
        self.assertEqual(response.status_code, 400)

    def test_rules_are_rbac_protected_and_org_scoped(self):
        user = User.objects.create(username='webhook-no-permission', name='No permission')
        view = ApplicationWebhookViewSet.as_view({'get': 'list'})
        with transaction.atomic():
            response = view(self.request('get', self.webhook_path, user=user))
        self.assertEqual(response.status_code, 403)

        other_org = Organization.objects.create(name='Webhook isolated org')
        with tmp_to_org(other_org):
            other_application = IntegrationApplication.objects.create(
                name='isolated-application', secret='isolated-secret',
            )
            other_webhook = ApplicationWebhook.objects.create(name='Isolated')
            other_webhook.applications.add(other_application)
        view = ApplicationWebhookViewSet.as_view({'get': 'retrieve'})
        with transaction.atomic():
            response = view(self.request('get', self.webhook_path), pk=other_webhook.id)
        self.assertEqual(response.status_code, 404)

    def test_create_encrypts_secrets_masks_response_and_patch_retains_values(self):
        response = self.create_webhook()
        self.assertEqual(response.status_code, 201, response.data)
        self.assertNotIn('url', response.data)
        self.assertNotIn('headers', response.data)
        self.assertEqual(response.data['url_display'], 'https://8.8.8.8/***')
        self.assertEqual(response.data['header_names'], ['Authorization'])
        webhook = ApplicationWebhook.objects.get(pk=response.data['id'])
        self.assertEqual(webhook.url, 'https://8.8.8.8/hooks/private-token')
        self.assertEqual(webhook.headers, {'Authorization': 'Bearer private-header'})
        with connection.cursor() as cursor:
            cursor.execute(
                'SELECT url, headers FROM accounts_applicationwebhook WHERE id = %s',
                [str(webhook.id)],
            )
            raw_url, raw_headers = cursor.fetchone()
        self.assertNotIn('private-token', raw_url)
        self.assertNotIn('private-header', raw_headers)

        view = ApplicationWebhookViewSet.as_view({'patch': 'partial_update'})
        response = view(self.request('patch', self.webhook_path, {'method': 'PATCH'}), pk=webhook.id)
        self.assertEqual(response.status_code, 200)
        webhook.refresh_from_db()
        self.assertEqual(webhook.url, 'https://8.8.8.8/hooks/private-token')
        self.assertEqual(webhook.headers, {'Authorization': 'Bearer private-header'})

    def test_test_saved_rule_renders_request_body(self):
        created = self.create_webhook()
        webhook_id = created.data['id']
        test = ApplicationWebhookViewSet.as_view({'post': 'test_webhook'})
        request = self.request('post', self.webhook_path + 'test/', {
            'event': ApplicationEvent.CREDENTIAL_UPDATED,
        })
        with patch(
            'accounts.credential_client.webhook_delivery.send_webhook', return_value=204,
        ) as sender:
            response = test(request, pk=webhook_id)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, {'success': True, 'status_code': 204, 'reason': ''})
        self.assertEqual(sender.call_args.args[3], {'event': ApplicationEvent.CREDENTIAL_UPDATED})
