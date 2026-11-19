import os

client_options = {
    'endpoint': {{ endpoint|safe }},
    'app_id': {{ app_id|safe }},
    'app_secret': {{ app_secret|safe }},
    'org_id': {{ org_id|safe }},
}
instance_id = os.environ.get('JMS_INSTANCE_ID') or {{ instance_id|safe }}
{% if include_keys %}
credential_keys = {{ credential_keys|safe }}
confirmation_keys = {{ confirmation_keys|safe }}
{% endif %}
