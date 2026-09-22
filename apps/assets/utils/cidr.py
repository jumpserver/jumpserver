from collections import defaultdict
from ipaddress import ip_address, ip_network


def address_in_networks(address, networks):
    try:
        address = ip_address(address)
    except ValueError:
        return False
    return any(address in network for network in networks)


def filter_assets_by_cidrs(queryset, cidrs):
    networks = [ip_network(cidr) for cidr in cidrs]
    # Inspect stored addresses; never expand networks (IPv6 and /0 can be huge).
    matches = [
        pk for pk, address in queryset.values_list('pk', 'address').iterator(chunk_size=2000)
        if address_in_networks(address, networks)
    ]
    return queryset.filter(pk__in=matches)


def assign_assets_to_zones(assets):
    from assets.models import Zone

    assets_by_org = defaultdict(list)
    for asset in assets:
        if asset.zone_id or not asset.org_id:
            continue
        try:
            address = ip_address(asset.address)
        except ValueError:
            continue
        if asset.platform.name.startswith('Gateway'):
            continue
        assets_by_org[asset.org_id].append((asset, address))

    for org_id, candidates in assets_by_org.items():
        # Explicit org scope also works when a creation runs in the root context.
        zones = Zone._base_manager.filter(org_id=org_id, auto_assign=True)
        rules = []
        for zone in zones.only('id', 'cidrs'):
            for cidr in zone.cidrs:
                try:
                    rules.append((ip_network(cidr), zone.pk))
                except ValueError:
                    continue
        # Prefer the most specific subnet; UUID provides a stable tie-breaker.
        rules.sort(key=lambda rule: (-rule[0].prefixlen, str(rule[1])))
        for asset, address in candidates:
            for network, zone_id in rules:
                if address in network:
                    asset.zone_id = zone_id
                    break
