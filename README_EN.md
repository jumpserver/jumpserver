## Jumpserver 

[![Python3](https://img.shields.io/badge/python-3.6-green.svg?style=plastic)](https://www.python.org/)
[![Django](https://img.shields.io/badge/django-2.2-brightgreen.svg?style=plastic)](https://www.djangoproject.com/)
[![Docker Pulls](https://img.shields.io/docker/pulls/jumpserver/jms_all.svg)](https://hub.docker.com/u/jumpserver)

---- 
## CRITICAL BUG WARNING

Recently we have found a critical bug for remote execution vulnerability which leads to pre-auth and info leak, please fix it as soon as possible.

Thanks for **reactivity from Alibaba Hackerone bug bounty program** report us this bug

**Vulnerable version:**
```
< v2.6.2
< v2.5.4
< v2.4.5 
= v1.5.9
>= v1.5.3
```

**Safe and Stable version:**
```
>= v2.6.2
>= v2.5.4
>= v2.4.5 
= v1.5.9 （version tag didn't change）
< v1.5.3
```

**Bug Fix Solution:**
Upgrade to the latest version or the version mentioned above


**Temporary Solution (upgrade asap):**

Modify the Nginx config file and disable the vulnerable api listed below

```
/api/v1/authentication/connection-token/
/api/v1/users/connection-token/
```

Path to Nginx config file

```
# Previous Community version
/etc/nginx/conf.d/jumpserver.conf

# Previous Enterprise version
jumpserver-release/nginx/http_server.conf
 
# Latest version
jumpserver-release/compose/config_static/http_server.conf
```

Changes in Nginx config file

```
### Put the following code on top of location server, or before /api and /
location /api/v1/authentication/connection-token/ {
   return 403;
}
 
location /api/v1/users/connection-token/ {
   return 403;
}
### End right here
 
location /api/ {
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_pass http://core:8080;
  }
 
...
```

Save the file and restart Nginx

```
docker deployment: 
$ docker restart jms_nginx

rpm or other deployment:
$ systemctl restart nginx

```

**Bug Fix Verification**

```
# Download the following script to check if it is fixed
$ wget https://github.com/jumpserver/jumpserver/releases/download/v2.6.2/jms_bug_check.sh 

# Run the code to verify it
$ bash jms_bug_check.sh demo.jumpserver.org
漏洞已修复 (It means the bug is fixed)
漏洞未修复 (It means the bug is not fixed and the system is still vulnerable)
```


**Attack Simulation**

Go to the logs directory which should contain gunicorn.log file. Then download the "attack" script and execute it

```
$ pwd
/opt/jumpserver/core/logs

$ ls gunicorn.log
gunicorn.log

$ wget 'https://github.com/jumpserver/jumpserver/releases/download/v2.6.2/jms_check_attack.sh'
$ bash jms_check_attack.sh
系统未被入侵 (It means the system is safe)
系统已被入侵 (It means the system is being attacked)
```

--------------------------

----

- [中文版](https://github.com/jumpserver/jumpserver/blob/master/README.md)

Jumpserver is the world's first open-source PAM (Privileged Access Management System) and is licensed under the GNU GPL v2.0. It is a 4A-compliant professional operation and maintenance security audit system.

Jumpserver uses Python / Django for development, follows Web 2.0 specifications, and is equipped with an industry-leading Web Terminal solution that provides a beautiful user interface and great user experience

Jumpserver adopts a distributed architecture to support multi-branch deployment across multiple cross-regional areas. The central node provides APIs, and login nodes are deployed in each branch. It can be scaled horizontally without concurrency restrictions.

Change the world, starting from little things.

----

### Features

 ![Jumpserver 功能](https://jumpserver-release.oss-cn-hangzhou.aliyuncs.com/Jumpserver148.jpeg "Jumpserver 功能")

### Start 

Quick start  [Docker Install](http://docs.jumpserver.org/zh/docs/dockerinstall.html)

Step by Step deployment. [Docs](http://docs.jumpserver.org/zh/docs/step_by_step.html)

Full documentation [Docs](http://docs.jumpserver.org)

### Demo、Video 和 Snapshot

We provide online demo, demo video and screenshots to get you started quickly.

[Demo](https://demo.jumpserver.org/auth/login/?next=/)
[Video](https://fit2cloud2-offline-installer.oss-cn-beijing.aliyuncs.com/tools/Jumpserver%20%E4%BB%8B%E7%BB%8Dv1.4.mp4)
[Snapshot](http://docs.jumpserver.org/zh/docs/snapshot.html)

### SDK

We provide the SDK for your other systems to quickly interact with the Jumpserver API.

- [Python](https://github.com/jumpserver/jumpserver-python-sdk) Jumpserver other components use this SDK to complete the interaction.
- [Java](https://github.com/KaiJunYan/jumpserver-java-sdk.git) Thanks to 恺珺 for providing his Java SDK vesrion.


### License & Copyright
Copyright (c) 2014-2019 Beijing Duizhan Tech, Inc., All rights reserved.

Licensed under The GNU General Public License version 2 (GPLv2)  (the "License"); you may not use this file except in compliance with the License. You may obtain a copy of the License at

https://www.gnu.org/licenses/gpl-2.0.html

Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the specific language governing permissions and limitations under the License.
