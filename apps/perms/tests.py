from types import SimpleNamespace

from django.test import SimpleTestCase
from rest_framework.request import Request
from rest_framework.test import APIRequestFactory

from perms.api.user_permission.nodes import UserAllPermedNodesApi


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
