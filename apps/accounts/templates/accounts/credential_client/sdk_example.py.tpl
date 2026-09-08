import time
import requests
from jms_pam import JumpServerPAMClient

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
