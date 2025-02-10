```python
import requests
import os
from datetime import datetime
from httpsig.requests_auth import HTTPSignatureAuth

API_URL = os.getenv("API_URL", "http://127.0.0.1:8080")
KEY_ID = os.getenv("API_KEY_ID", "72b0b0aa-ad82-4182-a631-ae4865e8ae0e")
KEY_SECRET = os.getenv("API_KEY_SECRET", "6fuSO7P1m4cj8SSlgaYdblOjNAmnxDVD7tr8")
ORG_ID = os.getenv("ORG_ID", "00000000-0000-0000-0000-000000000002")


class APIClient:
    def __init__(self):
        self.session = requests.Session()
        self.auth = HTTPSignatureAuth(
            key_id=KEY_ID, secret=KEY_SECRET,
            algorithm='hmac-sha256', headers=['(request-target)', 'accept', 'date', 'x-jms-org']
        )

    def get_account_secret(self, asset, account):
        url = f"{API_URL}/api/v1/accounts/integration-applications/account-secret/"
        headers = {
            'Accept': 'application/json',
            'X-JMS-ORG': ORG_ID,
            'Date': datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S GMT'),
            'X-Source': 'jms-pam'
        }
        params = {"asset": asset, "account": account}

        try:
            response = self.session.get(url, auth=self.auth, headers=headers, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"API 请求失败: {e}")
            return None


# 示例调用
if __name__ == "__main__":
    client = APIClient()
    result = client.get_account_secret(asset="ubuntu_docker", account="root")
    print(result)
```