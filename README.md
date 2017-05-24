## Jumpserver
Jumpserver是一款使用Python, Django开发的开源跳板机系统, 助力互联网企业高效 用户、资产、权限、审计 管理

### 环境
   * Python 3.5  # 大部分功能兼容Python2.7
   * Django 1.11

### 安装
使用docker compose 安装，一键完成，docker compose 安装见 docker官方

   $ docker-compose up

### 使用
   1. 访问 http://你的主机IP:8080 来访问 Jumpserver
   
   2. 左侧 应用程序接受 Coco和Luna的注册
   
   3. 添加 管理用户
   
   4. 添加 资产 
   
   5. 添加授权规则，授权给admin
   
   6. ssh -p2222 admin@你的主机IP 测试连接服务器
 
   7. 访问 http://你的主机IP:5000 访问Luna，点击左侧服务器连接测试
   
   
### 截图

参见 https://github.com/jumpserver/jumpserver/issues/438

### 开发者文档


   * [项目结构描述](https://github.com/jumpserver/jumpserver/blob/dev/docs/project_structure.md)
   * [Python代码规范](https://github.com/jumpserver/jumpserver/blob/dev/docs/python_style_guide.md)
   * [API设计规范](https://github.com/jumpserver/jumpserver/blob/dev/docs/api_style_guide.md)
