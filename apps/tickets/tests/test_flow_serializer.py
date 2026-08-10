from unittest.mock import Mock, patch

from django.test import SimpleTestCase

from tickets.serializers.flow import TicketFlowApproveSerializer


class TicketFlowApproveSerializerTestCase(SimpleTestCase):
    def setUp(self):
        self.users = {
            'type': 'attrs',
            'attrs': [
                {
                    'name': 'username',
                    'match': 'exact',
                    'value': 'no-matching-approver',
                }
            ],
        }

    @patch('tickets.serializers.flow.get_current_org_id')
    @patch('tickets.serializers.flow.ApprovalRule.get_assignees')
    def test_rejects_rule_without_matching_approvers(
            self, get_assignees, get_current_org_id
    ):
        queryset = Mock()
        queryset.exists.return_value = False
        get_assignees.return_value = queryset

        serializer = TicketFlowApproveSerializer(data={'users': self.users})

        self.assertFalse(serializer.is_valid())
        self.assertIn('users', serializer.errors)
        self.assertIn('No approvers matched', str(serializer.errors['users']))
        get_assignees.assert_called_once_with(org_id=get_current_org_id.return_value)

    @patch('tickets.serializers.flow.get_current_org_id')
    @patch('tickets.serializers.flow.ApprovalRule.get_assignees')
    def test_accepts_rule_with_matching_approvers(
            self, get_assignees, get_current_org_id
    ):
        queryset = Mock()
        queryset.exists.return_value = True
        get_assignees.return_value = queryset

        serializer = TicketFlowApproveSerializer(data={'users': self.users})

        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(serializer.validated_data['users'], self.users)
        get_assignees.assert_called_once_with(org_id=get_current_org_id.return_value)
