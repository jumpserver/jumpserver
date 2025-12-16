import os
import sys
import django
import random
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

OUTPUT_FILE = 'report_cleanup_and_keep_one_node_for_multi_parent_nodes_assets.txt'

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
    """Print log with timestamp to console"""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")


def write_report(content):
    """Write content to report file"""
    with open(OUTPUT_FILE, 'a', encoding='utf-8') as f:
        f.write(content)


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


def find_and_cleanup_multi_parent_assets():
    """Find and cleanup assets with multiple parent nodes"""
    
    log("Searching for assets with multiple parent nodes...")
    
    # Find all asset_ids that belong to multiple node_ids
    multi_parent_assets = AssetNodeThrough.objects.values('asset_id').annotate(
        node_count=Count('node_id', distinct=True)
    ).filter(node_count__gt=1).order_by('-node_count')
    
    total_count = multi_parent_assets.count()
    log(f"Found {total_count:,} assets with multiple parent nodes\n")
    
    if total_count == 0:
        log("✓ All assets already have single parent node")
        return {}
    
    # Collect all asset_ids and node_ids
    asset_ids = [item['asset_id'] for item in multi_parent_assets]
    
    # Get all through records
    all_through_records = AssetNodeThrough.objects.filter(asset_id__in=asset_ids)
    node_ids = list(set(through.node_id for through in all_through_records))
    
    # Batch fetch all objects
    log("Batch loading Asset objects...")
    assets_map = {asset.id: asset for asset in Asset.objects.filter(id__in=asset_ids)}
    
    log("Batch loading Node objects...")
    nodes_map = {node.id: node for node in Node.objects.filter(id__in=node_ids)}
    
    # Batch fetch all Organization objects
    org_ids = list(set(asset.org_id for asset in assets_map.values())) + \
              list(set(node.org_id for node in nodes_map.values()))
    org_ids = list(set(org_ids))
    
    log("Batch loading Organization objects...")
    orgs_map = {org.id: org for org in Organization.objects.filter(id__in=org_ids)}
    
    # Build mapping of asset_id -> list of through_records
    asset_nodes_map = {}
    for through in all_through_records:
        if through.asset_id not in asset_nodes_map:
            asset_nodes_map[through.asset_id] = []
        asset_nodes_map[through.asset_id].append(through)
    
    # Organize by organization
    org_cleanup_data = {}  # org_id -> { asset_id -> { keep_node_id, remove_node_ids } }
    
    for item in multi_parent_assets:
        asset_id = item['asset_id']
        
        # Get Asset object
        asset = assets_map.get(asset_id)
        if not asset:
            log(f"⚠ Asset {asset_id} not found in map, skipping")
            continue
        
        org_id = asset.org_id
        
        # Initialize org data if not exists
        if org_id not in org_cleanup_data:
            org_cleanup_data[org_id] = {}
        
        # Get all nodes for this asset
        through_records = asset_nodes_map.get(asset_id, [])
        
        if len(through_records) < 2:
            continue
        
        # Randomly select one node to keep
        keep_through = random.choice(through_records)
        remove_throughs = [t for t in through_records if t.id != keep_through.id]
        
        org_cleanup_data[org_id][asset_id] = {
            'asset_name': asset.name,
            'keep_node_id': keep_through.node_id,
            'keep_node': nodes_map.get(keep_through.node_id),
            'remove_records': remove_throughs,
            'remove_nodes': [nodes_map.get(t.node_id) for t in remove_throughs]
        }
    
    return org_cleanup_data


def perform_cleanup(org_cleanup_data, dry_run=False):
    """Perform the actual cleanup - delete extra node relationships"""
    
    if dry_run:
        log("DRY RUN: Simulating cleanup process (no data will be deleted)...")
    else:
        log("\nStarting cleanup process...")
    
    total_deleted = 0
    
    for org_id in org_cleanup_data.keys():
        for asset_id, cleanup_info in org_cleanup_data[org_id].items():
            # Delete the extra relationships
            for through_record in cleanup_info['remove_records']:
                if not dry_run:
                    through_record.delete()
                total_deleted += 1
    
    return total_deleted


def verify_cleanup():
    """Verify that there are no more assets with multiple parent nodes"""
    log("\n" + "="*80)
    log("VERIFICATION: Checking for remaining assets with multiple parent nodes...")
    log("="*80)
    
    # Find all asset_ids that belong to multiple node_ids
    multi_parent_assets = AssetNodeThrough.objects.values('asset_id').annotate(
        node_count=Count('node_id', distinct=True)
    ).filter(node_count__gt=1).order_by('-node_count')
    
    remaining_count = multi_parent_assets.count()
    
    if remaining_count == 0:
        log(f"✓ Verification successful: No assets with multiple parent nodes remaining\n")
        return True
    else:
        log(f"✗ Verification failed: Found {remaining_count:,} assets still with multiple parent nodes\n")
        # Show some details
        for item in multi_parent_assets[:10]:
            asset_id = item['asset_id']
            node_count = item['node_count']
            try:
                asset = Asset.objects.get(id=asset_id)
                log(f"  - Asset: {asset.name} ({asset_id}) has {node_count} parent nodes")
            except:
                log(f"  - Asset ID: {asset_id} has {node_count} parent nodes")
        
        if remaining_count > 10:
            log(f"  ... and {remaining_count - 10} more")
        
        return False


def generate_report(org_cleanup_data, total_deleted):
    """Generate and write report to file"""
    # Clear previous report
    if os.path.exists(OUTPUT_FILE):
        os.remove(OUTPUT_FILE)
    
    # Write header
    write_report(f"Multi-Parent Assets Cleanup Report\n")
    write_report(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    write_report(f"{'='*80}\n\n")
    
    # Get all organizations
    all_org_ids = list(set(org_id for org_id in org_cleanup_data.keys()))
    all_orgs = {org.id: org for org in Organization.objects.filter(id__in=all_org_ids)}
    
    # Calculate statistics
    total_orgs = Organization.objects.count()
    orgs_processed = len(org_cleanup_data)
    orgs_no_issues = total_orgs - orgs_processed
    total_assets_cleaned = sum(len(assets) for assets in org_cleanup_data.values())
    
    # Overview
    write_report("OVERVIEW\n")
    write_report(f"{'-'*80}\n")
    write_report(f"Total organizations: {total_orgs:,}\n")
    write_report(f"Organizations processed: {orgs_processed:,}\n")
    write_report(f"Organizations without issues: {orgs_no_issues:,}\n")
    write_report(f"Total assets cleaned: {total_assets_cleaned:,}\n")
    total_relationships = AssetNodeThrough.objects.count()
    write_report(f"Total relationships (through records): {total_relationships:,}\n")
    write_report(f"Total relationships deleted: {total_deleted:,}\n\n")
    
    # Summary by organization
    write_report("Summary by Organization:\n")
    for org_id in sorted(org_cleanup_data.keys()):
        org_name = get_org_name(org_id, all_orgs)
        asset_count = len(org_cleanup_data[org_id])
        write_report(f"  - {org_name} ({org_id}): {asset_count:,} assets cleaned\n")
    
    write_report(f"\n{'='*80}\n\n")
    
    # Detailed cleanup information grouped by organization
    for org_id in sorted(org_cleanup_data.keys()):
        org_name = get_org_name(org_id, all_orgs)
        asset_count = len(org_cleanup_data[org_id])
        
        write_report(f"ORGANIZATION: {org_name} ({org_id})\n")
        write_report(f"Total assets cleaned: {asset_count:,}\n")
        write_report(f"{'-'*80}\n\n")
        
        for asset_id, cleanup_info in org_cleanup_data[org_id].items():
            write_report(f"Asset: {cleanup_info['asset_name']} ({asset_id})\n")
            
            # Kept node
            keep_node = cleanup_info['keep_node']
            if keep_node:
                write_report(f"  ✓ Kept:   {keep_node.name} (key: {keep_node.key}) (id: {keep_node.id})\n")
            else:
                write_report(f"  ✓ Kept:   Unknown (id: {cleanup_info['keep_node_id']})\n")
            
            # Removed nodes
            write_report(f"  ✗ Removed: {len(cleanup_info['remove_nodes'])} node(s)\n")
            for node in cleanup_info['remove_nodes']:
                if node:
                    write_report(f"      - {node.name} (key: {node.key}) (id: {node.id})\n")
                else:
                    write_report(f"      - Unknown\n")
            
            write_report(f"\n")
        
        write_report(f"{'='*80}\n\n")
    
    log(f"✓ Report written to {OUTPUT_FILE}")


def main():
    try:
        # Display warning banner
        warning_message = """
╔══════════════════════════════════════════════════════════════════════════════╗
║                                  ⚠️  WARNING  ⚠️                              ║
║                                                                              ║
║  This script is designed for TEST/FAKE DATA ONLY!                           ║
║  DO NOT run this script in PRODUCTION environment!                          ║
║                                                                              ║
║  This script will DELETE asset-node relationships from the database.        ║
║  Use only for data cleanup in development/testing environments.             ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""
        print(warning_message)
        
        # Ask user to confirm before proceeding
        confirm = input("Do you understand the warning and want to continue? (yes/no): ").strip().lower()
        if confirm not in ['yes', 'y']:
            log("✗ Operation cancelled by user")
            sys.exit(0)
        
        log("✓ Proceeding with operation\n")
        
        org_cleanup_data = find_and_cleanup_multi_parent_assets()
        
        if not org_cleanup_data:
            log("✓ Cleanup complete, no assets to process")
            sys.exit(0)
        
        total_assets = sum(len(assets) for assets in org_cleanup_data.values())
        log(f"\nProcessing {total_assets:,} assets across {len(org_cleanup_data):,} organizations...")
        
        # First, do a dry-run to show what will be deleted
        log("\n" + "="*80)
        log("PREVIEW: Simulating cleanup process...")
        log("="*80)
        total_deleted_preview = perform_cleanup(org_cleanup_data, dry_run=True)
        log(f"✓ Dry-run complete: {total_deleted_preview:,} relationships would be deleted\n")
        
        # Generate preview report
        generate_report(org_cleanup_data, total_deleted_preview)
        log(f"✓ Preview report written to {OUTPUT_FILE}\n")
        
        # Ask for confirmation 3 times before actual deletion
        log("="*80)
        log("FINAL CONFIRMATION: Do you want to proceed with actual cleanup?")
        log("="*80)
        confirmation_count = 3
        for attempt in range(1, confirmation_count + 1):
            response = input(f"Confirm cleanup (attempt {attempt}/{confirmation_count})? (yes/no): ").strip().lower()
            if response not in ['yes', 'y']:
                log(f"✗ Cleanup cancelled by user at attempt {attempt}")
                sys.exit(1)
        
        log("✓ All confirmations received, proceeding with actual cleanup")
        
        # Perform cleanup
        total_deleted = perform_cleanup(org_cleanup_data)
        log(f"✓ Deleted {total_deleted:,} relationships")
        
        # Generate final report
        generate_report(org_cleanup_data, total_deleted)
        
        # Verify cleanup by checking for remaining multi-parent assets
        verify_cleanup()
        
        log(f"✓ Cleanup complete: processed {total_assets:,} assets")
        sys.exit(0)
    
    except Exception as e:
        log(f"✗ Error occurred: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(2)


if __name__ == "__main__":
    main()
