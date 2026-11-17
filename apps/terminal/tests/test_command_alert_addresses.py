from unittest.mock import patch
from uuid import uuid4

from django.test import TestCase
from django.utils import timezone
from django.utils.translation import override
from rest_framework.test import APIRequestFactory

from acls.models import CommandFilterACL, CommandGroup
from assets.models import Asset, Platform
from orgs.models import Organization
from orgs.utils import tmp_to_org
from terminal.api.session.command import InsecureCommandAlertAPI
from terminal.const import RiskLevelChoices
from terminal.models import Session
from terminal.notifications import CommandAlertMessage, CommandWarningMessage
from users.models import User


class CommandAlertAddressTests(TestCase):
    def setUp(self):
        self.org = Organization.objects.create(name='Command address tests')
        scope = tmp_to_org(self.org)
        scope.__enter__()
        self.addCleanup(scope.__exit__, None, None, None)
        self.user = User.objects.create(username='alert-reviewer', name='Reviewer')
        platform = Platform.objects.create(name='Alert database', category='database', type='mysql')
        self.asset = Asset.objects.create(name='database', address='192.0.2.55', platform=platform)
        self.session = Session.objects.create(
            asset_id=str(self.asset.pk), asset=self.asset.name,
            user=str(self.user), user_id=str(self.user.pk),
            account='root', protocol='mysql', remote_addr='2001:db8::5',
        )
        self.acl = CommandFilterACL.objects.create(name='Alert rule', action='warning')
        self.acl.reviewers.add(self.user)
        self.group = CommandGroup.objects.create(name='SELECT', content='SELECT')
        self.command = dict(
            user=str(self.user), asset=self.asset.name, input='SELECT 1',
            session=str(self.session.pk),
            org_id=str(self.org.pk), cmd_filter_acl=str(self.acl.pk), cmd_group=str(self.group.pk),
            timestamp=int(timezone.now().timestamp()), risk_level=RiskLevelChoices.warning,
        )

    def notify(self, risk_level=RiskLevelChoices.warning):
        view = InsecureCommandAlertAPI()
        request = view.initialize_request(APIRequestFactory().post(
            '/', [{**self.command, 'risk_level': risk_level}], format='json',
        ))
        with patch.object(CommandWarningMessage, 'publish_async', autospec=True) as warning, \
                patch.object(CommandAlertMessage, 'publish_async', autospec=True) as rejected:
            response = view.post(request)
        self.assertEqual(response.status_code, 200)
        publish = warning if risk_level == RiskLevelChoices.warning else rejected
        publish.assert_called_once()
        return publish.call_args.args[0]

    def test_warning_and_rejection_distinguish_asset_and_source_addresses(self):
        for level in (RiskLevelChoices.warning, RiskLevelChoices.reject):
            with self.subTest(level=level), override('en'):
                message = self.notify(level)
                self.assertEqual(message.command['_asset_address'], '192.0.2.55')
                self.assertEqual(message.command['_remote_addr'], '2001:db8::5')
                for content in (message.get_html_msg(), message.get_markdown_msg()):
                    self.assertIn('Asset address', content['message'])
                    self.assertIn('192.0.2.55', content['message'])
                    self.assertIn('Source IP', content['message'])
                    self.assertIn('2001:db8::5', content['message'])

    def test_unavailable_asset_does_not_replace_its_address_with_source_ip(self):
        for asset_id in ('', str(uuid4())):
            with self.subTest(asset_id=asset_id):
                self.session.asset_id = asset_id
                self.session.save(update_fields=['asset_id'])
                message = self.notify()
                self.assertEqual(message.command['_asset_address'], '')
                self.assertEqual(message.command['_remote_addr'], '2001:db8::5')

    def test_asset_lookup_remains_scoped_to_the_current_organization(self):
        other = Organization.objects.create(name='Another alert organization')
        Asset.objects.filter(pk=self.asset.pk).update(org_id=other.pk)
        message = self.notify()
        self.assertEqual(message.command['_asset_address'], '')
