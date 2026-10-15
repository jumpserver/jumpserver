from ipaddress import ip_network
from unittest.mock import patch

from django.db import transaction
from django.test import SimpleTestCase, TestCase
from rest_framework.exceptions import ValidationError
from rest_framework.test import APIRequestFactory, force_authenticate

from assets.api.asset.asset import AssetFilterSet, AssetViewSet
from assets.models import Asset, Custom, Host, Platform, Zone
from assets.serializers.domain import CIDRListField, ZoneSerializer
from assets.utils.cidr import address_in_networks
from orgs.models import Organization
from orgs.utils import tmp_to_org, tmp_to_root_org
from rbac.permissions import RBACPermission
from users.models import User


class ZoneCIDRValidationTests(SimpleTestCase):
    def test_optional_defaults_and_normalization(self):
        self.assertEqual(Zone().cidrs, [])
        self.assertFalse(Zone().auto_assign)
        self.assertFalse(ZoneSerializer().fields['cidrs'].required)
        self.assertEqual(CIDRListField().run_validation([]), [])
        self.assertEqual(CIDRListField().run_validation([
            '192.168.1.42/24', '192.168.1.0/24', '2001:DB8::1/32',
        ]), ['192.168.1.0/24', '2001:db8::/32'])

    def test_invalid_cidrs_are_rejected(self):
        for value in (None, '10.0.0.0/8', ['10.0.0.1'], ['example.com/24'],
                      ['10.0.0.0/33'], ['::/129'], [''], ['0.0.0.0/0'] * 101):
            with self.subTest(value=value), self.assertRaises(ValidationError):
                CIDRListField().run_validation(value)

    def test_auto_assignment_requires_cidrs_including_partial_updates(self):
        for instance, data in (
            (None, {'auto_assign': True}),
            (Zone(auto_assign=True, cidrs=['10.0.0.0/8']), {'cidrs': []}),
            (Zone(), {'auto_assign': True}),
        ):
            with self.subTest(data=data), self.assertRaises(ValidationError):
                ZoneSerializer(instance=instance, partial=True).validate(data)
        serializer = ZoneSerializer(instance=Zone(auto_assign=True, cidrs=['10.0.0.0/8']))
        self.assertEqual(serializer.validate({'name': 'Renamed'}), {'name': 'Renamed'})
        self.assertEqual(serializer.validate({'auto_assign': False, 'cidrs': []}),
                         {'auto_assign': False, 'cidrs': []})

    def test_boundaries_and_address_families(self):
        networks = [ip_network('192.0.2.0/24'), ip_network('2001:db8::/32')]
        for address in ('192.0.2.0', '192.0.2.255', '2001:db8::1'):
            self.assertTrue(address_in_networks(address, networks))
        for address in ('192.0.3.0', '2001:db9::1', 'host.example.com', 'https://192.0.2.1'):
            self.assertFalse(address_in_networks(address, networks))


class ZoneCIDRTests(TestCase):
    def setUp(self):
        self.org_context = tmp_to_org(Organization.default())
        self.org_context.__enter__()
        self.addCleanup(self.org_context.__exit__, None, None, None)
        self.platform = Platform.objects.create(name='CIDR test platform', type='linux', category='host')
        self.zone = Zone.objects.create(name='CIDR zone', cidrs=['10.0.0.0/8'], auto_assign=True)

    def create_asset(self, name='test', address='10.1.2.3', model=Host, **kwargs):
        return model.objects.create(name=name, address=address, platform=self.platform, **kwargs)

    def test_created_assets_are_assigned_before_save_returns(self):
        for model in (Asset, Host, Custom):
            with self.subTest(model=model):
                asset = self.create_asset(name=model.__name__, model=model)
                self.assertEqual(asset.zone_id, self.zone.pk)
                asset.refresh_from_db()
                self.assertEqual(asset.zone_id, self.zone.pk)

    def test_zone_serializer_saves_normalized_optional_ranges(self):
        serializer = ZoneSerializer(data={'name': 'Manual ranges', 'cidrs': ['192.0.2.55/24']})
        self.assertTrue(serializer.is_valid(), serializer.errors)
        zone = serializer.save()
        self.assertEqual(zone.cidrs, ['192.0.2.0/24'])
        self.assertFalse(zone.auto_assign)
        serializer = ZoneSerializer(zone, data={'auto_assign': True}, partial=True)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertTrue(serializer.save().auto_assign)

    def test_existing_assignment_gateway_and_hostname_are_preserved(self):
        other = Zone.objects.create(name='Explicit zone')
        assigned = self.create_asset(name='assigned', zone=other)
        self.assertEqual(assigned.zone_id, other.pk)
        self.assertIsNone(self.create_asset(name='hostname', address='host.example.com').zone_id)
        gateway_platform = Platform.objects.create(name='Gateway-CIDR', type='linux', category='host')
        gateway = Host.objects.create(name='gateway', address='10.0.0.1', platform=gateway_platform)
        self.assertIsNone(gateway.zone_id)

    def test_disabled_empty_and_nonmatching_rules_do_not_assign(self):
        self.zone.auto_assign = False
        self.zone.save()
        self.assertIsNone(self.create_asset(name='disabled').zone_id)
        self.zone.auto_assign = True
        self.zone.cidrs = []
        self.zone.save()
        self.assertIsNone(self.create_asset(name='empty').zone_id)
        self.zone.cidrs = ['192.0.2.0/24']
        self.zone.save()
        self.assertIsNone(self.create_asset(name='unmatched').zone_id)

    def test_ipv6_and_most_specific_network_win_with_stable_ties(self):
        precise = Zone.objects.create(name='Specific', cidrs=['10.1.0.0/16', '2001:db8::/32'], auto_assign=True)
        self.assertEqual(self.create_asset().zone_id, precise.pk)
        self.assertEqual(self.create_asset(name='ipv6', address='2001:db8::8').zone_id, precise.pk)
        tied = Zone.objects.create(name='Same range', cidrs=['10.1.0.0/16'], auto_assign=True)
        expected = min(precise.pk, tied.pk, key=str)
        self.assertEqual(self.create_asset(name='tie').zone_id, expected)

    def test_updates_and_enabling_subscription_do_not_reassign_existing_assets(self):
        asset = self.create_asset(address='192.0.2.1')
        asset.address = '10.1.2.3'
        asset.save()
        self.assertIsNone(asset.zone_id)
        self.zone.save()
        asset.refresh_from_db()
        self.assertIsNone(asset.zone_id)

    def test_bulk_create_uses_matching_and_preserves_explicit_assignments(self):
        explicit = Zone.objects.create(name='Bulk explicit')
        assets = [
            Asset(name='bulk-match', address='10.1.2.3', platform=self.platform),
            Asset(name='bulk-miss', address='192.0.2.1', platform=self.platform),
            Asset(name='bulk-explicit', address='10.1.2.4', platform=self.platform, zone=explicit),
        ]
        Asset.objects.bulk_create(assets, batch_size=2)
        self.assertEqual([a.zone_id for a in assets], [self.zone.pk, None, explicit.pk])
        for asset in assets:
            expected = asset.zone_id
            asset.refresh_from_db()
            self.assertEqual(asset.zone_id, expected)

    def test_creation_in_root_context_uses_the_asset_organization(self):
        with tmp_to_root_org():
            other_org = Organization.objects.create(name='Other CIDR org')
            Zone.objects.create(name='Other match', org_id=other_org.id, cidrs=['10.1.2.3/32'], auto_assign=True)
            asset = self.create_asset(name='root-created', org_id=self.zone.org_id)
        self.assertEqual(asset.zone_id, self.zone.pk)

    def test_filter_supports_ipv6_large_ranges_and_excludes_current_zone_and_gateways(self):
        self.zone.auto_assign = False
        self.zone.save()
        ipv4 = self.create_asset(name='v4', address='192.0.2.255')
        ipv6 = self.create_asset(name='v6', address='2001:db8::1')
        self.create_asset(name='dns', address='example.com')
        self.create_asset(name='already-added', address='192.0.2.1', zone=self.zone)
        gateway_platform = Platform.objects.create(name='Gateway-filter', type='linux', category='host')
        Host.objects.create(name='gateway', address='192.0.2.2', platform=gateway_platform)
        filters = AssetFilterSet({
            'cidrs': '0.0.0.0/0,::/0', 'exclude_zone': str(self.zone.id), 'is_gateway': 'false',
        }, queryset=Asset.objects.all())
        self.assertTrue(filters.is_valid(), filters.errors)
        self.assertEqual(set(filters.qs.values_list('id', flat=True)), {ipv4.pk, ipv6.pk})
        with self.assertRaises(ValidationError):
            AssetFilterSet({'cidrs': 'invalid'}, queryset=Asset.objects.all()).qs

    def test_filter_does_not_include_other_organizations(self):
        asset = self.create_asset()
        with tmp_to_root_org():
            other_org = Organization.objects.create(name='Other filter org')
            self.create_asset(name='foreign', org_id=other_org.id)
        matches = AssetFilterSet({'cidrs': '10.0.0.0/8'}, queryset=Asset.objects.all()).qs
        self.assertEqual(list(matches.values_list('pk', flat=True)), [asset.pk])

    def test_manual_assignment_requires_asset_change_permission(self):
        asset = self.create_asset()
        request = APIRequestFactory().patch('/api/v1/assets/assets/', [
            {'id': str(asset.pk), 'zone': None},
        ], format='json')
        user = User(username='read-only')
        force_authenticate(request, user)
        view = AssetViewSet.as_view({'patch': 'partial_bulk_update'}, permission_classes=[RBACPermission])
        with patch.object(user, 'has_perms', return_value=False) as has_perms:
            with transaction.atomic():
                response = view(request)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(set(has_perms.call_args.args[0]), {'assets.change_asset'})
        asset.refresh_from_db()
        self.assertEqual(asset.zone_id, self.zone.pk)

    def test_manual_filter_and_assignment_work_without_subscription(self):
        self.zone.auto_assign = False
        self.zone.cidrs = []
        self.zone.save()
        original = Zone.objects.create(name='Original')
        selected = self.create_asset(name='selected', zone=original)
        untouched = self.create_asset(name='untouched', address='192.0.2.1')
        factory = APIRequestFactory()
        url = f'/api/v1/assets/assets/?cidrs=10.0.0.0/8&is_gateway=0&exclude_zone={self.zone.pk}'
        request = factory.patch(url, [{'id': str(selected.pk), 'zone': str(self.zone.pk)}], format='json')
        force_authenticate(request, User(username='cidr-test'))
        view = AssetViewSet.as_view({'patch': 'partial_bulk_update'}, permission_classes=[])
        response = view(request)
        self.assertEqual(response.status_code, 200, response.data)
        selected.refresh_from_db()
        untouched.refresh_from_db()
        self.assertEqual(selected.zone_id, self.zone.pk)
        self.assertIsNone(untouched.zone_id)
        self.zone.refresh_from_db()
        self.assertEqual(self.zone.cidrs, [])
