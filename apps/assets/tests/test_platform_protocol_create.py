from rest_framework.test import APITestCase

from assets.models import Platform, PlatformProtocol
from rbac.models import Permission, Role
from users.models import User


class PlatformProtocolCreateTests(APITestCase):
    url = '/api/v1/assets/protocol-settings/'

    def setUp(self):
        self.platform = Platform.objects.create(name='Protocol test platform', category='host', type='linux')
        self.payload = {'platform': self.platform.pk, 'name': 'ssh', 'port': 2200}

    def sign_in_with(self, codename):
        user = User.objects.create(username=codename)
        role = Role.objects.create(name=codename)
        role.permissions.add(Permission.objects.get(content_type__app_label='assets', codename=codename))
        user.system_roles.add(role)
        self.client.force_authenticate(user)

    def test_editor_can_create_protocol_on_existing_platform(self):
        self.sign_in_with('change_platform')
        response = self.client.post(self.url + '?format=json', self.payload, format='json')
        self.assertEqual(response.status_code, 201, response.content)
        self.assertEqual(response.data['platform'], self.platform.pk)
        protocol = self.platform.protocols.get(pk=response.data['id'])
        self.assertEqual((protocol.name, protocol.port), ('ssh', 2200))

    def test_missing_and_invalid_fields_return_400(self):
        self.sign_in_with('change_platform')
        response = self.client.post(self.url, {}, format='json')
        self.assertEqual(response.status_code, 400, response.content)
        self.assertEqual(set(response.data), {'platform', 'name', 'port'})
        for field, value in (
            ('platform', self.platform.pk + 1000), ('platform', 'invalid'), ('platform', 1.5),
            ('name', ''), ('port', 'invalid'), ('port', -1), ('port', 65536),
        ):
            with self.subTest(field=field, value=value):
                response = self.client.post(self.url, {**self.payload, field: value}, format='json')
                self.assertEqual(response.status_code, 400, response.content)
                self.assertIn(field, response.data)
        self.assertFalse(self.platform.protocols.exists())

    def test_editor_cannot_add_protocol_to_internal_platform(self):
        self.sign_in_with('change_platform')
        self.platform.internal = True
        self.platform.save(update_fields=['internal'])
        response = self.client.post(self.url, self.payload, format='json')
        self.assertEqual(response.status_code, 403, response.content)
        self.assertFalse(self.platform.protocols.exists())

    def test_editor_can_add_protocol_to_existing_platform_form(self):
        self.sign_in_with('change_platform')
        ssh = self.platform.protocols.create(name='ssh', port=22, primary=True)
        response = self.client.patch(f'/api/v1/assets/platforms/{self.platform.pk}/', {
            'protocols': [
                {'id': ssh.pk, 'name': 'ssh', 'port': 22, 'primary': True},
                {'name': 'rdp', 'port': 3389},
            ],
        }, format='json')
        self.assertEqual(response.status_code, 200, response.content)
        self.assertCountEqual(self.platform.protocols.values_list('name', 'port'), [('ssh', 22), ('rdp', 3389)])

    def test_add_permission_allows_platform_form_but_not_standalone_create(self):
        self.sign_in_with('add_platform')
        metadata = self.client.options(self.url + '?name=ssh')
        self.assertEqual(metadata.status_code, 200, metadata.content)
        self.assertIn('setting', metadata.data['actions']['POST'])
        response = self.client.post(self.url, self.payload, format='json')
        self.assertEqual(response.status_code, 403, response.content)
        self.assertFalse(self.platform.protocols.exists())

        response = self.client.post('/api/v1/assets/platforms/', {
            'name': 'New platform', 'category': 'host', 'type': 'linux',
            'protocols': [{'name': 'ssh', 'port': 2200}],
        }, format='json')
        self.assertEqual(response.status_code, 201, response.content)
        protocol = PlatformProtocol.objects.get(platform_id=response.data['id'])
        self.assertEqual((protocol.name, protocol.port), ('ssh', 2200))
