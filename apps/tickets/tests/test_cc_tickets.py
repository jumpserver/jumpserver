from django.db import transaction
from django.test import TestCase
from rest_framework.permissions import IsAuthenticated
from rest_framework.test import force_authenticate

from tickets.api.ticket import TicketViewSet
from tickets.models import Ticket
from tickets.tests import test_workflow as fixtures


class CcTicketListTests(TestCase):
    setUpTestData = classmethod(fixtures.WorkflowTests.setUpTestData.__func__)
    setUp = fixtures.WorkflowTests.setUp
    create_workflow = fixtures.WorkflowTests.create_workflow
    start = fixtures.WorkflowTests.start
    task = fixtures.WorkflowTests.task

    def list_tickets(self, user, **filters):
        request = self.factory.get('/api/v1/tickets/tickets/', filters)
        force_authenticate(request, user)
        with transaction.atomic():
            return TicketViewSet.as_view(
                {'get': 'list'}, permission_classes=[IsAuthenticated],
            )(request)

    def listed_ids(self, user, **filters):
        response = self.list_tickets(user, **filters)
        self.assertEqual(response.status_code, 200, response.data)
        rows = response.data.get('results', []) if isinstance(response.data, dict) else response.data
        return [str(row['id']) for row in rows]

    def test_cc_filter_excludes_other_relationships_and_keeps_finished_tickets(self):
        copied = Ticket.objects.create(title='Copied request', applicant=self.applicant, org_id=self.org.id)
        copied.cc_users.add(self.carol, self.bob)
        finished = Ticket.objects.create(title='Finished copy', applicant=self.applicant,
                                         org_id=self.org.id, state='approved', status='closed')
        finished.cc_users.add(self.carol)
        own = Ticket.objects.create(title='My own request', applicant=self.carol, org_id=self.org.id)
        own.cc_users.add(self.bob)
        other = Ticket.objects.create(title='Someone else received a copy', applicant=self.applicant,
                                      org_id=self.org.id)
        other.cc_users.add(self.bob)

        self.assertCountEqual(self.listed_ids(self.carol, cc_users__id=str(self.carol.pk)),
                              [str(copied.pk), str(finished.pk)])
        self.assertEqual(self.listed_ids(self.carol, cc_users__id=str(self.carol.pk), state='approved'),
                         [str(finished.pk)])
        self.assertEqual(self.listed_ids(self.outsider, cc_users__id=str(self.carol.pk)), [])
        self.assertEqual(self.list_tickets(self.carol, cc_users__id='not-a-uuid').status_code, 400)

    def test_ticket_appears_only_after_cc_node_runs_and_is_not_an_approval_task(self):
        definition = fixtures.approval_definition([self.alice], levels=2)
        definition['nodes'].insert(2, {'id': 'notify', 'type': 'cc', 'config': {
            'users': [str(self.carol.pk)],
        }})
        definition['edges'] = [['start', 'approval_0'], ['approval_0', 'notify'],
                               ['notify', 'approval_1'], ['approval_1', 'end']]
        instance = self.start(self.create_workflow(definition))
        filters = {'cc_users__id': str(self.carol.pk)}
        self.assertEqual(self.listed_ids(self.carol, **filters), [])

        self.engine.approve(self.task(instance, self.alice), self.alice)
        self.assertEqual(self.listed_ids(self.carol, **filters), [str(instance.ticket_id)])
        self.assertEqual(self.listed_ids(self.carol, assignees__id=str(self.carol.pk), state='pending'), [])
        self.assertEqual(self.listed_ids(self.carol, processed_by=str(self.carol.pk)), [])
        self.assertEqual(self.listed_ids(self.alice, assignees__id=str(self.alice.pk), state='pending'),
                         [str(instance.ticket_id)])

        self.engine.reject(self.task(instance, self.alice), self.alice)
        self.assertEqual(self.listed_ids(self.carol, **filters), [str(instance.ticket_id)])
