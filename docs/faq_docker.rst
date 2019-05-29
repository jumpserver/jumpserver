Docker 使用说明
------------------------------

1. 查看所有镜像

.. code-block:: shell

    $ docker images

2. 查看所有创建的容器

.. code-block:: shell

    $ docker ps -a

3. 查看正在运行的容器

.. code-block:: shell

    $ docker ps

4. 进入正在运行的容器

.. code-block:: shell

    $ docker exec -it <容器的 CONTAINER ID 或者 容器 NAMES > /bin/bash

    # 例:
    $ docker ps
    CONTAINER ID    IMAGE                        COMMAND    CREATED        STATUS       PORTS                     NAMES
    ecda634206af    jumpserver/guacamole:test    "/init"    12 days ago    Up 3 days    0.0.0.0:8081->8080/tcp    jms_guacamole

    $ docker exec -it ecda634206af /bin/bash 或 docker exec -it jms_guacamole /bin/bash

5. 开始 停止 重启 容器

.. code-block:: shell

    $ docker start <容器的 CONTAINER ID 或者 容器 NAMES >
    $ docker stop <容器的 CONTAINER ID 或者 容器 NAMES >
    $ docker restart <容器的 CONTAINER ID 或者 容器 NAMES >

    # 例:
    $ docker ps
    CONTAINER ID    IMAGE                        COMMAND    CREATED        STATUS       PORTS                     NAMES
    ecda634206af    jumpserver/guacamole:test    "/init"    12 days ago    Up 3 days    0.0.0.0:8081->8080/tcp    jms_guacamole

    $ docker start ecda634206af 或 docker start jms_guacamole
    $ docker stop ecda634206af 或 docker stop jms_guacamole
    $ docker restart ecda634206af 或 docker restart jms_guacamole

6. 查看容器 log

.. code-block:: shell

    $ docker logs -f <容器的 CONTAINER ID 或者 容器 NAMES >

    # 例:
    $ docker ps
    CONTAINER ID    IMAGE                        COMMAND    CREATED        STATUS       PORTS                     NAMES
    ecda634206af    jumpserver/guacamole:test    "/init"    12 days ago    Up 3 days    0.0.0.0:8081->8080/tcp    jms_guacamole

    $ docker logs -f ecda634206af 或 docker logs -f jms_guacamole

7. 删除容器

.. code-block:: shell

    $ docker rm <容器的 CONTAINER ID 或者 容器 NAMES >

    # 例:
    $ docker ps
    CONTAINER ID    IMAGE                        COMMAND    CREATED        STATUS       PORTS                     NAMES
    ecda634206af    jumpserver/guacamole:test    "/init"    12 days ago    Up 3 days    0.0.0.0:8081->8080/tcp    jms_guacamole

    $ docker rm ecda634206af 或 docker rm jms_guacamole

8. 删除镜像


.. code-block:: shell

    $ docker rmi <镜像的 CONTAINER ID>

    # 例:
    $ docker images
    REPOSITORY             TAG     IMAGE ID        CREATED        SIZE
    jumpserver/guacamole   test    e0c2ec53a8fd    13 days ago    1.23GB

    $ docker rmi e0c2ec53a8fd

9. 更新镜像

.. code-block:: shell

    $ docker pull <镜像地址:版本>

    # 例:
    $ docker pull jumpserver/jms_all:latest
    $ docker pull jumpserver/jms_coco:1.5.0
    $ docker pull jumpserver/jms_guacamole:1.5.0
