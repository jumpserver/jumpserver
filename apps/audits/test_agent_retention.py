import uuid
from datetime import timedelta
from unittest.mock import patch

from django.test import TestCase, override_settings
from django.utils import timezone
from oauth2_provider.models import get_application_model

from audits.tasks import clean_expired_agent_sessions, clean_expired_session_period
from orgs.models import Organization
from orgs.utils import tmp_to_org, tmp_to_root_org
from terminal.models import AgentAction, AgentEvent, AgentSession, Session, Terminal
from users.models import User


class AgentAuditRetentionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create(username='agent-retention-user')
        cls.application = get_application_model().objects.create(name='Agent retention client')
        cls.node = Terminal.objects.create(name='agent-retention-node', type='koko')
        cls.org, _ = Organization.objects.get_or_create(
            id=Organization.DEFAULT_ID, defaults={'name': 'Default'},
        )
        cls.other_org = Organization.objects.create(name='Agent retention other')

    def setUp(self):
        self.enterContext(tmp_to_root_org())
        self.cutoff = timezone.now() - timedelta(days=30)
        self.old = self.cutoff - timedelta(days=1)

    def graph(self, org=None):
        with tmp_to_org(org or self.org):
            session = AgentSession.objects.create(
                user=self.user, application=self.application, terminal=self.node,
                idempotency_key=uuid.uuid4().hex, request_hash='0' * 64,
                resource='https://jumpserver.example/koko/mcp',
                date_created=self.old, date_expires=self.old, date_closed=self.old,
            )
            action = AgentAction.objects.create(
                session=session, user=self.user, application=self.application,
                kind='execute_command', idempotency_key=uuid.uuid4().hex, request_hash='0' * 64,
                status='succeeded', date_created=self.old, date_started=self.old, date_finished=self.old,
            )
            event = AgentEvent.objects.create(
                event_id=uuid.uuid4(), action=action, sequence=1, state='succeeded',
                payload={'exit_code': 0}, payload_hash='0' * 64, date_received=self.old,
            )
        return session, action, event

    def terminal_session(self, finished, started=None):
        with tmp_to_org(self.org):
            return Session.objects.create(
                terminal=self.node, user=str(self.user), user_id=str(self.user.pk),
                is_finished=finished, date_start=started or timezone.now(),
            )

    def test_cleanup_batches_old_graphs_across_organizations_and_reclaims_abandoned_sessions(self):
        self.graph()
        session, action, _ = self.graph(self.other_org)
        AgentSession.objects.filter(pk=session.pk).update(date_closed=None)
        AgentAction.objects.filter(pk=action.pk).update(status='dispatching', date_finished=None)
        _, action, event = self.graph()
        event.delete()
        action.delete()

        clean_expired_agent_sessions(self.cutoff, batch_size=1)

        self.assertFalse(AgentSession.objects.exists())
        self.assertFalse(AgentAction.objects.exists())
        self.assertFalse(AgentEvent.objects.exists())
        self.assertTrue(Terminal.objects.filter(pk=self.node.pk).exists())
        self.assertTrue(get_application_model().objects.filter(pk=self.application.pk).exists())

    def test_cleanup_preserves_active_connections_and_recent_evidence(self):
        expected = set()
        for state in ('live', 'native', 'interactive', 'closed', 'created', 'started', 'finished', 'event'):
            session, action, event = self.graph()
            expected.add(session.pk)
            recent = self.cutoff
            if state == 'live':
                AgentSession.objects.filter(pk=session.pk).update(date_closed=None, date_expires=timezone.now())
            elif state == 'native':
                AgentSession.objects.filter(pk=session.pk).update(terminal_session=self.terminal_session(False))
            elif state == 'interactive':
                AgentAction.objects.filter(pk=action.pk).update(interactive_session=self.terminal_session(False))
            elif state == 'closed':
                AgentSession.objects.filter(pk=session.pk).update(date_closed=recent)
            elif state == 'event':
                AgentEvent.objects.filter(pk=event.pk).update(date_received=recent)
            else:
                AgentAction.objects.filter(pk=action.pk).update(**{'date_' + state: recent})

        clean_expired_agent_sessions(self.cutoff, batch_size=1)

        self.assertEqual(set(AgentSession.objects.values_list('pk', flat=True)), expected)
        self.assertEqual(AgentAction.objects.count(), len(expected))
        self.assertEqual(AgentEvent.objects.count(), len(expected))

    def test_daily_session_cleanup_uses_existing_retention_setting(self):
        old, _, _ = self.graph()
        old_terminal = self.terminal_session(True, started=self.old)
        AgentSession.objects.filter(pk=old.pk).update(terminal_session=old_terminal)
        current = self.terminal_session(True)
        self.enterContext(patch('audits.tasks.delete_expired_commands_by_day'))
        self.enterContext(patch('audits.tasks.remove_files_by_days'))
        self.enterContext(patch('audits.tasks.find_and_delete_empty_dirs'))

        with override_settings(TERMINAL_SESSION_KEEP_DURATION=60):
            clean_expired_session_period()
        self.assertTrue(AgentSession.objects.filter(pk=old.pk).exists())
        self.assertTrue(Session.objects.filter(pk=old_terminal.pk).exists())
        with override_settings(TERMINAL_SESSION_KEEP_DURATION=30):
            clean_expired_session_period()
        self.assertFalse(AgentSession.objects.exists())
        self.assertFalse(AgentEvent.objects.exists())
        self.assertFalse(Session.objects.filter(pk=old_terminal.pk).exists())
        self.assertTrue(Session.objects.filter(pk=current.pk).exists())

    def test_cleanup_failure_keeps_complete_evidence(self):
        session, action, event = self.graph()
        with patch.object(AgentSession, 'delete', side_effect=RuntimeError('Cleanup failed')):
            with self.assertRaises(RuntimeError):
                clean_expired_agent_sessions(self.cutoff)
        self.assertTrue(AgentSession.objects.filter(pk=session.pk).exists())
        self.assertTrue(AgentAction.objects.filter(pk=action.pk).exists())
        self.assertTrue(AgentEvent.objects.filter(pk=event.pk).exists())
