#!/bin/bash
#

function delete_oauth2_provider_applications() {
python3 ../apps/manage.py shell << EOF
from oauth2_provider.models import *
apps = Application.objects.all()
apps.delete()
print("OAuth2 Provider Applications deleted successfully!")
EOF
}

delete_oauth2_provider_applications