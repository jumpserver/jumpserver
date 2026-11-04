from rest_framework.test import APITestCase

from assets.models import Node
from orgs.models import Organization
from orgs.utils import tmp_to_org
from rbac.builtin import BuiltinRole
from users.models import User


class NodeAddChildrenTests(APITestCase):
    def setUp(self):
        org = Organization.default()
        user = User.objects.create(username='node-admin')
        org.add_member(user, role=BuiltinRole.org_admin)
        self.client.force_authenticate(user)
        with tmp_to_org(org):
            self.root = Node.org_root()
            self.target = self.root.create_child('Target')
            self.child = self.root.create_child('Child')

    def test_invalid_nodes_return_field_error_without_moving_children(self):
        url = f'/api/v1/assets/nodes/{self.target.pk}/children/add/'
        child_id = str(self.child.pk)
        for method in (self.client.put, self.client.patch):
            for body in ({}, {'nodes': child_id}, {'nodes': [{'id': child_id}]},
                         {'nodes': [child_id, 'invalid-uuid']}):
                with self.subTest(method=method.__name__, body=body):
                    response = method(url, body, format='json')
                    self.assertEqual(response.status_code, 400, response.content)
                    self.assertIn('nodes', response.json())
                    self.child.refresh_from_db()
                    self.assertEqual(self.child.parent_key, self.root.key)

    def test_uuid_list_moves_child_and_empty_list_is_a_noop(self):
        for method, parent in ((self.client.put, self.target), (self.client.patch, self.root)):
            with self.subTest(method=method.__name__):
                url = f'/api/v1/assets/nodes/{parent.pk}/children/add/'
                original_key = self.child.key
                response = method(url, {'nodes': []}, format='json')
                self.assertEqual(response.status_code, 200, response.content)
                self.child.refresh_from_db()
                self.assertEqual(self.child.key, original_key)

                response = method(url, {'nodes': [str(self.child.pk)]}, format='json')
                self.assertEqual(response.status_code, 200, response.content)
                self.child.refresh_from_db()
                self.assertEqual(self.child.parent_key, parent.key)
