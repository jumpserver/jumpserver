from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from uuid import UUID

from django.test import SimpleTestCase

from accounts.filters import NodeFilterBackend
from accounts.serializers.tree import AccountTreeMetricsQuerySerializer
from accounts.tree import (
    _sum_account_counts_by_node, get_node_account_counts, get_account_tree_metrics, get_asset_account_counts,
)


class NodeAccountCountTests(SimpleTestCase):
    def test_shared_assets_are_counted_once_per_ancestor(self):
        counts = _sum_account_counts_by_node(
            [('a', '1'), ('a', '1:2'), ('a', '1:3'), ('b', '1:2:4'),
             ('b', '1:2:4'), ('c', '1:3')],
            {'a': 2, 'b': 5, 'c': 3}, {'1', '1:2', '1:3', '1:2:4'},
        )
        self.assertEqual(counts, {'1': 10, '1:2': 7, '1:3': 5, '1:2:4': 5})

    def test_prefix_siblings_and_empty_nodes_do_not_leak_counts(self):
        counts = _sum_account_counts_by_node(
            [('a', '1:20'), ('b', '1:2:3'), ('missing', '1:2')],
            {'a': 100, 'b': 4}, {'1:2', '1:20', '1:5'},
        )
        self.assertEqual(counts, {'1:2': 4, '1:20': 100, '1:5': 0})

    def test_large_account_population_uses_asset_weights(self):
        counts = _sum_account_counts_by_node(
            [('a', '1:2'), ('a', '1:3'), ('b', '1:3')],
            {'a': 1000000, 'b': 7}, {'1', '1:2', '1:3'},
        )
        self.assertEqual(counts, {'1': 1000007, '1:2': 1000000, '1:3': 1000007})

    def test_empty_node_batch_needs_no_account_query(self):
        accounts = MagicMock()
        self.assertEqual(get_node_account_counts([], accounts=accounts), {})
        accounts.filter.assert_not_called()

    def test_request_has_no_200_node_cap_and_deduplicates(self):
        node_ids = [str(UUID(int=i)) for i in range(1, 252)]
        resources = [{'type': 'node', 'id': node_id} for node_id in node_ids]
        serializer = AccountTreeMetricsQuerySerializer(data={'resources': resources + resources[:1]})
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(len(serializer.validated_data['resources']), 251)
        self.assertTrue(serializer.validated_data['include_descendants'])
        direct = AccountTreeMetricsQuerySerializer(data={
            'resources': resources[:1], 'include_descendants': False,
        })
        self.assertTrue(direct.is_valid(), direct.errors)
        self.assertFalse(direct.validated_data['include_descendants'])

    def test_invalid_node_ids_and_scope_are_rejected(self):
        for payload in ({'resources': []}, {'resources': [{'type': 'asset', 'id': 'invalid'}]},
                        {'resources': [{'type': 'user', 'id': str(UUID(int=1))}]},
                        {'resources': [{'type': 'node', 'id': str(UUID(int=1))}], 'include_descendants': 'invalid'}):
            serializer = AccountTreeMetricsQuerySerializer(data=payload)
            self.assertFalse(serializer.is_valid(), payload)

    @patch('accounts.filters.get_node_from_request')
    def test_direct_scope_does_not_expand_descendants(self, get_node):
        node = get_node.return_value
        queryset = MagicMock()
        request = SimpleNamespace(query_params={'include_descendants': 'false'})
        result = NodeFilterBackend().filter_queryset(request, queryset, None)
        queryset.filter.assert_called_once_with(asset__nodes=node)
        node.get_all_children.assert_not_called()
        self.assertIs(result, queryset.filter.return_value.distinct.return_value)

    @patch('accounts.filters.get_node_from_request')
    def test_default_scope_includes_current_node_and_descendants(self, get_node):
        node = get_node.return_value
        queryset = MagicMock()
        request = SimpleNamespace(query_params={})
        NodeFilterBackend().filter_queryset(request, queryset, None)
        node.get_all_children.assert_called_once_with(with_self=True)
        node.get_all_children.return_value.filter.assert_called_once_with(org_id=node.org_id)
        queryset.filter.return_value.distinct.assert_called_once()

    @patch('accounts.filters.get_node_from_request')
    def test_named_scope_takes_precedence_over_legacy_flag(self, get_node):
        request = SimpleNamespace(query_params={
            'include_descendants': 'true', 'show_current_asset': '1',
        })
        NodeFilterBackend().filter_queryset(request, MagicMock(), None)
        get_node.return_value.get_all_children.assert_called_once_with(with_self=True)

    @patch('accounts.filters.get_node_from_request')
    def test_legacy_direct_scope_remains_supported(self, get_node):
        node = get_node.return_value
        queryset = MagicMock()
        request = SimpleNamespace(query_params={'show_current_asset': '1'})
        NodeFilterBackend().filter_queryset(request, queryset, None)
        queryset.filter.assert_called_once_with(asset__nodes=node)

    def test_repeated_asset_occurrences_are_deduplicated_by_type_and_id(self):
        resource_id = UUID(int=1)
        node = {'type': 'node', 'id': str(resource_id)}
        asset = {'type': 'asset', 'id': str(resource_id)}
        serializer = AccountTreeMetricsQuerySerializer(data={
            'resources': [node, asset, asset, node],
        })
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(serializer.validated_data['resources'], [
            {'type': 'node', 'id': resource_id}, {'type': 'asset', 'id': resource_id},
        ])

    @patch('accounts.tree.Asset')
    @patch('accounts.tree.Node')
    @patch('accounts.tree.get_node_account_counts')
    def test_asset_counts_are_independent_of_node_scope(self, node_counts, nodes, assets):
        node_id, asset_id, empty_asset_id, hidden_id = [UUID(int=i) for i in range(1, 5)]
        assets.objects.filter.return_value.order_by.return_value.values_list.return_value = [asset_id, empty_asset_id]
        accounts = MagicMock()
        accounts.filter.return_value.order_by.return_value.values.return_value.annotate.return_value.values_list.return_value = [(asset_id, 7)]
        resources = [
            {'type': 'node', 'id': node_id}, {'type': 'asset', 'id': asset_id},
            {'type': 'asset', 'id': empty_asset_id}, {'type': 'asset', 'id': hidden_id},
        ]
        for descendants, node_count in ((True, 90), (False, 10)):
            node_counts.return_value = {node_id: node_count}
            results = get_account_tree_metrics(resources, accounts, descendants)
            self.assertEqual(results, [
                {'type': 'node', 'id': str(node_id), 'count': node_count},
                {'type': 'asset', 'id': str(asset_id), 'count': 7},
                {'type': 'asset', 'id': str(empty_asset_id), 'count': 0},
            ])

    @patch('accounts.tree.Asset')
    def test_asset_accounts_include_directory_services_without_duplicates(self, assets):
        assets.objects.filter.return_value.order_by.return_value.values_list.return_value = ['asset', 'empty']
        assets.directory_services.through.objects.filter.return_value.values_list.return_value = [
            ('asset', 'directory'), ('asset', 'directory'), ('asset', 'asset'),
        ]
        accounts = MagicMock()
        accounts.filter.return_value.order_by.return_value.values.return_value.annotate.return_value.values_list.return_value = [
            ('asset', 2), ('directory', 5),
        ]
        self.assertEqual(get_asset_account_counts(['asset', 'empty'], accounts), {
            'asset': 7, 'empty': 0,
        })
        accounts.filter.assert_called_once_with(asset_id__in={'asset', 'empty', 'directory'})
