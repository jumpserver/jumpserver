## Jumpserver 

![Total visitor](https://visitor-count-badge.herokuapp.com/total.svg?repo_id=jumpserver)
![Visitors in today](https://visitor-count-badge.herokuapp.com/today.svg?repo_id=jumpserver)
[![Python3](https://img.shields.io/badge/python-3.6-green.svg?style=plastic)](https://www.python.org/)
[![Django](https://img.shields.io/badge/django-2.1-brightgreen.svg?style=plastic)](https://www.djangoproject.com/)
[![Ansible](https://img.shields.io/badge/ansible-2.4.2.0-blue.svg?style=plastic)](https://www.ansible.com/)
[![Paramiko](https://img.shields.io/badge/paramiko-2.4.1-green.svg?style=plastic)](http://www.paramiko.org/)


----

- [中文版](https://github.com/jumpserver/jumpserver/blob/master/README_EN.md)

Jumpserver is the first fully open source bastion in the world, based on the GNU GPL v2.0 open source protocol. Jumpserver is a  professional operation and maintenance audit system conforms to 4A specifications.

Jumpserver is developed using Python / Django, conforms to the Web 2.0 specification, and is equipped with the industry-leading Web Terminal solution which have beautiful interface and great user experience.

Jumpserver adopts a distributed architecture to support multi-branch deployment across multiple areas. The central node provides APIs, and login nodes are deployed in each branch. It can be scaled horizontally without concurrency restrictions.

Change the world, starting from little things.

----

### Features


<table class="subscription-level-table">
    <tr class="subscription-level-tr-border">
        <td class="features-first-td-background-style" rowspan="5" style="text-align: center">
            Identity Authentication
        </td>
        <td class="features-second-td-background-style" rowspan="3" >
            Login Authentication
        </td>
        <td class="features-third-td-background-style">
            Resource unified login and authentication
        </td>
    </tr>
    <tr class="subscription-level-tr-border">
        <td class="features-third-td-background-style">
            LDAP Authentication
        </td>
    </tr>
    <tr class="subscription-level-tr-border">
        <td class="features-third-td-background-style">
            Support OpenID，achieved single sign-on
        </td>
    </tr>
    <tr class="subscription-level-tr-border">
        <td class="features-second-td-background-style">
            Multi-factors Authentication
        </td>
        <td class="features-third-td-background-style">
            MFA（Google Authenticator）
        </td>
    </tr>
    <tr class="subscription-level-tr-border">
        <td class="features-second-td-background-style">
            Login Review
        </td>
        <td class="features-third-td-background-style">
            Support secondary login review
        </td>
    </tr>
    <tr class="subscription-level-tr-border">
        <td class="features-first-td-background-style" rowspan="9" style="text-align: center" >
            Account Management
        </td>
        <td class="features-second-td-background-style" rowspan="2">
            Centralized Account Management
        </td>
        <td class="features-third-td-background-style">
            Manage user management
        </td>
    </tr>
    <tr class="subscription-level-tr-border">
        <td class="features-third-td-background-style">
            System user management
        </td>
    </tr>
    <tr class="subscription-level-tr-border">
        <td class="features-second-td-background-style" rowspan="4">
            Unified password management
        </td>
        <td class="features-third-td-background-style">
            Asset password custody
        </td>
    </tr>
    <tr class="subscription-level-tr-border">
        <td class="features-third-td-background-style">
            Auto-generated password
        </td>
    </tr>
    <tr class="subscription-level-tr-border">
        <td class="features-third-td-background-style">
            Automatic push password
        </td>
    </tr>
    <tr class="subscription-level-tr-border">
        <td class="features-third-td-background-style">
            Password expired setting
        </td>
    </tr>
    <tr class="subscription-level-tr-border">
        <td class="features-outline-td-background-style" rowspan="2">
            Batch password changes(X-PACK)
        </td>
        <td class="features-outline-td-background-style">
            Batch change password on a regular basis
        </td>
    </tr>
    <tr class="subscription-level-tr-border">
        <td class="features-outline-td-background-style">
            Generate random password
        </td>
    </tr>
    <tr class="subscription-level-tr-border">
        <td class="features-outline-td-background-style">
            Incorporate Multi-cloud Asset into management (X-PACK)
        </td>
        <td class="features-outline-td-background-style">
            Unified management of private and pulic cloud asset
        </td>
    </tr>
    <tr class="subscription-level-tr-border">
        <td class="features-first-td-background-style" rowspan="10" style="text-align: center">
            Authorization Control
        </td>
        <td class="features-second-td-background-style" rowspan="3">
            Asset authorization management 
        </td>
        <td class="features-third-td-background-style">
            Asset tree
        </td>
    </tr>
    <tr class="subscription-level-tr-border">
        <td class="features-third-td-background-style">
            Flexible Asset or Asset group authorization
        </td>
    </tr>
    <tr class="subscription-level-tr-border">
        <td class="features-third-td-background-style">
            Asset within nodes automatically inherit authorization
        </td>
    </tr>
    <tr class="subscription-level-tr-border">
        <td class="features-outline-td-background-style">
            Database authorization
        </td>
        <td class="features-outline-td-background-style">
            Implement mysql database app-level authorization
        </td>
     </tr>
    <tr class="subscription-level-tr-border">
        <td class="features-outline-td-background-style">
            RemoteApp(X-PACK)
        </td>
        <td class="features-outline-td-background-style">
            Implement more fine-grained app-level authorization
        </td>
    </tr>
    <tr class="subscription-level-tr-border">
        <td class="features-outline-td-background-style">
            Organization management (X-PACK)
        </td>
        <td class="features-outline-td-background-style">
            Implement multi-tenant management，privilege isolation
        </td>
    </tr>
    <tr class="subscription-level-tr-border">
        <td class="features-second-td-background-style">
            Multi-dimensional authorization
        </td>
        <td class="features-third-td-background-style">
            Can authorize user,user group or system user 
        </td>
    </tr>
    <tr class="subscription-level-tr-border">
        <td class="features-second-td-background-style">
            Command limitation
        </td>
        <td class="features-third-td-background-style">
            Restrict the use of privileged instructions,support black and white list
        </td>
    </tr>
    <tr class="subscription-level-tr-border">
        <td class="features-second-td-background-style">
            Unified file transfer
        </td>
        <td class="features-third-td-background-style">
            SFTP file upload/download
        </td>
    </tr>
    <tr class="subscription-level-tr-border">
        <td class="features-second-td-background-style">
            File management
        </td>
        <td class="features-third-td-background-style">
            Web SFTP file mangement
        </td>
    </tr>
    <tr class="subscription-level-tr-border">
        <td class="features-first-td-background-style" rowspan="7" style="text-align: center">
            Security Audit
        </td>
        <td class="features-second-td-background-style" rowspan="2">
            Session management
        </td>
        <td class="features-third-td-background-style">
            Session online management
        </td>
    </tr>
    <tr class="subscription-level-tr-border">
        <td class="features-third-td-background-style">
            Session offline management
        </td>
    </tr>
    <tr class="subscription-level-tr-border">
        <td class="features-second-td-background-style" rowspan="2">
            Video management
        </td>
        <td class="features-third-td-background-style">
            Support Linux video
        </td>
    </tr>
    <tr class="subscription-level-tr-border">
        <td class="features-third-td-background-style">
            Support Windows video
        </td>
    </tr>
    <tr class="subscription-level-tr-border">
        <td class="features-second-td-background-style">
            Command audit
        </td>
        <td class="features-third-td-background-style">
            Command recording 
        </td>
    </tr>
    <tr class="subscription-level-tr-border">
        <td class="features-second-td-background-style">
            File transfer audit
        </td>
        <td class="features-third-td-background-style">
            Upload/Download record audit
        </td>
    </tr>
    <tr class="subscription-level-tr-border">
        <td class="features-second-td-background-style">
            Ticket management
        </td>
        <td class="features-third-td-background-style">
            Secondary login review management
        </td>
     </tr>
</table>


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
- [Java](https://github.com/KaiJunYan/jumpserver-java-sdk.git) 恺珺同学提供的Java版本的SDK thanks to 恺珺 for provide Java SDK


### License & Copyright
Copyright (c) 2014-2019 Beijing Duizhan Tech, Inc., All rights reserved.

Licensed under The GNU General Public License version 2 (GPLv2)  (the "License"); you may not use this file except in compliance with the License. You may obtain a copy of the License at

https://www.gnu.org/licenses/gpl-2.0.html

Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the specific language governing permissions and limitations under the License.
