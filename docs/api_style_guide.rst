REST API规范约定
----------------

这里仅考虑 REST API 的基本情况。参考

`RESTful API 设计指南`_

`Github API 文档`_

协议
~~~~

API 与用户的通信协议，总是使用 HTTPS 协议。

域名
~~~~

这版 API 相对简单, 没有前后端分离, 没有独立 APP, 所以放在主域名下

::

    https://example.org/api/

版本
~~~~

将 API 的版本号放入 URL 中，由于一个项目多个 APP 所以 Jumpserver 使用以下风格，将版本号放到 APP 后面

::

    https://example.com/api/:app:/:version:/:resource:
    https://example.com/api/assets/v1.0/assets [GET, POST]
    https://example.com/api/assets/v1.0/assets/1 [GET, PUT, DELETE]

路径
~~~~

路径又称“终点”（endpoint），表示 API 的具体网址。
在 RESTful 架构中，每个网址代表一种资源（Resource），所以网址中不能有动词，只能有名词，而且所用的名词往往与数据库的表格名对应。一般来说，数据库中的表都是同种记录的“集合”（Collection），所以 API 中的名词也应该使用复数。
举例来说 Cmdb 中的 Assets 列表, IDC 列表。

::

    https://example.com/api/:app:/:version:/:resource:

    https://example.com/api/assets/v1.0/assets [GET, POST]
    https://example.com/api/assets/v1.0/assets/1 [GET, PUT, DELETE]
    https://example.com/api/assets/v1.0/idcs [GET, POST]

一般性的增删查改（CRUD）API，完全使用 HTTP Method 加上 URL 提供的语义，URL 中的可变部分（比如上面提到的），一般用来传递该API操作的核心实体对象的唯一 ID，如果有更多的参数需要提供，GET 方法请使用 URL Parameter（例如：“?client_id=xxxxx&app_id=xxxxxx”)，PUT/POST/DELETE 方法请使用请求体传递参数。

HTTP Method
~~~~~~~~~~~

对于资源的具体操作类型，由 HTTP 动词表示。

常用的HTTP动词有下面五个（括号里是对应的 SQL 命令）。

-  GET（SELECT）：从服务器取出资源（一项或多项）。
-  POST（CREATE）：在服务器新建一个资源。
-  PUT（UPDATE）：在服务器更新资源（客户端提供改变后的完整资源, 幂等
-  PATCH（UPDATE）：在服务器更新资源（客户端提供改变的属性）。
-  DELETE（DELETE）：从服务器删除资源。

.. _RESTful API 设计指南: http://www.ruanyifeng.com/blog/2014/05/restful_api.html
.. _Github API 文档: https://developer.github.com/v3/


过滤信息
~~~~~~~~

常见参数约定

::

    ?keyword=localhost 模糊搜索
    ?limit=10：指定返回记录的数量
    ?offset=10：指定返回记录的开始位置。
    ?page=2&per_page=100：指定第几页，以及每页的记录数。
    ?sort=name&order=asc：指定返回结果按照哪个属性排序，以及排序顺序。
    ?asset_id=1：指定筛选条件

状态码
~~~~~~

服务器向用户返回的状态码和提示信息，常见的有以下一些（方括号中是该状态码对应的HTTP动词）。

-  200 OK - [GET]：服务器成功返回用户请求的数据，该操作是幂等的（Idempotent）。
-  201 CREATED - [POST/PUT/PATCH]：用户新建或修改数据成功。
-  202 Accepted - [*]：表示一个请求已经进入后台排队（异步任务）
-  204 NO CONTENT - [DELETE]：用户删除数据成功。
-  400 INVALID REQUEST -
   [POST/PUT/PATCH]：用户发出的请求有错误，服务器没有进行新建或修改数据的操作，该操作是幂等的。
-  401 Unauthorized - [*]：表示用户没有权限（令牌、用户名、密码错误）。
-  403 Forbidden - [*]
   表示用户得到授权（与401错误相对），但是访问是被禁止的。
-  404 NOT FOUND -
   [*]：用户发出的请求针对的是不存在的记录，服务器没有进行操作，该操作是幂等的。
-  406 Not Acceptable -
   [GET]：用户请求的格式不可得（比如用户请求JSON格式，但是只有XML格式）。
-  410 Gone -[GET]：用户请求的资源被永久删除，且不会再得到的。
-  422 Unprocesable entity - [POST/PUT/PATCH]
   当创建一个对象时，发生一个验证错误。
-  500 INTERNAL SERVER ERROR -
   [*]：服务器发生错误，用户将无法判断发出的请求是否成功。

错误处理
~~~~~~~~

如果状态码是4xx，就应该向用户返回出错信息。一般来说，返回的信息中将 error 作为键名，出错信息作为键值即可。

::

    {
        error: "Invalid API key"
    }


返回结果
~~~~~~~~

针对不同操作，服务器向用户返回的结果应该符合以下规范。

::

    GET /collection：返回资源对象的列表（数组）
    GET /collection/resource：返回单个资源对象
    POST /collection：返回新生成的资源对象
    PUT /collection/resource：返回完整的资源对象
    PATCH /collection/resource：返回完整的资源对象
    DELETE /collection/resource：返回一个空文档

Hypermedia API
~~~~~~~~~~~~~~

RESTful
API 最好做到 Hypermedia，即返回结果中提供链接，连向其他 API 方法，使得用户不查文档，也知道下一步应该做什么。
比如，当用户向 api.example.com 的根目录发出请求，会得到这样一个文档。

::

    {"link": {
      "rel":   "collection https://www.example.com/zoos",
      "href":  "https://api.example.com/zoos",
      "title": "List of zoos",
      "type":  "application/vnd.yourformat+json"
    }}

上面代码表示，文档中有一个 Link 属性，用户读取这个属性就知道下一步该调用什么 API 了。

- rel 表示这个 API 与当前网址的关系（Collection 关系，并给出该 Collection 的网址）
- href 表示 API 的路径
- title 表示 API 的标题
- type 表示返回类型

Hypermedia API 的设计被称为 HATEOAS。 Github API 就是这种设计.

其它
~~~~

（1）API 的身份认证应该使用 OAuth 2.0 框架。

（2）服务器返回的数据格式，应该尽量使用 JSON。