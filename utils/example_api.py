#!/usr/bin/env python
import requests

# 私有token页面上目前不允许创建，只能后台生成，见 https://docs.jumpserver.org/zh/master/dev/rest_api/
private_token = '10659d70a223235b8f76d45a3023eca1147488d7'


def do_request(url, data=None, method='get', params=None, org_id=''):
    authorization = 'Token {}'.format(private_token)
    headers = {'Authorization': authorization, 'Content-Type': 'application/json'}
    if org_id:
        headers['X-JMS-ORG'] = org_id
    resp = requests.request(method=method, url=url, data=data, params=params, headers=headers)
    return resp


def get_assets_list():
    url = 'http://localhost:8080/api/v1/assets/assets/?limit=10'
    resp = do_request(url)
    print(resp.status_code)
    print(resp.json())
    print(resp)


if __name__ == '__main__':
    get_assets_list()