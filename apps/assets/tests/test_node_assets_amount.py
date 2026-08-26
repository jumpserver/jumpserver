from django.test import SimpleTestCase
from rest_framework.request import Request
from rest_framework.test import APIRequestFactory

from assets.api.tree import NodeChildrenAsTreeApi
from assets.models import Node
from assets.serializers import (
    NodeAssetsAmountQuerySerializer, NodeSerializer,
)


class NodeAssetsAmountQueryTestCase(SimpleTestCase):
    def test_realtime_amount_is_a_distinct_correlated_subquery(self):
        query = str(Node.objects.with_realtime_assets_amount().query)

        self.assertIn('COUNT(DISTINCT', query)
        self.assertIn('assets_amount_realtime', query)
        self.assertIn('LIKE', query)

    def test_direct_amount_does_not_query_descendant_keys(self):
        query = str(Node.objects.with_realtime_assets_amount(
            include_descendants=False
        ).query)

        self.assertIn('COUNT(DISTINCT', query)
        self.assertIn('assets_amount_realtime', query)
        self.assertNotIn('LIKE', query)

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

    def test_amount_batch_deduplicates_node_ids(self):
        node_id = '00000000-0000-0000-0000-000000000001'
        serializer = NodeAssetsAmountQuerySerializer(data={
            'node_ids': [node_id, node_id]
        })

        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(len(serializer.validated_data['node_ids']), 1)
        self.assertTrue(serializer.validated_data['include_descendants'])

    def test_amount_batch_accepts_direct_asset_scope(self):
        node_id = '00000000-0000-0000-0000-000000000001'
        serializer = NodeAssetsAmountQuerySerializer(data={
            'node_ids': [node_id],
            'include_descendants': False,
        })

        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertFalse(serializer.validated_data['include_descendants'])

    def test_amount_batch_is_bounded(self):
        serializer = NodeAssetsAmountQuerySerializer(data={
            'node_ids': [
                f'00000000-0000-0000-0000-{index:012d}'
                for index in range(201)
            ]
        })

        self.assertFalse(serializer.is_valid())
        self.assertIn('node_ids', serializer.errors)

    def test_tree_base_queryset_does_not_annotate_amount(self):
        view = NodeChildrenAsTreeApi()
        view.request = Request(APIRequestFactory().get(
            '/api/v1/assets/nodes/children/tree/',
            {'asset_amount': '0', 'all': 'all'},
        ))
        view.is_initial = False
        view.instance = None

        annotations = view.get_base_queryset().query.annotations

        self.assertNotIn('assets_amount_realtime', annotations)
