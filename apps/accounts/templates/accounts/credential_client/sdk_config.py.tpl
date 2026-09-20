from jms_pam.common import credential
from jms_pam.common.profile import client_profile


cred = credential.Credential({{ app_id|safe }}, {{ app_secret|safe }})
profile = client_profile.ClientProfile(
    endpoint={{ endpoint|safe }},
    org_id={{ org_id|safe }},
    configuration_id={{ configuration_id|safe }},
)
credential_keys = {{ credential_keys|safe }}
