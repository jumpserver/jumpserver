项目骨架
--------

说明如下：

::

    .
    ├── config-example.py               // 配置文件样例
    ├── docs                            // 所有 DOC 文件放到该目录
    │   └── README.md
    ├── LICENSE
    ├── README.md
    ├── install                         // 安装说明
    ├── logs                            // 日志目录
    ├── apps                            // 管理后台目录，也是各 APP 所在目录
    │   └── assets                      // APP 目录
    │   │   ├── admin.py
    │   │   ├── apps.py                 // 新版本 Django APP 设置文件
    │   │   ├── api.py                  // API 文件
    │   │   ├── __init__.py             // 对外暴露的接口，放到该文件中，方便别的 APP 引用
    │   │   ├── migrations              // Models Migrations 版本控制目录
    │   │   │   └── __init__.py
    │   │   ├── models.py               // 数据模型目录
    │   │   ├── static                  // APP 下静态资源目录,如果需要
    │   │   │   └── assets              // 多一层目录，防止资源重名
    │   │   │       └── some_image.png
    │   │   ├── templates               // APP 下模板目录
    │   │   │   └── assets              // 多一层目录，防止资源重名
    │   │   │       └── asset_list.html
    │   │   ├── templatetags            // 模板标签目录
    │   │   ├── tests.py                // 测试用例文件
    │   │   ├── urls.py                 // Urlconf 文件
    │   │   ├── utils.py                // 将 Views 和 API 可复用的代码放在这里, API 和 Views 只是请求和返回不同
    │   │   └── views.py                // Views 文件
    │   ├── common
    │   │   ├── templatetags            // 通用 Template Tag
    │   │   ├── utils.py                // 通用的函数方法
    │   │   └── views.py
    │   ├── fixtures                    // 初始化数据目录
    │   │   ├── init.json               // 初始化项目数据库
    │   │   └── fake.json               // 生成大量测试数据
    │   ├── jumpserver                  // 项目设置目录
    │   │    ├── __init__.py
    │   │    ├── settings.py            // 项目设置文件
    │   │    ├── urls.py                // 项目入口 Urlconf
    │   │    └── wsgi.py
    │   ├── manage.py
    │   ├── static                      // 项目静态资源目录
    │   ├── i18n                        // 项目多语言目录
    │   └── templates                   // 项目模板目录