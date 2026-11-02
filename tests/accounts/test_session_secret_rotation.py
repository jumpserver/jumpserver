import ast
import contextlib
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import Mock, patch


ROOT = Path(__file__).resolve().parents[2]


def load_node(path, name, env, members=None):
    tree = ast.parse((ROOT / path).read_text(encoding='utf-8'))
    node = next(item for item in tree.body if getattr(item, 'name', None) == name)
    if members is not None:
        node.body = [item for item in node.body if getattr(item, 'name', None) in members]
    node.decorator_list = []
    exec(compile(ast.fix_missing_locations(ast.Module(body=[node], type_ignores=[])), str(ROOT / path), 'exec'), env)
    return env[name]


class FakeCache:
    def __init__(self):
        self.data = {}

    def add(self, key, value, timeout):
        if key in self.data:
            return False
        self.data[key] = value
        return True

    def set(self, key, value, timeout):
        self.data[key] = value

    def get(self, key, default=None):
        return self.data.get(key, default)

    def delete(self, key):
        self.data.pop(key, None)

    def iter_keys(self, pattern):
        return iter([key for key in self.data if key.startswith(pattern.rstrip('*'))])


class SessionSecretRotationTests(unittest.TestCase):
    def setUp(self):
        self.cache = FakeCache()
        cls = load_node('apps/accounts/utils.py', 'AccountSecretTaskStatus', {'cache': self.cache})
        self.queue = cls()

    def test_existing_queue_is_available_and_cleanable_after_switch_off(self):
        self.queue.set_status('account', 'queued', use_add=True)
        self.assertEqual(self.queue.get_status('account'), 'queued')
        self.queue.set_status('account', 'ready')
        self.assertEqual(self.queue.get_status('account'), 'ready')
        self.queue.clear('account')
        self.assertEqual(self.queue.get_status('account'), None)

    def test_queued_task_is_processed_when_switch_is_off(self):
        from collections import defaultdict

        self.queue.set_status('account', 'queued')
        account = types.SimpleNamespace(id='account', org_id='org', secret_type='password')
        account_model = types.SimpleNamespace(objects=types.SimpleNamespace(filter=lambda **kw: [account]))
        modules = {'accounts.models': types.SimpleNamespace(ChangeSecretAutomation=object, Account=account_model)}
        process = Mock()
        env = {
            'account_secret_task_status': self.queue,
            'ChangeSecretAccountStatus': types.SimpleNamespace(QUEUED='queued', READY='ready'),
            'defaultdict': defaultdict, 'tmp_to_org': lambda org: contextlib.nullcontext(),
            '_process_accounts': process, '_': lambda s: s,
            'AutomationTypes': types.SimpleNamespace(change_secret='change_secret'),
        }
        task = load_node('apps/accounts/tasks/push_account.py', 'change_secret_accounts_to_assets_task', env)
        with patch.dict(sys.modules, modules):
            task([], snapshot={}, trigger='delay')
        self.assertEqual(self.queue.get_status('account'), 'ready')
        self.assertEqual(process.call_count, 1)
        self.assertEqual(process.call_args.args[0], ['account'])
        self.queue.clear('account')
        self.assertIsNone(self.queue.get_status('account'))

    def test_session_end_only_enqueues_when_enabled(self):
        settings = types.SimpleNamespace(XPACK_LICENSE_IS_VALID=True, CHANGE_SECRET_AFTER_SESSION_END=False)

        class Base:
            def update(self, instance, data):
                return instance

        env = {'settings': settings, 'Base': Base}
        tree = ast.parse((ROOT / 'apps/terminal/serializers/session.py').read_text(encoding='utf-8'))
        session = next(item for item in tree.body if isinstance(item, ast.ClassDef) and item.name == 'SessionSerializer')
        update = next(item for item in session.body if isinstance(item, ast.FunctionDef) and item.name == 'update')
        cls = ast.ClassDef(name='SessionBoundary', bases=[ast.Name(id='Base', ctx=ast.Load())],
                           keywords=[], body=[update], decorator_list=[])
        exec(compile(ast.fix_missing_locations(ast.Module(body=[cls], type_ignores=[])), '<session>', 'exec'), env)
        serializer = env['SessionBoundary']()
        serializer.enqueue_change_secret_task = Mock()
        instance = types.SimpleNamespace(protocol='ssh', is_finished=False, is_success=True)
        serializer.update(instance, {'is_finished': True})
        serializer.enqueue_change_secret_task.assert_not_called()
        settings.CHANGE_SECRET_AFTER_SESSION_END = True
        serializer.update(instance, {'is_finished': True})
        serializer.enqueue_change_secret_task.assert_called_once_with(instance)
        instance.protocol = 'vnc'
        serializer.update(instance, {'is_finished': True})
        self.assertEqual(serializer.enqueue_change_secret_task.call_count, 1)

    def test_secure_mode_filters_targets_at_execution_time(self):
        settings = types.SimpleNamespace(CHANGE_AUTH_PLAN_SECURE_MODE_ENABLED=True)
        env = {'settings': settings, 'BaseAccountQuerySet': object}
        manager_class = load_node(
            'apps/accounts/automations/base/manager.py', 'BaseChangeSecretPushManager',
            {**env, 'AccountBasePlaybookManager': object}, members={'get_accounts'},
        )
        manager = manager_class()
        manager.account_ids = ['account']
        manager.secret_type = None
        accounts = Mock()
        accounts.filter.return_value = accounts
        accounts.exclude.return_value = accounts
        privileged = types.SimpleNamespace(
            username='admin', asset=types.SimpleNamespace(all_accounts=accounts),
        )
        accounts.all.return_value = accounts
        manager.get_accounts(privileged)
        accounts.exclude.assert_called_once_with(username__in=['root', 'administrator', 'admin'])
        accounts.filter.assert_any_call(privileged=False)
        accounts.reset_mock()
        settings.CHANGE_AUTH_PLAN_SECURE_MODE_ENABLED = False
        manager.get_accounts(privileged)
        accounts.exclude.assert_not_called()
        self.assertNotIn(unittest.mock.call(privileged=False), accounts.filter.call_args_list)


if __name__ == '__main__':
    unittest.main()
