from django.test import SimpleTestCase
from rest_framework.test import APIRequestFactory

from assets.models import Node
from assets.serializers import NodeSerializer


class NodeAssetsAmountQueryTestCase(SimpleTestCase):
    def test_realtime_amount_is_a_distinct_correlated_subquery(self):
        query = str(Node.objects.with_realtime_assets_amount().query)

        self.assertIn('COUNT(DISTINCT', query)
        self.assertIn('assets_amount_realtime', query)
        self.assertIn('LIKE', query)

    def test_has_children_is_an_exists_subquery(self):
        query = str(Node.objects.with_has_children().query)

        self.assertIn('EXISTS', query)
        self.assertIn('has_children', query)

    def test_assets_can_make_node_expandable_when_requested(self):
        query = str(
            Node.objects.with_has_children(include_assets=True).query
        )

        self.assertGreaterEqual(query.count('EXISTS'), 2)

    def test_write_response_does_not_request_assets_amount(self):
        request = APIRequestFactory().post('/api/v1/assets/nodes/')
        serializer = NodeSerializer(context={'request': request})

        self.assertNotIn('assets_amount', serializer.fields)

    def test_get_response_includes_assets_amount(self):
        request = APIRequestFactory().get('/api/v1/assets/nodes/')
        serializer = NodeSerializer(context={'request': request})

        self.assertIn('assets_amount', serializer.fields)
