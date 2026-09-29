client_options = {
    'endpoint': {{ endpoint|safe }},
    'app_id': {{ app_id|safe }},
    'app_secret': {{ app_secret|safe }},
    'org_id': {{ org_id|safe }},
{% if configuration_id %}    'configuration_id': {{ configuration_id|safe }},
{% endif %}}
{% if include_keys %}
credential_keys = {{ credential_keys|safe }}
confirmation_keys = {{ confirmation_keys|safe }}
{% endif %}
