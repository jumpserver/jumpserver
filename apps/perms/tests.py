from types import SimpleNamespace

from django.test import SimpleTestCase, TestCase
from rest_framework.request import Request
from rest_framework.test import APIRequestFactory

from assets.models import Asset, MyAsset, Platform
from orgs.models import Organization
from perms.api.user_permission.assets import UserAllPermedAssetsApi
from perms.api.user_permission.nodes import UserAllPermedNodesApi
from users.models import User


class UserAllPermedNodesApiTest(SimpleTestCase):
    def test_search_filters_list_queryset_by_full_value(self):
        nodes = [
            SimpleNamespace(full_value='/Default/Alpha'),
            SimpleNamespace(full_value='/Default/Beta'),
        ]
        view = UserAllPermedNodesApi()
        view.request = Request(APIRequestFactory().get('/', {'search': 'ALP'}))
        view.__dict__['query_node_util'] = SimpleNamespace(
            get_whole_tree_nodes=lambda: nodes
        )

        filtered = view.filter_queryset(view.get_queryset())

        self.assertEqual(filtered, nodes[:1])


class UserAllPermedAssetsApiTest(TestCase):
    def test_order_by_name_uses_custom_name_with_asset_name_fallback(self):
        user = User.objects.create(username='custom-name-ordering')
        platform = Platform.objects.create(name='CustomNameOrdering')
        custom_asset = Asset.objects.create(
            name='Zulu', address='192.0.2.1', platform=platform,
            org_id=Organization.DEFAULT_ID,
        )
        original_asset = Asset.objects.create(
            name='Beta', address='192.0.2.2', platform=platform,
            org_id=Organization.DEFAULT_ID,
        )
        MyAsset.objects.create(user=user, asset=custom_asset, name='Alpha')

        view = UserAllPermedAssetsApi()
        request = Request(APIRequestFactory().get('/', {'order': 'name'}))
        request.user = user
        view.request = request
        view.kwargs = {'user': 'self'}
        view.__dict__['query_asset_util'] = SimpleNamespace(
            get_all_assets=lambda: Asset.objects.filter(
                id__in=[custom_asset.id, original_asset.id]
            )
        )

        queryset = view.filter_queryset(view.get_queryset())

        self.assertEqual(
            list(queryset.values_list('id', flat=True)),
            [custom_asset.id, original_asset.id],
        )
