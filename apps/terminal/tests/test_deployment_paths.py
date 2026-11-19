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
    def test_offline_files_are_resolved_in_native_and_ssh_task_directories(self):
        with tempfile.TemporaryDirectory() as directory, override_settings(ANSIBLE_DIR=directory):
            root = Path(directory).resolve()

            def stage(directory, resources):
                offline = Path(directory) / 'offline'
                offline.mkdir(parents=True)
                for resource in resources.values():
                    for key, name in resource.items():
                        (offline / name).write_text(name)
                        resource[key] = str(offline / name)
                return resources

            for publication in (False, True):
                with self.subTest(publication=publication):
                    app = SimpleNamespace(image_name='test/app:1')
                    provider = SimpleNamespace(id='provider', deploy_options={'PANDA_IMAGE': 'test/panda:1'})
                    deployment = SimpleNamespace(provider=provider, publication_id='app' if publication else None,
                                                 publication=SimpleNamespace(app=app))
                    manager = DeployAppProviderManager(deployment)
                    with patch('terminal.automations.deploy_app_provider.stage_resources',
                               side_effect=lambda directory, image: stage(directory, {
                                   'panda': {'file': 'panda.tar'},
                                   'docker': {'file': 'docker.tar.gz', 'service': 'docker.service'},
                               })), patch('terminal.automations.deploy_app_provider.stage_image_archives',
                                          side_effect=lambda app, directory: stage(directory, {
                                              'amd64': {'file': 'app.tar'},
                                          })), patch.object(manager, 'get_access_key', return_value='test-only'):
                        playbook = manager.generate_playbook()
                    runner = SuperPlaybookRunner(
                        inventory='', playbook=playbook, project_dir=manager.run_dir,
                        safety_mode='playbook_unsafe',
                    )
                    runner.copy_playbook()
                    runner.prepare_safe_inputs()
                    for relocated in (False, True):
                        with self.subTest(relocated=relocated):
                            task_dir = Path(manager.run_dir).resolve()
                            if relocated:
                                task_dir = root / f'executor-{publication}'
                                shutil.copytree(manager.run_dir, task_dir)
                                shutil.rmtree(manager.run_dir)
                            loader = DataLoader()
                            play = loader.load_from_file(str(task_dir / 'project/main.yml'))[0]
                            variables = {**play['vars'], 'playbook_dir': str(task_dir / 'project')}
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
                                    self.assertEqual(path.parent, task_dir / 'project/offline')
                                    self.assertEqual(path.read_text(), path.name)
                                    sources.append(path.name)
                            self.assertCountEqual(sources, ['app.tar'] if publication else [
                                'panda.tar', 'docker.tar.gz', 'docker.service',
                            ])
