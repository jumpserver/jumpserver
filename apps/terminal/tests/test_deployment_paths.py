import shutil
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from ansible.parsing.dataloader import DataLoader
from ansible.template import Templar
from django.test import SimpleTestCase, override_settings

from ops.ansible.runner import SuperPlaybookRunner
from terminal.automations.deploy_app_provider import DeployAppProviderManager


class DeploymentPathTests(SimpleTestCase):
    def test_offline_files_are_resolved_in_the_executor_task_directory(self):
        with tempfile.TemporaryDirectory() as directory, override_settings(ANSIBLE_DIR=directory):
            root = Path(directory).resolve()
            resources = {
                'panda': {'file': str(root / 'core/offline/panda.tar')},
                'docker': {'file': str(root / 'core/offline/docker.tar.gz'),
                           'service': str(root / 'core/offline/docker.service')},
            }
            for publication in (False, True):
                with self.subTest(publication=publication):
                    app = SimpleNamespace(image_name='test/app:1')
                    provider = SimpleNamespace(id='provider', deploy_options={'PANDA_IMAGE': 'test/panda:1'})
                    deployment = SimpleNamespace(provider=provider, publication_id='app' if publication else None,
                                                 publication=SimpleNamespace(app=app))
                    manager = DeployAppProviderManager(deployment)
                    with patch('terminal.automations.deploy_app_provider.stage_resources', return_value=resources), \
                            patch('terminal.automations.deploy_app_provider.stage_image_archives', return_value={
                                'amd64': {'file': str(root / 'core/offline/app.tar')},
                            }), patch.object(manager, 'get_access_key', return_value='test-only'):
                        playbook = manager.generate_playbook()
                    runner = SuperPlaybookRunner(
                        inventory='', playbook=playbook, project_dir=manager.run_dir,
                        safety_mode='playbook_unsafe',
                    )
                    runner.copy_playbook()
                    runner.prepare_safe_inputs()
                    remote = root / f'executor-{publication}'
                    shutil.copytree(manager.run_dir, remote)
                    (remote / 'offline').mkdir()
                    for name in ('panda.tar', 'docker.tar.gz', 'docker.service', 'app.tar'):
                        (remote / 'offline' / name).write_text(name)
                    shutil.rmtree(manager.run_dir)
                    loader = DataLoader()
                    play = loader.load_from_file(str(remote / 'project/main.yml'))[0]
                    variables = {**play['vars'], 'playbook_dir': str(remote / 'project')}
                    if publication:
                        variables['app_image_resource'] = variables['APP_IMAGE_RESOURCES']['amd64']
                    templar = Templar(loader=loader, variables=variables)
                    tasks = list(play['tasks'])
                    sources = []
                    while tasks:
                        task = tasks.pop()
                        tasks.extend(task.get('block', []))
                        source = task.get('ansible.builtin.copy', {}).get('src')
                        if source:
                            path = Path(templar.template(source)).resolve()
                            self.assertEqual(path.parent, remote / 'offline')
                            self.assertEqual(path.read_text(), path.name)
                            sources.append(path.name)
                    self.assertCountEqual(sources, ['app.tar'] if publication else [
                        'panda.tar', 'docker.tar.gz', 'docker.service',
                    ])
