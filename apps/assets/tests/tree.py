from assets.tree import Tree


def test():
    from orgs.models import Organization
    from assets.models import Node, Asset
    import time
    Organization.objects.get(id='1863cf22-f666-474e-94aa-935fe175203c').change_to()

    t1 = time.time()
    nodes = list(Node.objects.exclude(key__startswith='-').only('id', 'key', 'parent_key'))
    node_asset_id_pairs = Asset.nodes.through.objects.all().values_list('node_id', 'asset_id')
    t2 = time.time()
    node_asset_id_pairs = list(node_asset_id_pairs)
    tree = Tree(nodes,  node_asset_id_pairs)
    tree.build_tree()
    tree.nodes = None
    tree.node_asset_id_pairs = None
    import pickle
    d = pickle.dumps(tree)
    print('------------', len(d))
    return tree
    tree.compute_tree_node_assets_amount()

    print(f'校对算法准确性 ......')
    for node in nodes:
        tree_node = tree.key_tree_node_mapper[node.key]
        if tree_node.assets_amount != node.assets_amount:
            print(f'ERROR: {tree_node.assets_amount} {node.assets_amount}')
        # print(f'OK {tree_node.asset_amount} {node.assets_amount}')

    print(f'数据库时间: {t2 - t1}')
    return tree