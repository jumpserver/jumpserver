### API

这里仅考虑REST API的基本情况。

#### HTTP Method

1. 读操作使用GET方法，写操作使用PUT/POST/DELETE方法，其中删除记录的操作使用DELETE方法。  
2. 使用PUT方法实现的API必须是幂等的（多次执行同样操作，结果相同）。
3. POST则是实现非幂等的接口。
4. 一般性的CRUD操作，R一般使用GET方法，C使用POST，U使用PUT方法，D使用DELETE方法。

#### URL
1. /api/为api地址的prefix
2. 每个项目的的root path后面整合的时候回指定为项目名 如: /api/assets
3. 一般性的增删查改(CRUD)API，完全使用HTTP method加上url提供的语义，url中的可变部分（比如上面提到的<role_id>）
一般用来传递该API操作的核心实体对象的唯一ID，如果有更多的参数需要提供，GET方法请使用url parameter
(例如："?client_id=xxxxx&app_id=xxxxxx")，PUT/POST/DELETE方法请使用请求体传递参数。


#### 约定

1. 分页 ?page=
2. 每页数量 ?limit=
3. 
