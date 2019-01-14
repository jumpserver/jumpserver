API 文档
==========================

.. code-block:: shell

    通过访问 http://Jumpserver的URL地址/docs 来访问( 如 http://192.168.244.144/docs )
    注：需要打开 debug 模式,

    $ vi jumpserver/config.yml

    ...
    Debug=True


- 手动调用 api 的方法

.. code-block:: shell

    $ curl -X POST http://localhost/api/users/v1/auth/ -H 'Content-Type: application/json' -d '{"username": "admin", "password": "admin"}'  # 获取token
    {"token":"937b38011acf499eb474e2fecb424ab3"}  # 获取到的token

    # 如果开启了 MFA, 则返回的是 seed, 需要携带 seed 和 otp_code 再次提交一次才能获取到 token
    curl -X POST http://localhost/api/users/v1/auth/ -H 'Content-Type: application/json' -d '{"username": "admin", "password": "admin"}'
    {"code":101,"msg":"请携带seed值, 进行MFA二次认证","otp_url":"/api/users/v1/otp/auth/","seed":"629ba0935a624bd9b21e31c19e0cc8cb"}
    $ curl -X POST http://localhost/api/users/v1/otp/auth/ -H 'Content-Type: application/json' -H 'cache-control: no-cache' -d '{"seed": "629ba0935a624bd9b21e31c19e0cc8cb", "otp_code": "202123"}'
    {"token":"937b38011acf499eb474e2fecb424ab3"}
    # otp_code 为动态密码

    $ curl -H 'Authorization: Bearer 937b38011acf499eb474e2fecb424ab3' -H "Content-Type:application/json" http://localhost/api/users/v1/users/
    # 使用token访问,token有效期 1小时

- python代码示例

.. code-block:: python

    import requests
    import json
    from pprint import pprint

    def get_token():

        url = 'https://demo.jumpserver.org/api/users/v1/auth/'

        query_args = {
            "username": "admin",
            "password": "admin"
        }

        response = requests.post(url, data=query_args)

        return json.loads(response.text)['token']

    def get_user_info():

        url = 'https://demo.jumpserver.org/api/users/v1/users/'

        token = get_token()

        header_info = { "Authorization": 'Bearer ' + token }

        response = requests.get(url, headers=header_info)

        pprint(json.loads(response.text))

    get_user_info()
