API 文档
==========================

::

    # 通过访问 http://Jumpserver的URL地址/docs 来访问
    # ( 如 http://192.168.244.144/docs )
    # 注：需要打开 debug 模式，jumpserver/config.py Debug=True


- 手动调用 api 的方法

::

    $ curl -X POST -H 'Content-Type: application/json' -d '{"username": "admin", "password": "admin"}' http://localhost/api/users/v1/token/  # 获取token
    {"Token":"937b38011acf499eb474e2fecb424ab3","KeyWord":"Bearer"}%  # 获取到的token

    $ curl -H 'Authorization: Bearer 937b38011acf499eb474e2fecb424ab3' -H "Content-Type:application/json" http://localhost/api/users/v1/users/
    # 使用token访问，token有效期 1小时

- python代码示例

::

    import requests
    import json
    from pprint import pprint

    def get_token():

        url = 'https://jumpserver.tk/api/users/v1/token/'

        query_args = {
            "username": "admin",
            "password": "admin"
        }

        response = requests.post(url, data=query_args)

        return json.loads(response.text)['Token']

    def get_user_info():

        url = 'https://jumpserver.tk/api/users/v1/users/'

        token = get_token()

        header_info = { "Authorization": 'Bearer ' + token }

        response = requests.get(url, headers=header_info)

        pprint(json.loads(response.text))

    get_user_info()
