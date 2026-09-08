from contextlib import nullcontext
from unittest import mock

from django.test import TestCase
from rest_framework.exceptions import ValidationError

from orgs.utils import tmp_to_builtin_org
from terminal.automations.deploy_app_provider import DeployAppProviderManager
from terminal.models import AppProviderDeployment, VirtualApp, VirtualAppPublication
from terminal.serializers import AppProviderSerializer, VirtualAppPublicationSerializer


class VirtualAppPublicationConfirmationTests(TestCase):
    image_id = 'sha256:' + '1' * 64
    previous_image_id = 'sha256:' + '2' * 64
    repo_digest = 'registry.local/app@sha256:' + '3' * 64

    def setUp(self):
        with tmp_to_builtin_org(system=1):
            provider = AppProviderSerializer(data={'host': {
                'name': 'offline-provider', 'address': '192.0.2.10',
            }})
            provider.is_valid(raise_exception=True)
            provider = provider.save()
        self.app = VirtualApp.objects.create(name='offline-app', version='2.0', image_name='app:v2')
        self.publication = VirtualAppPublication.objects.get(provider=provider, app=self.app)

    def confirm(self, digest=None, status='success'):
        # The Core worker can finish while a previously loaded report waits.
        VirtualAppPublication.objects.filter(pk=self.publication.pk).update(
            status=status, app_version=self.app.version, image_digest=digest or self.image_id,
        )

    def report(self, **data):
        serializer = VirtualAppPublicationSerializer(self.publication, data=data, partial=True)
        serializer.is_valid(raise_exception=True)
        return serializer.save()

    def assert_confirmation(self, status, digest=None):
        self.publication.refresh_from_db()
        self.assertEqual(self.publication.status, status)
        self.assertEqual(self.publication.app_version, self.app.version)
        self.assertEqual(self.publication.image_digest, digest or self.image_id)

    def test_completed_panda_pull_establishes_publication_confirmation(self):
        self.report(status='success', app_version='2.0', image_digest=self.image_id)
        self.assert_confirmation('success')

    def test_incomplete_or_invalid_success_cannot_establish_confirmation(self):
        for fields in (
            {}, {'app_version': '2.0'}, {'image_digest': self.image_id},
            {'app_version': '2.0', 'image_digest': 'sha256:invalid'},
        ):
            with self.subTest(fields=fields):
                publication = self.report(status='success', **fields)
                self.assertEqual(publication.status, 'mismatch')
                self.assertEqual(publication.app_version, '')
                self.assertEqual(publication.image_digest, '')

    def test_panda_pull_can_refresh_an_image_after_publication_is_invalidated(self):
        for status in ('pending', 'mismatch', 'failed'):
            with self.subTest(status=status):
                self.confirm(self.previous_image_id)
                self.report(status=status, app_version='2.0', image_digest=self.previous_image_id)
                self.assert_confirmation(status, self.previous_image_id)
                self.report(status='success', app_version='2.0', image_digest=self.image_id)
                self.assert_confirmation('success')

    def test_matching_reports_preserve_confirmation_and_allow_recovery(self):
        self.confirm()
        for status in ('pending', 'mismatch', 'failed', 'success'):
            with self.subTest(status=status):
                self.report(status=status, app_version='2.0', image_digest=self.image_id)
                self.assert_confirmation(status)

    def test_same_version_stale_reports_cannot_overwrite_new_image(self):
        self.confirm(self.previous_image_id)
        self.publication.refresh_from_db()
        self.confirm()
        for status in ('success', 'pending', 'mismatch', 'failed'):
            with self.subTest(status=status), self.assertRaises(ValidationError):
                self.report(status=status, app_version='2.0', image_digest=self.previous_image_id)
            self.assert_confirmation('success')

    def test_incomplete_reports_cannot_erase_or_restore_confirmation(self):
        self.confirm(status='failed')
        for fields in (
            {}, {'app_version': '2.0'}, {'image_digest': self.image_id},
            {'app_version': '2.0', 'image_digest': ''},
        ):
            with self.subTest(fields=fields):
                self.report(status='success', **fields)
                self.assert_confirmation('failed')

    def test_old_or_empty_version_cannot_erase_confirmation(self):
        self.confirm()
        for version in ('1.0', ''):
            with self.subTest(version=version), self.assertRaises(ValidationError):
                self.report(status='failed', app_version=version, image_digest='')
            self.assert_confirmation('success')

    def test_verified_legacy_digest_migrates_once(self):
        self.confirm(self.repo_digest)
        self.report(status='success', app_version='2.0', image_digest=self.image_id)
        self.assert_confirmation('success')
        with self.assertRaises(ValidationError):
            self.report(status='success', app_version='2.0', image_digest=self.repo_digest)
        self.assert_confirmation('success')

    def test_legacy_digest_requires_success_with_valid_image_id(self):
        self.confirm(self.repo_digest)
        for status, digest in (('failed', self.image_id), ('success', 'sha256:invalid')):
            with self.subTest(status=status, digest=digest), self.assertRaises(ValidationError):
                self.report(status=status, app_version='2.0', image_digest=digest)
            self.assert_confirmation('success', self.repo_digest)

    def test_unmanaged_provider_retains_publication_compatibility(self):
        self.publication.provider.host = None
        self.publication.provider.save(update_fields=['host'])
        self.report(status='success', app_version='2.0', image_digest=self.image_id)
        self.assert_confirmation('success')

    @mock.patch('terminal.automations.deploy_app_provider.safe_db_connection', new=nullcontext)
    def test_late_ssh_result_cannot_overwrite_a_completed_panda_pull(self):
        for outcome in ('success', 'failed', 'error'):
            with self.subTest(outcome=outcome):
                self.confirm(self.previous_image_id, status='pending')
                deployment = AppProviderDeployment.objects.create(
                    provider=self.publication.provider, publication=self.publication,
                )

                def finish_pull(*args, **kwargs):
                    self.report(status='success', app_version='2.0', image_digest=self.image_id)
                    if outcome == 'error':
                        raise RuntimeError('SSH verification failed')
                    status = 'successful' if outcome == 'success' else outcome
                    return mock.Mock(status=status, result={'ok': {'provider': {'image': {'res': {
                        'ansible_stats': {'data': {'virtual_app_image': {
                            'name': self.app.image_name, 'version': self.app.version,
                            'id': self.previous_image_id,
                        }}},
                    }}}}})

                with mock.patch.object(
                    DeployAppProviderManager, 'generate_inventory', return_value='/tmp/inventory'
                ), mock.patch.object(
                    DeployAppProviderManager, 'generate_playbook', return_value='/tmp/playbook'
                ), mock.patch('terminal.automations.deploy_app_provider.SuperPlaybookRunner') as runner:
                    runner.return_value.run.side_effect = finish_pull
                    DeployAppProviderManager(deployment).run()
                deployment.refresh_from_db()
                self.assertEqual(deployment.status, outcome)
                self.assert_confirmation('success')
