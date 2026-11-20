from urllib.parse import urlsplit

from rest_framework.test import APITestCase

from assets.models import Node
from orgs.models import Organization
from orgs.utils import tmp_to_org
from rbac.builtin import BuiltinRole
from users.models import User


class NodeTreePaginationTests(APITestCase):
    def test_next_page_uses_a_same_origin_link(self):
        org = Organization.default()
        user = User.objects.create(username='node-tree-admin')
        org.add_member(user, role=BuiltinRole.org_admin)
        self.client.force_authenticate(user)
        with tmp_to_org(org):
            parent = Node.org_root().create_child('Parent')
            parent.create_child('First')
            parent.create_child('Second')

        url = '/api/v1/assets/nodes/children/tree/'
        first_page = self.client.get(url, {
            'parent_key': parent.key,
            'include_asset_count': 0,
            'node_page_size': 1,
        })
        self.assertEqual(first_page.status_code, 200, first_page.content)
        data = first_page.json()
        self.assertEqual([node['name'] for node in data['results']], ['First'])
        self.assertTrue(data['node_pagination']['has_more'])
        next_link = data['node_pagination']['next']
        parts = urlsplit(next_link)
        self.assertEqual((parts.scheme, parts.netloc, parts.path), ('', '', url))

        second_page = self.client.get(next_link)
        self.assertEqual(second_page.status_code, 200, second_page.content)
        data = second_page.json()
        self.assertEqual([node['name'] for node in data['results']], ['Second'])
        self.assertFalse(data['node_pagination']['has_more'])
        self.assertIsNone(data['node_pagination']['next'])
