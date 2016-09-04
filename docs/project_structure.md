## 项目骨架

说明如下：

```
.
├── config-example.py               // 配置文件样例
├── docs                            // 所有doc文件放到该目录
│   └── README.md
├── LICENSE
├── README.md
├── install                         // 安装说明
├── logs                            // 日志目录
├── apps                            // 管理后台目录，也是各app所在目录
│   └── assets                      // app目录
│   │   ├── admin.py
│   │   ├── apps.py                 // 新版本django app设置文件
│   │   ├── api.py                  // api文件
│   │   ├── __init__.py             // 对外暴露的接口，放到该文件中，方便别的app引用
│   │   ├── migrations              // models Migrations版本控制目录
│   │   │   └── __init__.py
│   │   ├── models.py               // 数据模型目录
│   │   ├── static                  // app下静态资源目录,如果需要
│   │   │   └── assets              // 多一层目录，防止资源重名
│   │   │       └── some_image.png
│   │   ├── templates               // app下模板目录
│   │   │   └── assets              // 多一层目录，防止资源重名
│   │   │       └── asset_list.html
│   │   ├── templatetags            // 模板标签目录
│   │   ├── tests.py                // 测试用例文件
│   │   ├── urls.py                 // urlconf文件
│   │   ├── utils.py                // 将views和api可复用的代码放在这里, api和views只是请求和返回不同
│   │   └── views.py                // views文件
│   ├── common 
│   │   ├── templatetags            // 通用template tag
│   │   ├── utils.py                // 通用的函数方法
│   │   └── views.py                
│   ├── fixtures                    // 初始化数据目录
│   │   ├── init.json               // 初始化项目数据库
│   │   └── fake.json               // 生成大量测试数据
│   ├── jumpserver                  // 项目设置目录
│   │    ├── __init__.py
│   │    ├── settings.py            // 项目设置文件
│   │    ├── urls.py                // 项目入口urlconf
│   │    └── wsgi.py
│   ├── manage.py
│   ├── static                      // 项目静态资源目录
│   ├── static                      // 项目多语言目录
│   └── templates                   // 项目模板目录
```
