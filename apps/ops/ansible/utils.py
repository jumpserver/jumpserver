from django.conf import settings


def escape_jinja2_syntax(value):
    """Keep inventory and extra vars literal when Ansible templates them."""
    if isinstance(value, dict):
        return {key: escape_jinja2_syntax(item) for key, item in value.items()}
    if isinstance(value, list):
        return [escape_jinja2_syntax(item) for item in value]
    if not isinstance(value, str):
        return value

    has_overrides = value.startswith('#jinja2:')
    if not has_overrides and not any(
            delimiter in value for delimiter in ('{{', '{%', '{#')
    ):
        return value

    # Escape every opening brace to prevent adjacent delimiters from
    # forming new expressions. A single pass also preserves literal text
    # that happens to contain the old temporary marker strings.
    escaped = value.replace('{', '{{ "{" }}')
    # Ansible parses this header before rendering and can change the
    # delimiters. Keep it literal so only the default syntax is active.
    if has_overrides:
        escaped = '{{ "#" }}' + escaped[1:]
    return escaped


def get_ansible_task_log_path(task_id, create=True):
    from ops.utils import get_task_log_path
    return get_task_log_path(
        settings.ANSIBLE_LOG_DIR, task_id, level=2, create=create
    )
