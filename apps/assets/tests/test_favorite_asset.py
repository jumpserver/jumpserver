from rest_framework.test import APITestCase

from assets.models import Asset, FavoriteFolder, Platform
from orgs.models import Organization
from orgs.utils import tmp_to_org
from perms.models import AssetPermission
from users.models import User


class FavoriteAssetTests(APITestCase):
    def test_manage_favorite_by_returned_id(self):
        org = Organization.default()
        with tmp_to_org(org):
            user = User.objects.create(username='favorite-user', name='Favorite user')
            org.add_member(user)
            platform = Platform.objects.create(name='Favorite platform', category='host', type='linux')
            asset = Asset.objects.create(name='Favorite host', address='192.0.2.1', platform=platform)
            grant = AssetPermission.objects.create(name='Favorite access')
            grant.users.add(user)
            grant.assets.add(asset)
        folder = FavoriteFolder.objects.create(user=user, name='Servers')
        self.client.force_authenticate(user)

        url = '/api/v1/assets/favorite-assets/'
        asset_id = str(asset.pk)
        created = self.client.post(url, {'asset': asset_id}, format='json')
        self.assertEqual(created.status_code, 201, created.content)
        favorite_id = created.json()['id']
        self.assertNotEqual(favorite_id, asset_id)
        self.assertEqual(created.json()['asset_info']['id'], asset_id)

        listed = self.client.get(url, {'limit': 1})
        self.assertEqual(listed.status_code, 200)
        self.assertEqual(listed.json()['results'][0]['id'], favorite_id)
        detail_url = f'{url}{favorite_id}/'
        detail = self.client.get(detail_url)
        self.assertEqual(detail.status_code, 200)
        self.assertEqual(detail.json()['asset'], asset_id)

        updated = self.client.patch(detail_url, {'id': asset_id, 'folder': str(folder.pk)}, format='json')
        self.assertEqual(updated.status_code, 200, updated.content)
        self.assertEqual(updated.json()['id'], favorite_id)
        self.assertEqual(self.client.get(detail_url).json()['folder'], str(folder.pk))

        replaced = self.client.put(detail_url, {'asset': asset_id, 'folder': None}, format='json')
        self.assertEqual(replaced.status_code, 200, replaced.content)
        self.assertIsNone(self.client.get(detail_url).json()['folder'])
        self.assertEqual(self.client.delete(detail_url).status_code, 204)
        self.assertEqual(self.client.get(detail_url).status_code, 404)
