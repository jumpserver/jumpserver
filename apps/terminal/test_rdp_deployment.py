from pathlib import Path
from unittest import TestCase

import yaml
from jinja2 import Environment


class RdpDeploymentTests(TestCase):
    playbook = Path(__file__).with_name('automations') / 'deploy_applet_host' / 'playbook.yml'

    def test_installer_reboot_requirement_is_handled_before_configuration(self):
        play = yaml.safe_load(self.playbook.read_text())[0]
        tasks = [task for block in play['tasks'] if 'install' in block.get('tags', [])
                 for task in block['block']]
        installer = next(task for task in tasks if task.get('register') == 'tinker_install')
        reboot = tasks[tasks.index(installer) + 1]
        self.assertIn('/NORESTART', installer['ansible.windows.win_command']['argv'])
        self.assertIn('/RESTARTEXITCODE=3010', installer['ansible.windows.win_command']['argv'])
        options = reboot['ansible.windows.win_reboot']
        self.assertGreater(options['reboot_timeout'], 0)
        self.assertLessEqual(options['reboot_timeout'], 600)
        # Keep win_reboot's default Windows logon readiness check.
        self.assertNotIn('test_command', options)
        env = Environment()
        for code, failed, needs_restart in ((0, False, False), (3010, False, True), (1, True, False)):
            with self.subTest(code=code):
                variables = {'tinker_install': {'rc': code}}
                self.assertEqual(env.compile_expression(installer['failed_when'])(**variables), failed)
                self.assertEqual(env.compile_expression(reboot['when'])(**variables), needs_restart)
        self.assertEqual([task for task in tasks[tasks.index(installer) + 1:]
                          if 'ansible.windows.win_reboot' in task], [reboot])

    def test_rdp_refresh_runs_once_after_health_before_readiness_retries(self):
        play = yaml.safe_load(self.playbook.read_text())[0]
        tasks = next(block['block'] for block in play['tasks'] if block['tags'] == ['deploy'])
        health = next(task for task in tasks if task.get('register') == '_result')
        restarts = [task for task in tasks
                    if task.get('ansible.windows.win_service', {}).get('state') == 'restarted']
        self.assertEqual(len(restarts), 1)
        restart = restarts[0]
        self.assertEqual(restart['ansible.windows.win_service']['name'], 'TermService')
        self.assertTrue(restart['ansible.windows.win_service']['force_dependent_services'])
        self.assertNotIn('until', restart)
        self.assertNotIn('retries', restart)
        self.assertNotIn('loop', restart)
        restore = tasks[tasks.index(restart) + 1]
        self.assertEqual(restore['ansible.windows.win_service']['state'], 'started')
        self.assertIn('rdp_dependents.result.Running', restore['loop'])
        self.assertIn('UmRdpService', restore['loop'])
        ready = next(task for task in tasks if task.get('register') == 'rdp_ready')
        self.assertLess(tasks.index(health), tasks.index(restart))
        self.assertLess(tasks.index(restore), tasks.index(ready))
        self.assertEqual(ready['until'], 'rdp_ready is succeeded')
        self.assertGreater(ready['retries'], 0)
        self.assertLessEqual(ready['retries'] * ready['delay'], 60)
        self.assertFalse(ready.get('ignore_errors', False))
        self.assertNotIn('Restart-Service', ready['ansible.windows.win_powershell']['script'])
