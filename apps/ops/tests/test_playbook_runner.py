from pathlib import Path
from tempfile import TemporaryDirectory

from django.test import SimpleTestCase

from ops.ansible.runner import PlaybookRunner, SuperPlaybookRunner


class PlaybookStagingTests(SimpleTestCase):
    def setUp(self):
        directory = TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.source = self.root / 'source'
        self.private = self.root / 'job'
        self.project = self.private / 'project'
        self.write_source('main.yml', '- hosts: all\n  tasks: []\n')

    def write_source(self, name, content='fixture\n'):
        path = self.source / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        return path

    def stage(self, runner_class=PlaybookRunner):
        runner = runner_class('', str(self.source / 'main.yml'), str(self.private))
        runner.copy_playbook()
        self.assertEqual(runner.playbook, 'main.yml')

    def test_preserves_scripts_and_files_for_remote_tasks(self):
        names = (
            'hello.sh', 'helper.py', 'files/install.bash', 'files/setup.exe',
            'files/helper.dll', 'files/helper.so', 'roles/demo/files/check.py',
            'roles/demo/tasks/main.yml',
        )
        for name in names:
            self.write_source(name)

        self.stage()

        for name in names:
            with self.subTest(name=name):
                self.assertEqual((self.project / name).read_bytes(), (self.source / name).read_bytes())

    def test_filters_plugins_and_configuration_and_removes_stale_files(self):
        names = (
            'ansible.cfg', '.ansible.cfg', 'action_plugins/custom.py',
            'lookup_plugins/custom.py', 'httpapi_plugins/custom.py',
            'callback_plugins/custom.py', 'filter_plugins/custom.py',
            'modules/custom.py', 'library/custom.py',
            'roles/demo/filter_plugins/custom.py',
            'collections/ansible_collections/demo/custom/__init__.py',
        )
        for name in names:
            self.write_source(name)
        self.project.mkdir(parents=True)
        (self.project / 'obsolete.txt').write_text('stale')

        self.stage()

        for name in names:
            with self.subTest(name=name):
                self.assertFalse((self.project / name).exists())
                self.assertTrue((self.source / name).exists())
        self.assertFalse((self.project / 'obsolete.txt').exists())
        self.assertTrue((self.project / 'main.yml').is_file())

    def test_removes_links_without_reading_or_changing_their_targets(self):
        outside = self.root / 'outside'
        outside.mkdir()
        (outside / 'data.txt').write_text('outside')
        (self.source / 'file-link').symlink_to(outside / 'data.txt')
        (self.source / 'directory-link').symlink_to(outside, target_is_directory=True)

        self.stage()

        for name in ('file-link', 'directory-link'):
            self.assertFalse((self.project / name).is_symlink())
            self.assertFalse((self.project / name).exists())
            self.assertTrue((self.source / name).is_symlink())
        self.assertEqual((outside / 'data.txt').read_text(), 'outside')

    def test_filters_user_plugins_even_when_project_is_already_staged(self):
        self.source = self.project
        self.write_source('main.yml')
        self.write_source('action_plugins/custom.py')
        self.write_source('library/custom.py')
        self.write_source('ansible.cfg')
        self.write_source('files/setup.sh')

        self.stage()

        for name in ('action_plugins', 'library', 'ansible.cfg'):
            self.assertFalse((self.project / name).exists())
        self.assertTrue((self.project / 'files/setup.sh').is_file())

    def test_preserves_trusted_platform_modules_plugins_and_scripts(self):
        names = ('modules/custom.py', 'filter_plugins/custom.py', 'files/setup.sh')
        for name in names:
            self.write_source(name)
        (self.source / 'setup.sh').symlink_to(self.source / 'files/setup.sh')

        self.stage(SuperPlaybookRunner)

        for name in (*names, 'setup.sh'):
            with self.subTest(name=name):
                self.assertEqual((self.project / name).read_bytes(), (self.source / name).read_bytes())
        self.assertFalse((self.project / 'setup.sh').is_symlink())
