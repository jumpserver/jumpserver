# Python 示例
# pip install requests drf-httpsig
import datetime
import json

import requests
from httpsig.requests_auth import HTTPSignatureAuth


def get_auth(KeyID, SecretID):
    signature_headers = ['(request-target)', 'accept', 'date']
    auth = HTTPSignatureAuth(key_id=KeyID, secret=SecretID, algorithm='hmac-sha256', headers=signature_headers)
    return auth


def get_user_info(jms_url, auth):
    url = jms_url + '/api/v1/users/users/?limit=1'
    gmt_form = '%a, %d %b %Y %H:%M:%S GMT'
    headers = {
        'Accept': 'application/json',
        'X-JMS-ORG': '00000000-0000-0000-0000-000000000002',
        'Date': datetime.datetime.utcnow().strftime(gmt_form)
    }

    response = requests.get(url, auth=auth, headers=headers)
    print(json.loads(response.text))


if __name__ == '__main__':
    jms_url = 'http://localhost:8080'
    KeyID = '0753098d-810c-45fb-b42c-b27077147933'
    SecretID = 'a58d2530-d7ee-4390-a204-3492e44dde84'
    auth = get_auth(KeyID, SecretID)
    get_user_info(jms_url, auth)
