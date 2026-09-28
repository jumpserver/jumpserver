from jms_pam.common import credential
from jms_pam.common.profile import client_profile


cred = credential.Credential({{ app_id|safe }}, {{ app_secret|safe }})
profile = client_profile.ClientProfile(
    endpoint={{ endpoint|safe }},
    org_id={{ org_id|safe }},
{% if configuration_id %}    configuration_id={{ configuration_id|safe }},
{% endif %}
)
{% if include_keys %}
credential_keys = {{ credential_keys|safe }}
confirmation_keys = {{ confirmation_keys|safe }}
{% endif %}
