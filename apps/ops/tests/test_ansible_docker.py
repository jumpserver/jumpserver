import filecmp
import os
from tempfile import TemporaryDirectory

from django.conf import settings
from django.test import SimpleTestCase, override_settings

from ops.ansible.docker import prepare_isolated_ansible_runtime


class PrepareIsolatedAnsibleRuntimeTest(SimpleTestCase):
    @override_settings(ANSIBLE_DOCKER_ENABLED=True)
    def test_stages_current_custom_modules_and_module_utils(self):
        with TemporaryDirectory() as project_dir:
            envvars = prepare_isolated_ansible_runtime(project_dir)

            runtime_apps_dir = os.path.join(
                project_dir, 'jms_runtime', 'apps'
            )
            runtime_ansible_dir = os.path.join(
                runtime_apps_dir, 'libs', 'ansible'
            )
            source_ansible_dir = os.path.join(
                settings.APPS_DIR, 'libs', 'ansible'
            )

            self.assertEqual(
                envvars['ANSIBLE_CONFIG'],
                os.path.join(project_dir, 'ansible.cfg'),
            )
            self.assertEqual(
                envvars['ANSIBLE_LIBRARY'],
                os.pathsep.join((
                    os.path.join(runtime_ansible_dir, 'modules'),
                    os.path.join(project_dir, 'project', 'modules'),
                    os.path.join(project_dir, 'modules'),
                )),
            )
            self.assertEqual(envvars['PYTHONPATH'], runtime_apps_dir)

            for relative_path in (
                'modules/mongodb_user.py',
                'modules/mssql_script.py',
                'modules/postgresql_login_ping.py',
                'modules_utils/mongodb_client.py',
            ):
                self.assertTrue(filecmp.cmp(
                    os.path.join(source_ansible_dir, relative_path),
                    os.path.join(runtime_ansible_dir, relative_path),
                    shallow=False,
                ))

    @override_settings(ANSIBLE_DOCKER_ENABLED=False)
    def test_does_not_stage_runtime_without_docker_isolation(self):
        with TemporaryDirectory() as project_dir:
            self.assertEqual(
                prepare_isolated_ansible_runtime(project_dir), {}
            )
            self.assertFalse(os.listdir(project_dir))
