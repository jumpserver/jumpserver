傻瓜安装
==========================

由于部分用户对 Linux 不熟悉，这里提供基于 CentoOS_7_64 的傻瓜安装脚本。

本脚本仅支持 CentoOS7 64 位的系统安装 Jumpserver，无法在其他系统中正常运行。

该脚本基于完全干净的 CentOS7 64位系统的安装，该脚本会安装 Redis 和 Mariadb 等各种依赖，望运行时请注意。


下载安装脚本
```````````````
使用 root 命令行输入::

    $ wget https://raw.githubusercontent.com/jumpserver/Dockerfile/mysql/get.sh

执行
```````````````

    $ sh get.sh

错误情况
```````````````

如果遇到错误，本脚本会以中文的形式大致叙述一下解决方法，请自行尝试解决，如网络原因文件下载失败，请删除未下载完成的文件后手动执行该命令。


安装后期
```````````````

后续的使用请参考 `快速入门 <admin_create_asset.html>`_
如遇到问题可参考 `FAQ <faq.html>`_
