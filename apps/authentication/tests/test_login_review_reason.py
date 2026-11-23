import time
from unittest.mock import patch
from uuid import uuid4

from django.conf import settings
from django.contrib.auth import SESSION_KEY
from django.test import Client, TestCase
from django.urls import reverse

from acls.models import LoginACL
from authentication.mixins import AuthMixin
from authentication.models import SSOToken
from orgs.utils import tmp_to_org, tmp_to_root_org
from tickets.models import Ticket, WorkflowInstance
from tickets.plugins.login_confirm.plugin import Plugin
from tickets.tests import test_workflow as fixtures
from tickets.workflow.engine import WorkflowEngine


class LoginReviewReasonTests(TestCase):
    setUpTestData = classmethod(fixtures.WorkflowTests.setUpTestData.__func__)

    def setUp(self):
        scope = tmp_to_root_org()
        scope.__enter__()
        self.addCleanup(scope.__exit__, None, None, None)
        self.acl = LoginACL.objects.create(
            name='Optional login reason', action='review',
            users={'type': 'ids', 'ids': [str(self.applicant.pk)]},
        )
        self.acl.reviewers.add(self.alice)
        self.guard = reverse('authentication:login-guard')
        self.wait = reverse('authentication:login-wait-confirm')
        self.authenticate()

    def authenticate(self):
        session = self.client.session
        session.update({
            'auth_password': 1, 'user_id': str(self.applicant.pk),
            'auth_password_expired_at': time.time() + 600,
            'auth_backend': settings.AUTH_BACKEND_MODEL, 'auth_confirm_required': '1',
            'auth_acl_id': str(self.acl.pk),
        })
        session.save()

    def test_reason_is_optional_and_only_submitting_opens_a_ticket(self):
        for reason in ('', '  ', '排查生产告警\n核对昨晚的变更', 'x' * 4096):
            with self.subTest(reason=reason[:30]):
                self.client = Client()
                self.authenticate()
                count = Ticket.objects.count()
                self.assertRedirects(self.client.get(self.guard), self.wait, fetch_redirect_response=False)
                reserved = self.client.session['auth_ticket_id']
                page = self.client.get(self.wait)
                self.assertEqual(page.status_code, 200)
                self.assertIsNone(page.context['ticket'])
                self.assertFalse(page.context['form'].fields['reason'].required)
                self.assertNotContains(page, 'class="btn btn-primary btn-sm block btn-copy"')
                self.assertEqual(Ticket.objects.count(), count)
                self.assertRedirects(self.client.post(self.wait, {'reason': reason}), self.guard,
                                     fetch_redirect_response=False)
                ticket = Ticket.objects.get(pk=reserved)
                self.assertEqual(ticket.comment, reason.strip())
                self.assertEqual(ticket.state, 'pending')
                self.assertEqual(Plugin().request_items(ticket)[-1]['value'], reason.strip() or '-')
                self.assertNotIn(SESSION_KEY, self.client.session)
                self.client.post(self.wait, {'reason': 'Must not replace the submitted reason'})
                ticket.refresh_from_db()
                self.assertEqual(ticket.comment, reason.strip())
                self.assertEqual(Ticket.objects.count(), count + 1)
                self.assertContains(self.client.get(self.wait), 'btn-copy')
                self.assertNotContains(self.client.get(self.wait), 'name="reason"')

    def test_stale_submission_reuses_the_reserved_ticket_and_workflow(self):
        ticket_id = uuid4()
        first = self.acl.create_confirm_ticket(None, self.applicant, reason='First', ticket_id=ticket_id)
        with tmp_to_org(self.org):
            repeated = self.acl.create_confirm_ticket(None, self.applicant, reason='Second', ticket_id=ticket_id)
        self.assertEqual(first.pk, repeated.pk)
        self.assertEqual(repeated.comment, 'First')
        self.assertEqual(WorkflowInstance.objects.filter(ticket=first).count(), 1)

    def test_invalid_reason_preserves_input_without_creating_a_ticket(self):
        self.client.get(self.guard)
        for reason in ('x' * 4097, '\x00'):
            response = self.client.post(self.wait, {'reason': reason})
            self.assertEqual(response.status_code, 200)
            self.assertIn('reason', response.context['form'].errors)
            self.assertFalse(Ticket.objects.exists())

    def test_submission_requires_current_authentication_and_csrf(self):
        self.client.get(self.guard)
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.cookies = self.client.cookies
        with patch('jumpserver.middleware.IGNORE_CSRF_CHECK', False):
            response = csrf_client.post(self.wait, {'reason': 'Forged'})
        self.assertEqual(response.status_code, 302)
        self.assertIn('csrf_failure=1', response.url)
        self.assertFalse(Ticket.objects.exists())
        session = self.client.session
        session['auth_password_expired_at'] = time.time() - 1
        session.save()
        self.assertRedirects(self.client.post(self.wait, {'reason': 'Expired'}),
                             reverse('authentication:login'), fetch_redirect_response=False)
        self.assertFalse(Ticket.objects.exists())

    def test_approval_completes_login_and_preserves_next_url(self):
        self.client.get(self.guard)
        self.assertRedirects(self.client.post(self.wait + '?next=%2Fui%2F', {'reason': 'Maintenance'}),
                             self.guard + '?next=%2Fui%2F', fetch_redirect_response=False)
        ticket = Ticket.objects.get(pk=self.client.session['auth_ticket_id'])
        self.assertRedirects(self.client.get(self.guard), self.wait, fetch_redirect_response=False)
        task = ticket.approval_tasks.get(state='pending')
        WorkflowEngine().approve(task, self.alice)
        self.assertEqual(self.client.get(reverse('api-auth:login-confirm-ticket-status')).json(), {'msg': 'ok'})
        with patch.object(AuthMixin, 'send_auth_signal'):
            self.client.get(self.guard)
        self.assertIn(SESSION_KEY, self.client.session)

    def test_browser_sso_also_waits_for_reason_submission(self):
        self.client = Client()
        token = SSOToken.objects.create(user=self.applicant)
        response = self.client.get(reverse('api-auth:sso-login'), {'authkey': str(token.authkey), 'next': '/ui/'})
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith(self.guard))
        self.assertFalse(Ticket.objects.exists())
        self.assertNotIn(SESSION_KEY, self.client.session)
        self.assertContains(self.client.get(self.wait), 'name="reason"')
        self.client.post(self.wait, {'reason': 'SSO maintenance'})
        self.assertEqual(Ticket.objects.get().comment, 'SSO maintenance')
        token.refresh_from_db()
        self.assertTrue(token.expired)

    def test_api_callers_can_still_create_review_without_a_reason(self):
        from authentication import errors
        from django.test import RequestFactory

        view = AuthMixin()
        view.request = RequestFactory().post('/api/v1/authentication/auth/')
        view.request.session = self.client.session
        with self.assertRaises(errors.LoginConfirmWaitError):
            view.check_user_login_confirm_if_need(self.applicant)
        self.assertEqual(Ticket.objects.get().comment, '')
