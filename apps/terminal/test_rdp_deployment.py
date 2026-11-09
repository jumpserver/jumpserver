from pathlib import Path
from unittest import TestCase

import yaml
from jinja2 import Environment, StrictUndefined


class RdpDeploymentTests(TestCase):
    playbook = Path(__file__).with_name('automations') / 'deploy_applet_host' / 'playbook.yml'

    def test_installer_reboot_requirement_is_handled_before_configuration(self):
        play = yaml.safe_load(self.playbook.read_text())[0]
        tasks = [task for block in play['tasks'] if 'install' in block.get('tags', [])
                 for task in block['block']]
        installer = next(task for task in tasks if task.get('register') == 'tinker_install')
        rds_ready = next(task for task in tasks if task.get('register') == 'rds_ready')
        policy = next(task for task in tasks if task.get('register') == 'nla_policy')
        nla = next(task for task in tasks if task.get('ansible.windows.win_regedit', {}).get('name')
                   == 'UserAuthentication')
        self.assertLess(tasks.index(rds_ready), tasks.index(policy))
        self.assertLess(tasks.index(policy), tasks.index(nla))
        self.assertLess(tasks.index(nla), tasks.index(installer))
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

    def test_rdp_policies_are_checked_before_reinstallation(self):
        play = yaml.safe_load(self.playbook.read_text())[0]
        install = next(block for block in play['tasks']
                       if any(task.get('register') == 'tinker_install' for task in block['block']))
        tasks = install['block']
        installer = next(task for task in tasks if task.get('register') == 'tinker_install')
        self.assertIn('install', install['tags'])
        env = Environment()
        cases = (
            ({'exists': False}, True),
            ({'exists': True, 'type': 'REG_DWORD', 'value': 0}, True),
            ({'exists': True, 'type': 'REG_DWORD', 'value': 1}, False),
            ({'exists': True, 'type': 'REG_DWORD', 'value': 2}, False),
            ({'exists': True, 'type': 'REG_SZ', 'value': '0'}, False),
        )
        for register, setting in (('nla_policy', 'UserAuthentication'),
                                  ('password_prompt_policy', 'fPromptForPassword')):
            policy = next(task for task in tasks if task.get('register') == register)
            guard = tasks[tasks.index(policy) + 1]
            self.assertLess(tasks.index(guard), tasks.index(installer))
            self.assertEqual(policy['ansible.windows.win_reg_stat']['name'], setting)
            for state, expected in cases:
                with self.subTest(setting=setting, policy=state):
                    allowed = all(env.compile_expression(condition)(**{register: state})
                                  for condition in guard['ansible.builtin.assert']['that'])
                    self.assertEqual(allowed, expected)

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
        self.assertEqual(restore['ansible.windows.win_service'], {'name': 'UmRdpService', 'state': 'started'})
        self.assertNotIn('loop', restore)
        self.assertFalse(any(task.get('register') == 'rdp_dependents' for task in tasks))
        ready = next(task for task in tasks if task.get('register') == 'rdp_ready')
        for setting in ('UserAuthentication', 'fPromptForPassword'):
            task = next(task for task in tasks if task.get('ansible.windows.win_regedit', {}).get('name')
                        == setting)
            self.assertEqual(task['ansible.windows.win_regedit']['data'], 0)
            self.assertEqual(task['ansible.windows.win_regedit']['type'], 'dword')
            self.assertEqual(task['ansible.windows.win_regedit']['state'], 'present')
            self.assertNotIn('when', task)
            self.assertLess(tasks.index(health), tasks.index(task))
            self.assertLess(tasks.index(task), tasks.index(restart))
        self.assertLess(tasks.index(restore), tasks.index(ready))
        self.assertEqual(ready['until'], 'rdp_ready is succeeded')
        self.assertGreater(ready['retries'], 0)
        self.assertLessEqual(ready['retries'] * ready['delay'], 60)
        self.assertFalse(ready.get('ignore_errors', False))
        self.assertNotIn('Restart-Service', ready['ansible.windows.win_powershell']['script'])

    def test_failure_summary_keeps_error_details_and_hides_credentials(self):
        play = yaml.safe_load(self.playbook.read_text())[0]
        install = next(block for block in play['tasks']
                       if any(task.get('register') == 'tinker_install' for task in block['block']))
        deploy = next(block for block in play['tasks'] if block['tags'] == ['deploy'])
        env = Environment(undefined=StrictUndefined)
        policy = next(task for task in install['block'] if 'ansible.builtin.assert' in task and
                      'password_prompt_policy' in task['ansible.builtin.assert']['that'][0])
        detail = env.from_string(policy['ansible.builtin.assert']['fail_msg']).render(
            password_prompt_policy={'type': 'REG_DWORD', 'value': 1})
        summary = env.from_string(install['rescue'][0]['fail']['msg']).render(
            ansible_failed_task={'name': policy['name']}, ansible_failed_result={'msg': detail})
        self.assertIn(detail, summary)
        template = env.from_string(deploy['rescue'][0]['fail']['msg'])
        cases = (
            ({'msg': 'Connection refused'}, {}, 'Connection refused'),
            ({'error': [{'exception': {'message': detail}}]}, {}, detail),
            ({'error': [{}], 'msg': 'CIM query failed'}, {}, 'CIM query failed'),
            ({'error': None}, {}, 'Review the failed task output'),
            ({'msg': 'sensitive-component-key'}, {'no_log': True}, None),
            ({'error': [{'exception': {'message': 'sensitive-component-key'}}],
              '_ansible_no_log': True}, {}, None),
        )
        for result, task, expected in cases:
            with self.subTest(result=result, task=task):
                summary = template.render(ansible_failed_task={'name': 'Deployment task', **task},
                                          ansible_failed_result=result)
                if expected is None:
                    self.assertNotIn('sensitive-component-key', summary)
                    self.assertIn('hidden', summary)
                else:
                    self.assertIn(expected, summary)
