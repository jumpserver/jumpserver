import json
import os
import subprocess
import sys
from pathlib import Path
from unittest import TestCase


LIMITS = ('MCP_DCR_REGISTRATIONS_PER_MINUTE',)
SETTINGS_PROBE = '''
import json
import sys
from unittest.mock import patch

from jumpserver.conf import Config, ConfigManager

config = Config({
    'SECRET_KEY': 'mcp-settings-test-key',
    'BOOTSTRAP_TOKEN': 'mcp-settings-test-token',
    **json.loads(sys.stdin.read()),
})
with patch.object(ConfigManager, 'load_user_config', return_value=config):
    from jumpserver import settings

print(json.dumps([settings.MCP_DCR_REGISTRATIONS_PER_MINUTE]))
'''


class MCPSettingsTests(TestCase):
    def probe(self, overrides=None, environment=None):
        env = {key: value for key, value in os.environ.items() if key not in LIMITS}
        return subprocess.run(
            [sys.executable, '-c', SETTINGS_PROBE], input=json.dumps(overrides or {}),
            cwd=Path(__file__).resolve().parents[2], env={**env, **(environment or {})},
            capture_output=True, text=True, timeout=30,
        )

    def test_defaults_and_deployment_overrides(self):
        overrides = dict(zip(LIMITS, (90,)))
        for config, environment, expected in (
            ({}, {}, [30]),
            (overrides, {}, [90]),
            ({}, {key: str(value) for key, value in overrides.items()}, [90]),
        ):
            with self.subTest(config=config, environment=environment):
                result = self.probe(config, environment)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(json.loads(result.stdout), expected)

    def test_invalid_limits_fail_at_startup(self):
        for key, value in (
            ('MCP_DCR_REGISTRATIONS_PER_MINUTE', -1),
            ('MCP_DCR_REGISTRATIONS_PER_MINUTE', True),
            ('MCP_DCR_REGISTRATIONS_PER_MINUTE', 1.5),
            ('MCP_DCR_REGISTRATIONS_PER_MINUTE', 0),
        ):
            with self.subTest(key=key, value=value):
                result = self.probe({key: value})
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(f'{key} must be an integer >= 1', result.stderr)
        result = self.probe(environment={'MCP_DCR_REGISTRATIONS_PER_MINUTE': 'unlimited'})
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('MCP_DCR_REGISTRATIONS_PER_MINUTE must be an integer >= 1', result.stderr)
