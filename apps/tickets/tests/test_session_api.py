from types import SimpleNamespace
from unittest.mock import Mock, patch
from uuid import uuid4

from django.test import SimpleTestCase, TestCase
from rest_framework.test import APIRequestFactory, force_authenticate

from orgs.models import Organization
from orgs.utils import get_current_org_id, set_current_org, tmp_to_org
from terminal.models import Session, Terminal
from tickets.api.relation import TicketSessionApi, TicketSessionListApi
from tickets.models import Ticket, TicketSession
from users.models import User


class TicketSessionAPITests(SimpleTestCase):
    def setUp(self):
        self.original_org_id = get_current_org_id()
        self.request_org = Organization(id=str(uuid4()), name='Request org')
        self.session_org = Organization(id=str(uuid4()), name='Session org')
        orgs = {
            org.id: org for org in (
                self.request_org, self.session_org, Organization.root(),
            )
        }
        org_lookup = patch.object(
            Organization, 'get_instance',
            side_effect=lambda oid, default=None: orgs.get(str(oid), default),
        )
        org_lookup.start()
        self.addCleanup(org_lookup.stop)
        self.addCleanup(
            set_current_org, Organization(id=self.original_org_id or Organization.DEFAULT_ID)
        )
        set_current_org(self.request_org)

        self.ticket_id = uuid4()
        self.session = SimpleNamespace(id=uuid4(), org=self.session_org)
        self.user = SimpleNamespace(
            id=uuid4(), is_authenticated=True, is_anonymous=False,
            has_perms=Mock(return_value=True),
            get_all_permissions=Mock(return_value=[]),
            perms=['tickets.view_ticket'],
        )
        self.relation = self.start_patch('TicketSession.objects.filter')
        self.relation.return_value.first.return_value = SimpleNamespace(session=self.session)
        self.related_tickets = self.start_patch('Ticket.get_user_related_tickets')
        self.related_tickets.return_value.filter.return_value.exists.return_value = False
        self.serializer = self.start_patch('SessionSerializer')
        self.serializer.return_value.data = {'id': str(self.session.id), 'account': 'root'}

    def start_patch(self, name):
        patcher = patch('tickets.api.relation.' + name)
        value = patcher.start()
        self.addCleanup(patcher.stop)
        return value

    def request(self, authenticated=True):
        path = '/api/v1/tickets/tickets/{}/session/'.format(self.ticket_id)
        request = APIRequestFactory().get(path)
        if authenticated:
            force_authenticate(request, user=self.user)
        view = TicketSessionApi.as_view(throttle_classes=[], authentication_classes=[])
        response = view(request, ticket_id=self.ticket_id)
        self.assertEqual(get_current_org_id(), self.request_org.id)
        return response

    def assert_denied(self, response, status=404):
        self.assertEqual(response.status_code, status)
        self.serializer.assert_not_called()

    def test_unrelated_user_cannot_read_session_in_same_or_other_org(self):
        for org in (self.request_org, self.session_org):
            with self.subTest(org=org.name):
                self.session.org = org
                self.assert_denied(self.request())

    def test_ticket_related_user_can_read_session_across_orgs(self):
        self.related_tickets.return_value.filter.return_value.exists.return_value = True

        response = self.request()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, self.serializer.return_value.data)
        self.related_tickets.assert_called_once_with(self.user)
        self.related_tickets.return_value.filter.assert_called_once_with(id=self.ticket_id)
        self.user.get_all_permissions.assert_not_called()

    def test_auditor_can_read_session_in_authorized_org(self):
        def permissions():
            if get_current_org_id() == self.session_org.id:
                return ['terminal.view_session']
            return []

        self.user.get_all_permissions.side_effect = permissions

        self.assertEqual(self.request().status_code, 200)
        self.user.get_all_permissions.assert_called_once_with()

    def test_request_org_audit_permission_does_not_grant_access_to_other_org(self):
        self.user.perms.append('terminal.view_session')
        self.user.get_all_permissions.side_effect = lambda: (
            self.user.perms if get_current_org_id() == self.request_org.id else []
        )

        self.assert_denied(self.request())

    def test_system_auditor_can_read_sessions_in_multiple_orgs(self):
        self.user.get_all_permissions.return_value = ['terminal.view_session']
        for org in (self.request_org, self.session_org):
            with self.subTest(org=org.name):
                self.session.org = org
                self.assertEqual(self.request().status_code, 200)

    def test_missing_session_org_does_not_fall_back_to_root_permissions(self):
        self.session.org = None
        self.user.get_all_permissions.return_value = ['terminal.view_session']

        self.assert_denied(self.request())
        self.user.get_all_permissions.assert_not_called()

    def test_missing_relation_returns_404(self):
        self.relation.return_value.first.return_value = None

        self.assert_denied(self.request())
        self.related_tickets.assert_not_called()

    def test_ticket_permission_is_still_required(self):
        self.user.has_perms.return_value = False

        self.assert_denied(self.request(), status=403)
        self.user.has_perms.assert_called_once_with(['tickets.view_ticket'])
        self.relation.assert_not_called()

    def test_anonymous_user_cannot_read_session(self):
        self.assert_denied(self.request(authenticated=False), status=403)
        self.relation.assert_not_called()


class TicketSessionListTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner, cls.auditor = [
            User(username=name, name=name, email=f'{name}@example.test')
            for name in ('ticket-owner', 'session-auditor')
        ]
        User.objects.bulk_create([cls.owner, cls.auditor])
        cls.org = Organization.default()
        cls.other = Organization(id=str(uuid4()), name='Other session organization')
        Organization.objects.bulk_create([cls.other])
        cls.ticket = Ticket.objects.create(title='Asset review', type='login_asset_confirm',
                                           applicant=cls.owner, org_id=cls.org.id)

    def request(self, user):
        with tmp_to_org(self.other), patch.object(user, 'has_perms', return_value=True):
            request = APIRequestFactory().get('/')
            force_authenticate(request, user=user)
            return TicketSessionListApi.as_view(throttle_classes=[])(request, ticket_id=self.ticket.pk)

    def add_session(self, org, **kwargs):
        with tmp_to_org(org):
            session = Session.objects.create(**kwargs)
        TicketSession.objects.create(ticket=self.ticket, session=session)
        return session

    def test_related_user_sees_unique_sessions_online_first_across_request_orgs(self):
        self.assertEqual(self.request(self.owner).data, [])
        ended = self.add_session(self.org, is_finished=True)
        live = self.add_session(self.org, terminal=Terminal.objects.create(name='Test KoKo', type='koko'))
        TicketSession.objects.create(ticket=self.ticket, session=live)
        response = self.request(self.owner)
        self.assertEqual(response.status_code, 200)
        self.assertEqual([row['id'] for row in response.data], [str(live.pk), str(ended.pk)])
        self.assertEqual(response.data[0]['org_id'], str(self.org.id))
        self.assertEqual(response.data[0]['terminal_type'], 'koko')
        self.assertTrue(response.data[0]['can_join'])
        self.assertFalse(response.data[1]['can_join'])

    def test_auditor_only_sees_sessions_in_authorized_organizations(self):
        allowed = self.add_session(self.org)
        self.add_session(self.other)
        with patch.object(self.auditor, 'get_all_permissions', side_effect=lambda: (
                ['terminal.view_session'] if get_current_org_id() == self.org.id else [])):
            response = self.request(self.auditor)
        self.assertEqual(response.status_code, 200)
        self.assertEqual([row['id'] for row in response.data], [str(allowed.pk)])
        self.assertFalse(response.data[0]['can_join'])
        with patch.object(self.auditor, 'get_all_permissions', return_value=[]):
            self.assertEqual(self.request(self.auditor).status_code, 404)
