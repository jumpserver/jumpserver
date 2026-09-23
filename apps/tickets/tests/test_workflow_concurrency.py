from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from unittest.mock import patch

from django.db import close_old_connections, connection, connections
from django.test import TransactionTestCase, skipUnlessDBFeature

from orgs.utils import tmp_to_org, tmp_to_root_org
from tickets.models import ApprovalTask, Workflow, WorkflowInstance
from tickets.tests import test_workflow
from tickets.workflow.engine import WorkflowEngine
from tickets.workflow.errors import WorkflowConflict
from tickets.workflow.publication import publish_workflow


@skipUnlessDBFeature('has_select_for_update')
class WorkflowConcurrencyTests(TransactionTestCase):
    """Use separate database connections to exercise the instance/publication locks."""

    def setUp(self):
        delivery = patch('tickets.workflow.business.deliver_event')
        delivery.start()
        self.addCleanup(delivery.stop)
        test_workflow.WorkflowTests.setUpTestData.__func__(type(self))
        with tmp_to_org(self.org):
            self.engine = WorkflowEngine()
            self.workflow = test_workflow.WorkflowTests.create_workflow(self, strategy='all')
            self.instance = test_workflow.WorkflowTests.start(self, self.workflow)

    def race(self, operations):
        barrier = Barrier(len(operations))

        def run(operation):
            close_old_connections()
            try:
                if connection.vendor == 'postgresql':
                    with connection.cursor() as cursor:
                        cursor.execute("SET lock_timeout = '5s'")
                        cursor.execute("SET statement_timeout = '10s'")
                with tmp_to_org(self.org):
                    barrier.wait(timeout=10)
                    try:
                        return operation()
                    except WorkflowConflict:
                        return 'conflict'
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=len(operations)) as executor:
            futures = [executor.submit(run, operation) for operation in operations]
            return [future.result(timeout=20) for future in futures]

    def test_simultaneous_votes_complete_once(self):
        tasks = list(ApprovalTask.objects.filter(node_instance__instance=self.instance).select_related('assignee'))
        results = self.race([
            lambda task=task: WorkflowEngine().approve(task, task.assignee).state for task in tasks
        ])
        self.assertCountEqual(results, ['running', 'approved'])
        with tmp_to_root_org():
            self.assertEqual(WorkflowInstance.objects.get(pk=self.instance.pk).state, 'approved')
        self.assertEqual(self.instance.events.filter(type='workflow.completed').count(), 1)

    def test_simultaneous_duplicate_vote_is_counted_once(self):
        task = ApprovalTask.objects.select_related('assignee').filter(node_instance__instance=self.instance).first()
        operation = lambda: WorkflowEngine().approve(task, task.assignee).state
        self.assertCountEqual(self.race([operation, operation]), ['running', 'conflict'])
        self.assertEqual(self.instance.events.filter(type='approval.approved').count(), 1)

    def test_simultaneous_publish_rejects_stale_editor(self):
        operation = lambda: publish_workflow(
            self.workflow, test_workflow.approval_definition([self.alice]), expected_version=1,
        ).number
        self.assertCountEqual(self.race([operation, operation]), [2, 'conflict'])
        with tmp_to_root_org():
            self.assertEqual(Workflow.objects.get(pk=self.workflow.pk).active_version.number, 2)
        self.assertEqual(self.workflow.versions.count(), 2)
