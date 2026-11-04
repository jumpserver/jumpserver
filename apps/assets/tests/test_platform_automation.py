from rest_framework.test import APITestCase

from assets.models import PlatformAutomation
from rbac.builtin import BuiltinRole
from users.models import User


class PlatformAutomationUpdateTests(APITestCase):
    def setUp(self):
        user = User.objects.create(username='platform-automation-editor')
        user.system_roles.add(BuiltinRole.system_admin.get_role())
        self.client.force_authenticate(user)

        self.platform = {'name': 'TestPlatform', 'category': 'host', 'type': 'linux'}
        url = '/api/v1/assets/platforms/'
        created = self.client.post(url, self.platform, format='json')
        self.assertEqual(created.status_code, 201, created.content)
        platform_id = created.data['id']
        self.url = f'{url}{platform_id}/'
        self.automation = PlatformAutomation.objects.get(platform_id=platform_id)

    def test_put_preserves_omitted_automation(self):
        config = {'ansible_connection': 'ssh'}
        response = self.client.patch(self.url, {
            'automation': {'ansible_enabled': True, 'ansible_config': config},
        }, format='json')
        self.assertEqual(response.status_code, 200, response.content)

        response = self.client.put(self.url, {**self.platform, 'name': 'Renamed'}, format='json')
        self.assertEqual(response.status_code, 200, response.content)
        self.automation.refresh_from_db()
        self.assertEqual(self.automation.platform.name, 'Renamed')
        self.assertTrue(self.automation.ansible_enabled)
        self.assertEqual(self.automation.ansible_config, config)

    def test_put_accepts_empty_automation_and_rejects_null(self):
        response = self.client.put(self.url, {**self.platform, 'automation': {}}, format='json')
        self.assertEqual(response.status_code, 200, response.content)
        response = self.client.put(self.url, {**self.platform, 'automation': None}, format='json')
        self.assertEqual(response.status_code, 400, response.content)
        self.assertIn('automation', response.data)
