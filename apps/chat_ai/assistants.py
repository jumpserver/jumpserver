from dataclasses import dataclass


ASSET_OPERATIONS = frozenset({
    'assets_assets_list',
    'assets_assets_retrieve',
    'assets_categories_list',
    'assets_hosts_list',
    'assets_hosts_retrieve',
    'assets_nodes_assets_list',
    'assets_nodes_list',
    'assets_nodes_retrieve',
    'assets_platforms_list',
    'assets_platforms_retrieve',
    'assets_protocols_list',
})

SESSION_AUDIT_OPERATIONS = frozenset({
    'audits_activities_list',
    'audits_login_logs_list',
    'audits_login_logs_retrieve',
    'audits_my_login_logs_list',
    'audits_my_login_logs_retrieve',
    'audits_operate_logs_list',
    'audits_operate_logs_retrieve',
    'audits_service_access_logs_list',
    'audits_service_access_logs_retrieve',
    'audits_tickets_list',
    'audits_tickets_retrieve',
    'terminal_commands_list',
    'terminal_commands_retrieve',
    'terminal_sessions_list',
    'terminal_sessions_retrieve',
    'terminal_tasks_list',
    'terminal_tasks_retrieve',
})

OPS_OPERATIONS = frozenset({
    'audits_job_logs_list',
    'audits_job_logs_retrieve',
    'audits_jobs_list',
    'audits_jobs_retrieve',
    'ops_jobs_list',
    'ops_jobs_retrieve',
    'ops_tasks_list',
    'ops_tasks_retrieve',
    'terminal_components_metrics_retrieve',
    'terminal_terminals_list',
    'terminal_terminals_retrieve',
})

DIAGNOSTIC_OPERATIONS = ASSET_OPERATIONS | SESSION_AUDIT_OPERATIONS | OPS_OPERATIONS


@dataclass(frozen=True)
class AssistantProfile:
    key: str
    name: str
    description: str
    instructions: str
    operation_ids: frozenset | None = None
    full_access: bool = False
    starter_prompts: tuple = ()

    def as_dict(self):
        return {
            'key': self.key,
            'name': self.name,
            'description': self.description,
            'scope': (
                'full_access' if self.full_access
                else 'global_allowlist' if self.operation_ids is None
                else 'fixed'
            ),
            'capabilities': sorted(self.operation_ids or ()),
            'starter_prompts': list(self.starter_prompts),
        }


ASSISTANTS = {
    'general': AssistantProfile(
        key='general',
        name='JumpServer assistant',
        description='General JumpServer questions and all permitted Core operations.',
        instructions=(
            'Act as a general JumpServer assistant with full Core operation access. Prefer read-only inspection '
            'before proposing any change. All write operations require explicit user approval. '
            'When data is incomplete, state what was checked and what remains unknown.'
        ),
        full_access=True,
        starter_prompts=(
            'Summarize the current JumpServer environment.',
            'Check recent operational exceptions that I am allowed to view.',
        ),
    ),
    'asset': AssistantProfile(
        key='asset',
        name='Asset assistant',
        description='Asset, node, platform, and protocol inspection.',
        instructions=(
            'Focus on assets, nodes, platforms, and protocols. Compare returned records carefully and present '
            'important identifiers, status, address, platform, and node placement in a compact structure.'
        ),
        operation_ids=ASSET_OPERATIONS,
        starter_prompts=(
            'List recently updated assets and highlight incomplete platform information.',
            'Compare assets under the selected nodes.',
        ),
    ),
    'session_audit': AssistantProfile(
        key='session_audit',
        name='Session audit assistant',
        description='Session, command, login, access, and operation audit diagnosis.',
        instructions=(
            'Focus on sessions and audits. Build a time-ordered explanation from session, command, login, '
            'service-access, and operation records. Never infer an event that is absent from the returned data.'
        ),
        operation_ids=SESSION_AUDIT_OPERATIONS,
        starter_prompts=(
            'Analyze recent failed logins and show the supporting records.',
            'Build a timeline for the selected session and its commands.',
        ),
    ),
    'ops': AssistantProfile(
        key='ops',
        name='Operations assistant',
        description='Job, task, component, and terminal health diagnosis.',
        instructions=(
            'Focus on jobs, tasks, component metrics, and terminal health. Identify failed or stale executions, '
            'include relevant timestamps and status values, and recommend the smallest safe follow-up check.'
        ),
        operation_ids=OPS_OPERATIONS,
        starter_prompts=(
            'Find recent failed jobs and summarize their execution status.',
            'Check terminal and component health and highlight anomalies.',
        ),
    ),
}


def get_assistant(key):
    return ASSISTANTS.get(str(key or 'general'), ASSISTANTS['general'])


def list_assistants():
    return [profile.as_dict() for profile in ASSISTANTS.values()]
