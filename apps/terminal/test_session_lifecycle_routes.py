import json
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

from django.test import SimpleTestCase
from django.utils import timezone, translation
from rest_framework.test import APIRequestFactory, force_authenticate

from audits.const import ActivityChoices
from audits.models import ActivityLog
from audits.serializers import ActivityUnionLogSerializer
from common.permissions import IsServiceAccount
from common.utils import i18n_trans
from terminal.api.session.session import SessionViewSet
from terminal.models import Session
from terminal.session_lifecycle import AssetConnectSuccess


class SessionConnectionRouteAuditTests(SimpleTestCase):
    def setUp(self):
        self.session = Session(id=uuid4(), asset='isolated-mongo', org_id=uuid4())

    def render(self, reason, language='en'):
        with translation.override(language):
            detail = AssetConnectSuccess(self.session, reason).detail()
            return i18n_trans(detail)

    def test_direct_route_is_displayed(self):
        self.assertEqual(
            self.render(json.dumps({'route': 'direct'})),
            'Connect to asset isolated-mongo success (direct connection)',
        )

    def test_gateway_route_labels_all_names_as_configured(self):
        reason = json.dumps({
            'route': 'ssh_gateway',
            'configured_gateways': [
                {'id': 'gateway-1', 'name': 'gateway one'},
                {'id': 'gateway-2', 'name': 'gateway two'},
            ],
        })
        content = self.render(reason)
        self.assertIn('SSH gateway forwarding; configured gateways: gateway one; gateway two', content)
        self.assertNotIn('selected', content)

    def test_gateway_route_without_names_still_shows_forwarding(self):
        for gateways in (None, {}, [], [None, 'unknown', {'name': False, 'id': []}]):
            with self.subTest(gateways=gateways):
                reason = json.dumps({'route': 'ssh_gateway', 'configured_gateways': gateways})
                self.assertEqual(
                    self.render(reason),
                    'Connect to asset isolated-mongo success (SSH gateway forwarding)',
                )

    def test_only_gateway_name_or_id_is_displayed(self):
        reason = json.dumps({
            'route': 'ssh_gateway',
            'password': 'DO-NOT-DISPLAY-PASSWORD',
            'token': 'DO-NOT-DISPLAY-TOKEN',
            'configured_gateways': [
                {'id': 'gateway-1', 'name': 'gateway one', 'password': 'DO-NOT-DISPLAY-SECRET'},
                {'id': 'gateway-2', 'name': None},
                {'name': {'secret': 'DO-NOT-DISPLAY-NESTED'}},
            ],
        })
        content = self.render(reason)
        self.assertIn('configured gateways: gateway one; gateway-2', content)
        self.assertNotIn('DO-NOT-DISPLAY', content)
        self.assertNotIn('password', content)

    def test_legacy_and_invalid_reasons_keep_original_content(self):
        reasons = (
            None, '', 'old component reason', '{invalid json', 'null', '[]', '123',
            'true', '"direct"', '{"route": "unknown", "password": "SECRET"}',
            '{"route": ["direct"]}', '{"password": "SECRET"}',
            '[' * 1100 + '0' + ']' * 1100,
        )
        for reason in reasons:
            with self.subTest(reason=str(reason)[:80]):
                self.assertEqual(self.render(reason), 'Connect to asset isolated-mongo success')

    def test_gateway_names_remain_single_line_and_preserve_unicode(self):
        reason = json.dumps({
            'route': 'ssh_gateway',
            'configured_gateways': [{'name': ' 测试\n网关\t甲 '}],
        })
        self.assertIn('configured gateways: 测试 网关 甲', self.render(reason))

    def test_direct_route_ignores_unrelated_gateway_and_secret_fields(self):
        reason = json.dumps({
            'route': 'direct',
            'configured_gateways': [{'name': 'DO-NOT-DISPLAY'}],
            'secret': 'DO-NOT-DISPLAY',
        })
        self.assertNotIn('DO-NOT-DISPLAY', self.render(reason))
        self.assertIn('direct connection', self.render(reason))

    def test_chinese_audit_translation(self):
        direct = self.render(json.dumps({'route': 'direct'}), language='zh-hans')
        gateway = self.render(json.dumps({
            'route': 'ssh_gateway', 'configured_gateways': [{'name': '网关甲'}],
        }), language='zh-hans')
        self.assertEqual(direct, '连接资产 isolated-mongo 成功（直连）')
        self.assertEqual(gateway, '连接资产 isolated-mongo 成功（已通过 SSH 网关转发；配置网关：网关甲）')

    def test_lifecycle_api_persists_route_detail_and_audit_serializer_displays_it(self):
        reason = json.dumps({
            'route': 'ssh_gateway', 'configured_gateways': [{'id': 'gw-1', 'name': 'gateway one'}],
            'secret': 'DO-NOT-DISPLAY',
        })
        request = APIRequestFactory().post('/', {
            'event': 'asset_connect_success', 'reason': reason,
        }, format='json')
        service_user = SimpleNamespace(
            pk=uuid4(), is_authenticated=True, is_valid=True, is_service_account=True,
        )
        force_authenticate(request, user=service_user)
        created = []

        def create_activity(**kwargs):
            activity = ActivityLog(**kwargs)
            created.append(activity)
            return activity

        view = SessionViewSet.as_view({'post': 'lifecycle_log'}, permission_classes=[IsServiceAccount])
        with (
                patch.object(SessionViewSet, 'get_object', return_value=self.session),
                patch.object(ActivityLog.objects, 'create', side_effect=create_activity),
        ):
            response = view(request, pk=str(self.session.id))
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(len(created), 1)
        activity = created[0]
        self.assertEqual(activity.type, ActivityChoices.session_log)
        self.assertEqual(activity.resource_id, self.session.id)
        self.assertNotIn('DO-NOT-DISPLAY', activity.detail)
        row = {
            'id': str(activity.id), 'datetime': timezone.now(), 'r_type': activity.type,
            'r_detail': activity.detail, 'r_detail_id': None, 'r_action': '', 'r_user': '',
        }
        with translation.override('en'):
            content = ActivityUnionLogSerializer(row).data['content']
        self.assertEqual(
            content,
            'Connect to asset isolated-mongo success (SSH gateway forwarding; configured gateways: gateway one)',
        )
