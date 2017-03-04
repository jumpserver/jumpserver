## Jumpserver
Jumpserver是一款使用Python, Django开发的开源跳板机系统, 助力互联网企业高效 用户、资产、权限、审计 管理

### 开发环境
   * Python 2.7  # 开发时需考虑兼容Python3
   * Django 1.10

### 安装
- 安装依赖库
```
   $ cd requirements
   $ sudo yum -y install `cat rpm_requirements.txt`  # CentOS/RedHat
   $ sudo apt-get  install `cat deb_requirements.txt`  # Ubuntu/Debian
```

- 安装Python依赖包

```
# 请自行安装 Python2.7 和 pip, 以下运行是以python2.7和pip2.7开始
$ pip2.7 install -r requirements.txt -i https://pypi.doubanio.com/simple

# MacOS
$ pip2.7 install -r requirements.txt -i https://pypi.doubanio.com/simple --user
```
	   
- 配置文件

```	
$ cd ..
$ cp config_example.py config.py
```

配置项 参考 config.py

- 初始化数据库
```
# cd utils
# sh make_migrations.sh
# sh init_db.sh
```
 
- 依赖redis
```
$ yum -y install redis
$ service redis start  # Run docker or redis-server &
```

- 启动

```
$ python2.7 run_server.py
```
 
### 开发者文档


   * [项目结构描述](https://github.com/jumpserver/jumpserver/blob/dev/docs/project_structure.md)
   * [Python代码规范](https://github.com/jumpserver/jumpserver/blob/dev/docs/python_style_guide.md)
   * [API设计规范](https://github.com/jumpserver/jumpserver/blob/dev/docs/api_style_guide.md)
