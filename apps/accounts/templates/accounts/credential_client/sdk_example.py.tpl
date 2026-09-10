import time
import requests
from jms_pam import JumpServerPAMClient

# Set JMS_PAM_INSTANCE_ID before starting: a stable, unique ID for EACH independent
# application process/connection pool. Do not reuse one ID across workers or hosts.
# Create the SDK client inside each worker, after any process fork.

{% if notification_enabled %}
def on_event(event):
    # Replace with your application handler. No secrets are included.
    print(event['event'], event.get('key'), event.get('revision'))

{% endif %}
with JumpServerPAMClient.from_config('jms-pam.json') as client:
{% if notification_enabled %}    client.start_events(handler=on_event)
{% endif %}    while True:
        for key in {{ credential_keys|safe }}:
            try:
                credential = client.get_credential(key)
                # Connect/reload using credential.username and credential.secret.
                # Confirm ONLY after the application is using this version:
                # client.confirm_applied(credential)
            except requests.RequestException as error:
                print(error)
        time.sleep(30)
