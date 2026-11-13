import uuid

from django.db import transaction
from django.test import TestCase
from django.urls import resolve
from rest_framework.request import Request
from rest_framework.test import APIRequestFactory, force_authenticate

from audits.api import FTPLogViewSet
from audits.ftp import ftp_log_sources
from audits.models import FTPLog
from audits.serializers import FTPLogSerializer
from orgs.models import Organization
from orgs.utils import tmp_to_org
from rbac.models import Permission, Role
from terminal.api.session.session import SessionFilterSet
from terminal.models import Session
from users.models import User


class FTPAgentAuditTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.org = Organization.objects.create(name='FTP audit organization')
        cls.other_org = Organization.objects.create(name='FTP other organization')
        cls.user = User.objects.create(username='ftp-auditor')
        cls.ordinary = User.objects.create(username='ftp-ordinary')
        cls.org.add_member(cls.user)
        cls.org.add_member(cls.ordinary)
        role = Role.objects.create(name='FTP auditor', scope='org')
        role.permissions.add(Permission.objects.get(content_type__app_label='audits', codename='view_ftplog'))
        with tmp_to_org(cls.org):
            cls.user.org_roles.add(role)
            cls.sessions = [Session.objects.create(
                user='FTP user', user_id=str(cls.user.pk), asset='FTP asset', account='root',
                account_id='root', protocol='sftp', login_from=source,
            ) for source in ('AG', 'AH', 'WT')]
            cls.logs = [FTPLog.objects.create(
                user='FTP user', asset='FTP asset', account='root', operate='download', filename='/file',
                session=str(session.pk),
            ) for session in cls.sessions]
            malformed = 'a' + cls.sessions[0].pk.hex
            for reference in ('', 'invalid', str(uuid.uuid4()), malformed):
                cls.logs.append(FTPLog.objects.create(
                    user='FTP user', asset='FTP asset', account='root', operate='download',
                    filename='/unknown', session=reference,
                ))
        with tmp_to_org(cls.other_org):
            other = Session.objects.create(user='Other', asset='Other', account='root', login_from='AG')
            cls.foreign_log = FTPLog.objects.create(user='Other', asset='Other', account='root',
                operate='download', filename='/other', session=str(other.pk))
        with tmp_to_org(cls.org):
            cls.logs.append(FTPLog.objects.create(user='FTP user', asset='FTP asset', account='root',
                operate='download', filename='/mismatch', session=str(other.pk)))

    def setUp(self):
        self.enterContext(tmp_to_org(self.org))

    def request(self, params=None, user=None):
        request = APIRequestFactory().get('/api/v1/audits/ftp-logs/', params or {'limit': 20})
        force_authenticate(request, user=user or self.user)
        route = resolve(request.path)
        with transaction.atomic():
            return route.func(request, **route.kwargs)

    def test_sources_use_one_query_per_page_and_preserve_unknown_references(self):
        with self.assertNumQueries(1):
            sources = ftp_log_sources(self.logs)
        with self.assertNumQueries(0):
            data = FTPLogSerializer(self.logs, many=True, context={'ftp_sources': sources}).data
        self.assertEqual([row['login_from']['value'] for row in data], ['AG', 'AH', 'WT', '', '', '', '', ''])
        view = FTPLogViewSet()
        view.action = 'list'
        view.request = Request(APIRequestFactory().get('/api/v1/audits/ftp-logs/'))
        view.get_serializer_context = lambda: {}
        with self.assertNumQueries(1):
            self.assertEqual(len(view.get_serializer(self.logs, many=True).data), len(self.logs))

    def test_filter_precedes_pagination_and_keeps_human_handoff_ordinary(self):
        for category, expected in (('agent', 1), ('user', 2), ('unknown', 5)):
            with self.subTest(category=category):
                response = self.request({'category': category, 'limit': 1})
                self.assertEqual(response.status_code, 200, response.data)
                self.assertEqual(response.data['count'], expected)
                source = response.data['results'][0]['login_from']['value']
                self.assertIn(source, {'agent': ('AG',), 'user': ('AH', 'WT'), 'unknown': ('',)}[category])
        response = self.request({'session': str(self.sessions[0].pk), 'limit': 20})
        self.assertEqual([row['id'] for row in response.data['results']], [str(self.logs[0].pk)])

    def test_audit_permission_and_organization_are_not_expanded(self):
        self.assertEqual(self.request(user=self.ordinary).status_code, 403)
        response = self.request()
        self.assertEqual(response.data['count'], 8)
        self.assertNotIn(str(self.foreign_log.pk), {row['id'] for row in response.data['results']})
        self.assertEqual(self.request({'category': 'invalid'}).status_code, 400)

    def test_reference_formats_and_removed_session_do_not_break_filtering(self):
        self.logs[0].session = self.sessions[0].pk.hex.upper()
        self.logs[0].save(update_fields=['session'])
        self.assertEqual(self.request({'category': 'agent', 'limit': 20}).data['count'], 1)
        self.sessions[0].delete()
        response = self.request({'category': 'unknown', 'limit': 20})
        self.assertEqual(response.data['count'], 6)
        self.assertTrue(FTPLog.objects.filter(pk=self.logs[0].pk).exists())

    def test_normal_session_filter_keeps_handoff_and_all_query_remains_available(self):
        queryset = Session.objects.all()
        filtered = SessionFilterSet({'category': 'user'}, queryset=queryset)
        self.assertTrue(filtered.is_valid(), filtered.errors)
        self.assertEqual(set(filtered.qs.values_list('login_from', flat=True)), {'AH', 'WT'})
        self.assertEqual(queryset.count(), 3)
