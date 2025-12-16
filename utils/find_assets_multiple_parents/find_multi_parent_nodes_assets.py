import os
import sys
import django
from datetime import datetime

if os.path.exists('../../apps'):
    sys.path.insert(0, '../../apps')
if os.path.exists('../apps'):
    sys.path.insert(0, '../apps')
elif os.path.exists('./apps'):
    sys.path.insert(0, './apps')

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "jumpserver.settings")
django.setup()


from assets.models import Asset, Node
from orgs.models import Organization
from django.db.models import Count

OUTPUT_FILE = 'report_find_multi_parent_nodes_assets.txt'

# Special organization IDs and names
SPECIAL_ORGS = {
    '00000000-0000-0000-0000-000000000000': 'GLOBAL',
    '00000000-0000-0000-0000-000000000002': 'DEFAULT',
    '00000000-0000-0000-0000-000000000004': 'SYSTEM',
}

try:
    AssetNodeThrough = Asset.nodes.through
except Exception as e:
    print("Failed to get AssetNodeThrough model. Check Asset.nodes field definition.")
    raise e


def log(msg=''):
    """Print log with timestamp"""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")


def get_org_name(org_id, orgs_map):
    """Get organization name, check special orgs first, then orgs_map"""
    # Check if it's a special organization
    org_id_str = str(org_id)
    if org_id_str in SPECIAL_ORGS:
        return SPECIAL_ORGS[org_id_str]
    
    # Try to get from orgs_map
    org = orgs_map.get(org_id)
    if org:
        return org.name
    
    return 'Unknown'


def write_report(content):
    """Write content to report file"""
    with open(OUTPUT_FILE, 'a', encoding='utf-8') as f:
        f.write(content)


def find_assets_multiple_parents():
    """Find assets belonging to multiple node_ids organized by organization"""

    log("Searching for assets with multiple parent nodes...")
    
    # Find all asset_ids that belong to multiple node_ids
    multi_parent_assets = AssetNodeThrough.objects.values('asset_id').annotate(
        node_count=Count('node_id', distinct=True)
    ).filter(node_count__gt=1).order_by('-node_count')
    
    total_count = multi_parent_assets.count()
    log(f"Found {total_count:,} assets with multiple parent nodes\n")
    
    if total_count == 0:
        log("✓ All assets belong to only one node")
        return {}
    
    # Collect all asset_ids and node_ids that need to be fetched
    asset_ids = [item['asset_id'] for item in multi_parent_assets]
    
    # Get all through records for these assets
    all_through_records = AssetNodeThrough.objects.filter(asset_id__in=asset_ids)
    node_ids = list(set(through.node_id for through in all_through_records))
    
    # Batch fetch all Asset and Node objects
    log("Batch loading Asset objects...")
    assets_map = {asset.id: asset for asset in Asset.objects.filter(id__in=asset_ids)}
    
    log("Batch loading Node objects...")
    nodes_map = {node.id: node for node in Node.objects.filter(id__in=node_ids)}
    
    # Batch fetch all Organization objects
    org_ids = list(set(asset.org_id for asset in assets_map.values())) + \
              list(set(node.org_id for node in nodes_map.values()))
    org_ids = list(set(org_ids))  # Remove duplicates
    
    log("Batch loading Organization objects...")
    orgs_map = {org.id: org for org in Organization.objects.filter(id__in=org_ids)}
    
    # Build mapping of asset_id -> list of through_records
    asset_nodes_map = {}
    for through in all_through_records:
        if through.asset_id not in asset_nodes_map:
            asset_nodes_map[through.asset_id] = []
        asset_nodes_map[through.asset_id].append(through)
    
    # Organize by organization first, then by node count, then by asset
    org_assets_data = {}  # org_id -> { node_count -> [asset_data] }
    
    for item in multi_parent_assets:
        asset_id = item['asset_id']
        node_count = item['node_count']
        
        # Get Asset object from map
        asset = assets_map.get(asset_id)
        if not asset:
            log(f"⚠ Asset {asset_id} not found in map, skipping")
            continue
        
        org_id = asset.org_id
        
        # Initialize org data if not exists
        if org_id not in org_assets_data:
            org_assets_data[org_id] = {}
        
        # Get all nodes for this asset
        through_records = asset_nodes_map.get(asset_id, [])
        
        node_details = []
        for through in through_records:
            # Get Node object from map
            node = nodes_map.get(through.node_id)
            if not node:
                log(f"⚠ Node {through.node_id} not found in map, skipping")
                continue
            
            node_details.append({
                'id': node.id,
                'name': node.name,
                'key': node.key,
                'path': node.full_value if hasattr(node, 'full_value') else ''
            })
        
        if not node_details:
            continue
        
        if node_count not in org_assets_data[org_id]:
            org_assets_data[org_id][node_count] = []
        
        org_assets_data[org_id][node_count].append({
            'asset_id': asset.id,
            'asset_name': asset.name,
            'nodes': node_details
        })
    
    return org_assets_data


def generate_report(org_assets_data):
    """Generate and write report to file organized by organization"""
    # Clear previous report
    if os.path.exists(OUTPUT_FILE):
        os.remove(OUTPUT_FILE)
    
    # Write header
    write_report(f"Multi-Parent Assets Report\n")
    write_report(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    write_report(f"{'='*80}\n\n")
    
    # Get all organizations
    all_org_ids = list(set(org_id for org_id in org_assets_data.keys()))
    all_orgs = {org.id: org for org in Organization.objects.filter(id__in=all_org_ids)}
    
    # Calculate statistics
    total_orgs = Organization.objects.count()
    orgs_with_issues = len(org_assets_data)
    orgs_without_issues = total_orgs - orgs_with_issues
    total_assets_with_issues = sum(
        len(assets) 
        for org_id in org_assets_data 
        for assets in org_assets_data[org_id].values()
    )
    
    # Overview
    write_report("OVERVIEW\n")
    write_report(f"{'-'*80}\n")
    write_report(f"Total organizations: {total_orgs:,}\n")
    write_report(f"Organizations with multiple-parent assets: {orgs_with_issues:,}\n")
    write_report(f"Organizations without issues: {orgs_without_issues:,}\n")
    write_report(f"Total assets with multiple parent nodes: {total_assets_with_issues:,}\n\n")
    
    # Summary by organization
    write_report("Summary by Organization:\n")
    for org_id in sorted(org_assets_data.keys()):
        org_name = get_org_name(org_id, all_orgs)
        
        org_asset_count = sum(
            len(assets) 
            for assets in org_assets_data[org_id].values()
        )
        write_report(f"  - {org_name} ({org_id}): {org_asset_count:,} assets\n")
    
    write_report(f"\n{'='*80}\n\n")
    
    # Detailed sections grouped by organization, then node count
    for org_id in sorted(org_assets_data.keys()):
        org_name = get_org_name(org_id, all_orgs)
        
        org_asset_count = sum(
            len(assets) 
            for assets in org_assets_data[org_id].values()
        )
        
        write_report(f"ORGANIZATION: {org_name} ({org_id})\n")
        write_report(f"Total assets with issues: {org_asset_count:,}\n")
        write_report(f"{'-'*80}\n\n")
        
        # Group by node count within this organization
        for node_count in sorted(org_assets_data[org_id].keys(), reverse=True):
            assets = org_assets_data[org_id][node_count]
            
            write_report(f"  Section: {node_count} Parent Nodes ({len(assets):,} assets)\n")
            write_report(f"  {'-'*76}\n\n")
            
            for asset in assets:
                write_report(f"  {asset['asset_name']} ({asset['asset_id']})\n")
                
                for node in asset['nodes']:
                    write_report(f"    {node['name']} ({node['key']}) ({node['path']}) ({node['id']})\n")
                
                write_report(f"\n")
            
            write_report(f"\n")
        
        write_report(f"{'='*80}\n\n")
    
    log(f"✓ Report written to {OUTPUT_FILE}")


def main():
    try:
        org_assets_data = find_assets_multiple_parents()
        
        if not org_assets_data:
            log("✓ Detection complete, no issues found")
            sys.exit(0)
        
        total_assets = sum(
            len(assets) 
            for org_id in org_assets_data 
            for assets in org_assets_data[org_id].values()
        )
        log(f"Generating report for {total_assets:,} assets across {len(org_assets_data):,} organizations...")
        
        generate_report(org_assets_data)
        
        log(f"✗ Detected {total_assets:,} assets with multiple parent nodes")
        sys.exit(1)
    
    except Exception as e:
        log(f"✗ Error occurred: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(2)


if __name__ == "__main__":
    main()
