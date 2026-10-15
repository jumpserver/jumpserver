from importlib import import_module
from unittest.mock import patch

from django.apps import apps
from django.db import connection
from django.test import TestCase
from django.utils import timezone

from orgs.utils import tmp_to_root_org
from orgs.models import Organization
from terminal.models import Session, SessionSharing, SessionJoinRecord
from terminal.serializers.sharing import SessionSharingSerializer, SessionJoinRecordSerializer
from tickets.const import StepState
from tickets.serializers.super_ticket import SuperTicketSerializer
from tickets.models import Ticket, TicketStep, TicketAssignee
from users.models import User


class DeletedUserHistoryTests(TestCase):
    def setUp(self):
        self.org_context = tmp_to_root_org()
        self.org_context.__enter__()
        self.addCleanup(self.org_context.__exit__, None, None, None)
        activity = patch('terminal.signal_handlers.session_sharing.UserCreateShareLink')
        activity.start()
        self.addCleanup(activity.stop)
        self.owner = User(username='history-owner', name='Owner', email='owner@example.test')
        self.joiner = User(username='history-joiner', name='Joiner', email='joiner@example.test')
        User.objects.bulk_create([self.owner, self.joiner])
        self.owner_id = self.owner.pk
        self.joiner_id = self.joiner.pk
        self.session = Session.objects.create(
            user=str(self.owner), user_id=str(self.owner.pk), date_start=timezone.now(), org_id=Organization.DEFAULT_ID,
        )
        self.sharing = SessionSharing.objects.create(
            session=self.session, creator=self.owner, verify_code='1234', expired_time=30, org_id=Organization.DEFAULT_ID,
        )
        self.record = SessionJoinRecord.objects.create(
            session=self.session, sharing=self.sharing, joiner=self.joiner,
            verify_code='1234', remote_addr='127.0.0.1', org_id=Organization.DEFAULT_ID,
        )
        self.ticket = Ticket.objects.create(title='Historical approval')
        self.step = TicketStep.objects.create(ticket=self.ticket, state=StepState.approved)
        self.assignee = TicketAssignee(step=self.step, assignee=self.owner, state=StepState.approved)
        TicketAssignee.objects.bulk_create([self.assignee])

    def test_bulk_user_deletion_retains_history_and_disables_share(self):
        self.assertTrue(self.record.can_join()[0])
        User.objects.filter(pk=self.owner_id).delete()
        self.assignee.refresh_from_db()
        self.sharing.refresh_from_db()
        self.record.refresh_from_db()
        self.assertIsNone(self.assignee.assignee_id)
        self.assertEqual(self.assignee.assignee_display, 'Owner(history-owner)')
        self.assertIsNone(self.sharing.creator_id)
        self.assertFalse(self.sharing.is_active)
        self.assertEqual(self.record.joiner_id, self.joiner_id)
        self.assertFalse(self.record.can_join()[0])
        self.sharing.is_active = True
        self.assertFalse(self.sharing.can_join(self.joiner)[0])
        process = self.ticket.process_map[0]
        self.assertIsNone(process['processor'])
        self.assertEqual(process['processor_display'], 'Owner(history-owner)')
        self.assertEqual(self.ticket.current_assignees, [])
        self.assertEqual(SuperTicketSerializer.get_processor(self.ticket), 'Owner(history-owner)')
        self.assertIn('Owner(history-owner)', str(self.assignee))

    def test_joiner_deletion_retains_record_and_serialization(self):
        self.joiner.delete()
        self.record.refresh_from_db()
        self.assertIsNone(self.record.joiner_id)
        self.assertFalse(self.record.can_join()[0])
        self.assertEqual(SessionJoinRecordSerializer(self.record).data['joiner_display'], 'Joiner(history-joiner)')

    def test_share_deletion_retains_join_record(self):
        self.sharing.delete()
        self.record.refresh_from_db()
        self.assertIsNone(self.record.sharing_id)
        self.assertFalse(self.record.can_join()[0])
        self.assertEqual(self.record.action_permission, '')
        self.assertEqual(SessionJoinRecordSerializer(self.record).data['joiner_display'], 'Joiner(history-joiner)')

    def test_snapshots_survive_renaming_and_subsequent_saves(self):
        User.objects.filter(pk__in=[self.owner_id, self.joiner_id]).update(name='Renamed')
        for obj, field, expected in [
            (self.sharing, 'creator_display', 'Owner(history-owner)'),
            (self.record, 'joiner_display', 'Joiner(history-joiner)'),
            (self.assignee, 'assignee_display', 'Owner(history-owner)'),
        ]:
            obj.refresh_from_db()
            obj.save()
            obj.refresh_from_db()
            self.assertEqual(getattr(obj, field), expected)

    def test_direct_assignee_creation_and_readonly_api_fields(self):
        item = TicketAssignee.objects.create(step=self.step, assignee=self.joiner)
        self.assertEqual(item.assignee_display, 'Joiner(history-joiner)')
        for serializer, prefix in [(SessionSharingSerializer(), 'creator'), (SessionJoinRecordSerializer(), 'joiner')]:
            self.assertTrue(serializer.fields[f'{prefix}_display'].read_only)

    def test_backfill_existing_rows(self):
        for model, prefix in [(TicketAssignee, 'assignee'), (SessionSharing, 'creator'), (SessionJoinRecord, 'joiner')]:
            model.objects.update(**{f'{prefix}_display': ''})
        with connection.schema_editor(atomic=False) as editor:
            for module in [
                'tickets.migrations.0009_ticketassignee_assignee_display_and_more',
                'terminal.migrations.0015_sessionjoinrecord_joiner_display_and_more',
            ]:
                import_module(module).backfill_identity_snapshots(apps, editor)
        self.assignee.refresh_from_db()
        self.sharing.refresh_from_db()
        self.record.refresh_from_db()
        self.assertEqual(self.assignee.assignee_display, 'Owner(history-owner)')
        self.assertEqual(self.sharing.creator_display, 'Owner(history-owner)')
        self.assertEqual(self.record.joiner_display, 'Joiner(history-joiner)')
