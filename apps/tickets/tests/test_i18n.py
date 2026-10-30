from django.test import SimpleTestCase
from django.utils.translation import gettext, override

from ops.models import CeleryTask
from ops.celery import app
from tickets.models import Workflow, WorkflowVersion, WorkflowNode
from tickets.serializers.workflow import WorkflowSerializer
from tickets.workflow.definition import validate_definition
from tickets.workflow.errors import WorkflowConfigurationError, WorkflowConflict


class TicketTranslationTests(SimpleTestCase):
    def test_generated_workflow_name_is_localized_without_changing_its_identity(self):
        workflow = Workflow(name='Apply for asset', type='apply_asset', created_by='System')
        with override('zh'):
            self.assertEqual(workflow.display_name, '申请资产')
            self.assertEqual(str(workflow), '申请资产')
            data = WorkflowSerializer(workflow).data
            self.assertEqual(data['display_name'], '申请资产')
            self.assertEqual(data['name'], 'Apply for asset')
        with override('en'):
            self.assertEqual(workflow.display_name, gettext('Apply for asset'))
        self.assertEqual(workflow.name, 'Apply for asset')

    def test_custom_names_are_preserved_even_when_they_match_an_english_default(self):
        workflow = Workflow(name='Apply for asset', type='apply_asset', created_by='Administrator')
        with override('zh'):
            self.assertEqual(workflow.display_name, 'Apply for asset')
            workflow.created_by = 'System'
            workflow.name = 'Operations approval'
            self.assertEqual(workflow.display_name, 'Operations approval')

    def test_generated_node_names_remain_localized_when_a_version_is_copied(self):
        workflow = Workflow(created_by='Legacy ticket import', is_system=True)
        version = WorkflowVersion(workflow=workflow, number=1)
        with override('zh'):
            self.assertEqual(workflow.display_name, '历史工单审批')
            for kind, name, expected in [('start', 'start', '开始'), ('end', 'end', '结束'),
                                         ('approval', 'Approval 2', '第 2 级审批')]:
                node = WorkflowNode(version=version, type=kind, name=name)
                self.assertEqual(workflow.node_display_name(node), expected)
                self.assertEqual(node.name, name)
            for name in ['Operations approval', '2']:
                node.name = name
                self.assertEqual(workflow.node_display_name(node), name)
            node.name = 'Approval 2'
            version.number = 2
            self.assertEqual(workflow.node_display_name(node), '第 2 级审批')
            version.number = 1
            workflow.created_by = 'Administrator'
            self.assertEqual(workflow.node_display_name(node), 'Approval 2')

    def test_validation_errors_follow_the_request_language(self):
        for language, expected in [('zh', '审批流程必须包含节点和连线。'),
                                   ('en', 'A workflow requires nodes and edges.')]:
            with override(language):
                with self.assertRaises(WorkflowConfigurationError) as error:
                    validate_definition({})
                self.assertEqual(str(error.exception.detail[0]), expected)
        with override('zh'):
            self.assertEqual(str(WorkflowConflict().detail), '流程状态已变更，请刷新后重试。')

    def test_system_task_metadata_is_translated_without_changing_task_identifiers(self):
        names = ['expire_workflow_approvals', 'execute_ticket_change_secret', 'dispatch_ticket_change_secrets',
                 'execute_ticket_file_transfer', 'maintain_ticket_file_transfers', 'cleanup_ticket_transfer_files']
        for name in names:
            identifier = f'tickets.tasks.{name}'
            task = app.tasks.get(identifier)
            self.assertIsNotNone(task, 'Ticket task metadata must be available in the web process.')
            self.assertEqual(task.name, identifier)
            with override('en'):
                english = str(task.verbose_name)
            with override('zh'):
                meta = CeleryTask(name=identifier).meta
                self.assertNotEqual(str(meta['comment']), english)
                self.assertIn('工单', str(meta['comment']))
                self.assertTrue(str(meta['description']))
