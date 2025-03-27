import os
import requests
from httpsig.requests_auth import HTTPSignatureAuth
import datetime


def test_drf_ak():
    KEY_ID = os.environ.get('KEY_ID') or ''
    SECRET = os.environ.get('KEY_SECRET') or ''

    signature_headers = ['(request-target)', 'date']
    now = datetime.datetime.now()
    headers = {
      'Host': 'localhost:8000',
      'Accept': 'application/json',
      'Date': now.strftime('%a, %d %b %Y %H:%M:%S GMT'),
    }
    
    # url = 'http://localhost:8080/api/v1/assets/assets/?limit=100'
    url = 'http://localhost:8080/api/v1/users/users/?limit=100'
    
    auth = HTTPSignatureAuth(key_id=KEY_ID, secret=SECRET,
                           algorithm='hmac-sha256',
                           headers=signature_headers)
    req = requests.get(url, auth=auth, headers=headers)
    print(req.content)


if __name__ == '__main__':
    test_drf_ak()
