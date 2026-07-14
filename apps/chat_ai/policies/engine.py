import fnmatch
from dataclasses import dataclass

from django.conf import settings
from rest_framework.exceptions import PermissionDenied

from chat_ai.executor.sanitizer import contains_sensitive


DEFAULT_BLOCKED_PATH_PATTERNS = (
    '*password*', '*secret*', '*private-key*', '*private_key*', '*access-key*',
    '*access_key*', '*token*', '*credential*', '*backup*account*', '*account*backup*',
    '*/accounts/*', '*chat-ai*', '*/settings/*',
)


class PolicyError(PermissionDenied):
    default_code = 'chat_ai_policy_denied'


@dataclass(frozen=True)
class PolicyDecision:
    enabled: bool
    risk_level: str
    requires_approval: bool
    reason: str = ''


class PolicyEngine:
    def __init__(self, operation_scope=None, read_only=False):
        self.allowed_tags = set(getattr(settings, 'CHAT_AI_ALLOWED_TAGS', []) or [])
        self.allowed_operations = set(getattr(settings, 'CHAT_AI_ALLOWED_OPERATION_IDS', []) or [])
        self.operation_scope = set(operation_scope) if operation_scope is not None else None
        self.read_only = bool(read_only)
        self.allowed_paths = tuple(getattr(settings, 'CHAT_AI_ALLOWED_PATHS', []) or ())
        configured_blocked = tuple(getattr(settings, 'CHAT_AI_BLOCKED_PATHS', []) or ())
        self.blocked_paths = DEFAULT_BLOCKED_PATH_PATTERNS + configured_blocked
        self.method_policies = getattr(settings, 'CHAT_AI_METHOD_POLICIES', {}) or {}

    def _path_allowed(self, path):
        lowered = path.lower()
        if any(fnmatch.fnmatch(lowered, pattern.lower()) for pattern in self.blocked_paths):
            return False
        if self.allowed_paths and not any(fnmatch.fnmatch(path, pattern) for pattern in self.allowed_paths):
            return False
        return True

    def evaluate(self, operation):
        method_policy = self.method_policies.get(operation.method) or {}
        risk_level = method_policy.get('risk_level', operation.risk_level)
        requires_approval = bool(method_policy.get('approval', operation.requires_approval))
        if self.read_only and operation.method != 'GET':
            return PolicyDecision(False, 'write', True, 'Background reports are read-only.')
        if operation.method == 'DELETE':
            return PolicyDecision(False, 'dangerous', True, 'DELETE operations are disabled.')
        if operation.method not in self.method_policies:
            return PolicyDecision(False, 'dangerous', True, 'HTTP method is not allowed.')
        if not method_policy.get('enabled', False):
            return PolicyDecision(False, risk_level, requires_approval, f'{operation.method} operations are disabled.')
        if not self._path_allowed(operation.path):
            return PolicyDecision(False, risk_level, requires_approval, 'Sensitive API path is blocked.')
        if self.allowed_operations and operation.operation_id not in self.allowed_operations:
            return PolicyDecision(False, risk_level, requires_approval, 'Operation is not allowlisted.')
        if self.operation_scope is not None and operation.operation_id not in self.operation_scope:
            return PolicyDecision(False, risk_level, requires_approval, 'Operation is outside this assistant scope.')
        if self.allowed_tags and not self.allowed_tags.intersection(operation.tags):
            return PolicyDecision(False, risk_level, requires_approval, 'Operation tag is not allowlisted.')
        return PolicyDecision(True, risk_level, requires_approval)

    def is_searchable(self, operation):
        return self.evaluate(operation).enabled

    def enforce(self, operation, arguments=None):
        decision = self.evaluate(operation)
        if not decision.enabled:
            raise PolicyError(decision.reason)
        if contains_sensitive(arguments or {}):
            raise PolicyError('Sensitive fields must be submitted directly to Core and cannot enter Chat AI.')
        return decision
