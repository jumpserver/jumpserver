API 文档
==========================

::

    # 通过访问 http://Jumpserver的URL地址/docs 来访问
    # ( 如 http://192.168.244.144/docs )
    # 注：需要打开 debug 模式，jumpserver/config.py Debug=True

手动调用 api 的方法

::

    $ curl -X POST -d '{"username": "admin", "password": "admin"}' http://localhost/api/users/v1/token/  # 获取token
    {"Token":"937b38011acf499eb474e2fecb424ab3","KeyWord":"Bearer"}%  # 获取到的token
    $ curl -H 'Authorization: Bearer 937b38011acf499eb474e2fecb424ab3' -H "Content-Type:application/json" http://localhost/api/users/v1/users/
    # 使用token访问，token有效期 1小时
