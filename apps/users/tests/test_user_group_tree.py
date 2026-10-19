from types import SimpleNamespace
from unittest.mock import MagicMock, Mock, patch
from uuid import UUID

from django.test import SimpleTestCase

from perms.filters import AssetPermissionFilter
from perms.serializers.tree import PermissionTreeMetricsQuerySerializer
from users.serializers.tree import UserGroupTreeQuerySerializer
from users.tree import UserGroupTree


class UserGroupTreeVirtualGroupTests(SimpleTestCase):
    def setUp(self):
        self.org_id = str(UUID(int=1))
        self.tree = UserGroupTree.__new__(UserGroupTree)
        self.tree.org_id = self.org_id
        self.tree.org = SimpleNamespace(
            id=self.org_id, name='Test', is_root=lambda: False
        )
        self.tree.groups = MagicMock()
        self.tree.users = MagicMock()
        self.tree.group_org_names = {}
        self.tree._set_group_org_names = Mock()
        self.tree._ungrouped_users = Mock()
        membership = patch('users.tree.User.groups.through.objects.filter')
        self.memberships = membership.start()
        self.memberships.return_value.values_list.return_value.distinct.return_value = []
        self.addCleanup(membership.stop)

    def test_virtual_group_is_first_and_does_not_consume_real_group_offsets(self):
        groups = [
            SimpleNamespace(id=UUID(int=i + 2), name=f'Group {i}', org_id=self.org_id)
            for i in range(5)
        ]
        self.tree.groups.order_by.return_value = groups
        expected_ids = [f'ungrouped_users:{self.org_id}'] + [
            str(group.id) for group in groups
        ]
        for limit in (1, 2, 4, 100):
            with self.subTest(limit=limit):
                offset = 0
                ids = []
                while True:
                    page = self.tree.children(
                        'organization', self.org_id, limit=limit, offset=offset
                    )
                    ids.extend(node['id'] for node in page['results'])
                    self.assertLessEqual(page['returned_count'], limit)
                    self.assertFalse(any(
                        node['meta']['type'] == 'user' for node in page['results']
                    ))
                    if not page['has_more']:
                        break
                    self.assertGreater(page['next_offset'], offset)
                    offset = page['next_offset']
                self.assertEqual(ids, expected_ids)
        self.tree._ungrouped_users.assert_not_called()

    def test_empty_organization_still_has_a_virtual_group(self):
        self.tree.groups.order_by.return_value = []
        self.assertTrue(self.tree.root()[0]['hasChildren'])
        page = self.tree.children('organization', self.org_id, limit=1)
        self.assertEqual(page['results'][0]['meta']['type'], 'ungrouped_users')
        self.assertFalse(page['has_more'])
        self.tree._ungrouped_users.assert_not_called()

    def test_virtual_group_users_have_their_own_pagination_and_parent(self):
        users = [
            SimpleNamespace(id=UUID(int=i + 20), name=f'User {i}', username=f'u{i}')
            for i in range(3)
        ]
        self.tree._ungrouped_users.return_value.order_by.return_value = users
        first = self.tree.children('ungrouped_users', self.org_id, limit=2)
        last = self.tree.children(
            'ungrouped_users', self.org_id, limit=2, offset=first['next_offset']
        )
        nodes = first['results'] + last['results']
        self.assertEqual(len(nodes), 3)
        self.assertTrue(first['has_more'])
        self.assertFalse(last['has_more'])
        for node, user in zip(nodes, users):
            self.assertEqual(node['pId'], f'ungrouped_users:{self.org_id}')
            self.assertEqual(node['meta']['data']['parent_type'], 'ungrouped_users')
            self.assertEqual(node['meta']['data']['resource_id'], str(user.id))
        self.tree.groups.filter.assert_not_called()

    def test_other_organizations_virtual_group_is_not_accessible(self):
        result = self.tree.children('ungrouped_users', str(UUID(int=2)))
        self.assertEqual(result['results'], [])
        self.tree._ungrouped_users.assert_not_called()

    @patch('users.tree.Subquery', return_value=None)
    def test_search_keeps_ungrouped_users_under_the_virtual_group(self, subquery):
        user = SimpleNamespace(
            id=UUID(int=20), name='Match', username='match', tree_parent_group_id=None
        )
        self.tree._ordered_users = Mock(return_value=[user])
        matching = MagicMock()
        matching.order_by.return_value.values_list.return_value = []
        resolved = MagicMock()
        resolved.order_by.return_value = []
        self.tree.groups.filter.side_effect = [matching, resolved]
        result = self.tree.search('match', limit=1)
        self.assertEqual(
            [node['meta']['type'] for node in result['results']],
            ['organization', 'ungrouped_users', 'user'],
        )
        self.assertEqual(result['results'][2]['pId'], result['results'][1]['id'])
        self.assertEqual(result['matched_user_count'], 1)
        self.assertFalse(result['truncated'])

    def test_virtual_group_api_parameters_and_count_type(self):
        query = UserGroupTreeQuerySerializer(data={
            'parent_type': 'ungrouped_users', 'parent_id': self.org_id,
            'offset': 100, 'limit': 100,
        })
        self.assertTrue(query.is_valid(), query.errors)
        invalid = UserGroupTreeQuerySerializer(data={
            'parent_type': 'ungrouped_users', 'parent_id': 'not-an-org-id',
        })
        self.assertFalse(invalid.is_valid())
        metrics = PermissionTreeMetricsQuerySerializer(data={
            'resources': [{'type': 'ungrouped_users', 'id': self.org_id}],
            'metric': 'permission_effective',
        })
        self.assertTrue(metrics.is_valid(), metrics.errors)
        filters = AssetPermissionFilter(data={'ungrouped_users': 'true'})
        self.assertTrue(filters.form.is_valid(), filters.form.errors)
        self.assertIs(filters.get_query_param('ungrouped_users'), True)
