<div align="center"><a name="readme-top"></a>
  <a href="https://jumpserver.org"><img src="https://download.jumpserver.org/images/jumpserver-logo.svg" alt="JumpServer" width="300" /></a>
  
### Popular Open-Source Bastion Host

<!-- SHIELD GROUP-->
[![][license-shield]][license-link]
[![][docker-shield]][docker-link]
[![][github-release-shield]][github-release-link]
[![][github-stars-shield]][github-stars-link]

**English** · [简体中文](./README.zh-CN.md) · [Documents][docs-link] · [Report Bug][github-issues-link] · [Request Feature][github-issues-link]

For 9 years, pouring heart and soul into creating a high-quality open-source bastion host. <br/>

</div>

#
![][image-dashboard]
_[To-do]: Need to design the graphics._

<details>
<summary><kbd>Table of contents</kbd></summary>

#### TOC

- [Getting Started](#getting-started)
- [Introduction](#introduction)
- [Why JumpServer](#why-jumpserver)
- [Installation](#installation)
- [Product Architecture & Components](#product-architecture--components)
- [Features](#features)
  - [`1` User Authentication Supporting Integration with Multiple Single Sign-On Systems](#1-user-authentication-supporting-integration-with-multiple-single-sign-on-systems)
  - [`2` User Management Based on Role-based Access Control](#2-user-management-based-on-role-based-access-control)
  - [`3` Asset Management of Everything is an Asset](#3-asset-management-of-everything-is-an-asset)
  - [`4` Asset Account Management](#4-asset-account-management)
  - [`5` Asset Authorization Management](#5-asset-authorization-management)
  - [`6` Asset Permission Management Based Access Control Logic](#6-asset-permission-management-based-access-control-logic)
  - [`7` Remote Application Management for Everything](#7-remote-application-management-for-everything)
  - [`8` Support for Multiple Asset Connection Methods](#8-support-for-multiple-asset-connection-methods)
  - [`9` Comprehensive and Detailed User Behavior Audit System](#9-comprehensive-and-detailed-user-behavior-audit-system)
  - [`10` Organization Management with Resource Isolation](#10-organization-management-with-resource-isolation) [![][version-ee-shield-badge]][official-website-en-link] 
  - [`11` Ticket Management](#11-ticket-management) [![][version-ee-shield-badge]][official-website-en-link] 
- [Contributing](#contributing)
- [Security](#security)
- [License](#license)
####

<br/>

</details>

## Getting Started

Step right into our online demonstration environment, where you can effortlessly experience our product without the need for time-consuming software installations. With just a few clicks, you'll quickly grasp the functionality and features of our product. In the demonstration environment, you can explore the various features of our product to your heart's content and experience our innovative design and exceptional performance.

Whether you're new to the experience or a seasoned expert, we invite you to join our Discord community right away! Here, our developers and enthusiastic users come together to offer support and assistance. No matter what challenges you encounter during your usage, we are committed to answering your questions and providing guidance.

| [![][demo-shield-badge]][demo-link]       | No installation or registration necessary! Visit our website to experience it firsthand.                           |
| :---------------------------------------- | :----------------------------------------------------------------------------------------------------------------- |
| [![][discord-shield-badge]][discord-link] | Join our Discord community! This is where you can connect with developers and other enthusiastic users of JumpServer. |

> \[!IMPORTANT]
>
> **Star Us**, You will receive all release notifications from GitHub without any delay \~ ⭐️

![][image-star]

<details>
  <summary><kbd>Star History</kbd></summary>
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/svg?repos=jumpserver%2Fjumpserver&theme=dark&type=Date">
    <img width="100%" src="https://api.star-history.com/svg?repos=jumpserver%2Fjumpserver&type=Date">
  </picture>
</details>

> \[!TIP]
>
> This is a demonstration video that can quickly help you understand the page design and product features of JumpServer.

<video controls src="https://github.com/jumpserver/jumpserver/assets/32935519/6f984266-24a1-4d1f-9745-4a8e0122f49c" muted="false"></video>
_[To-do]: Need to design the video._

## Introduction

JumpServer is a widely acclaimed open-source bastion host, serving as a professional operational security auditing system compliant with the 4A standards. It helps businesses securely manage and access all types of assets in a more secure manner, enabling pre-authorization, real-time monitoring, and post-audit capabilities.

JumpServer aims to become the industry's preferred platform, assisting businesses in securely and efficiently managing and accessing all types of assets. By offering a professional operational security auditing system compliant with 4A standards, JumpServer is committed to delivering advanced asset management and access solutions, meeting enterprises' needs for security, reliability, and efficiency.

JumpServer's vision is to become a leader in the enterprise-level asset management and access control field, providing comprehensive solutions for users to securely and efficiently manage and utilize their assets. Through continuous innovation and enhancement of product features, JumpServer is committed to driving the development of the entire industry and becoming a key supporter and promoter of enterprise digital transformation.

![][image-supported-asset-type]
_[To-do]: Need to design the graphics._

## Why JumpServer
1. **Open Source**: JumpServer is an open-source software, meaning users can freely access, use, and modify its source code to meet individual needs, while also benefiting from community support and collaboration.
2. **Plugin-Free**: JumpServer provides comprehensive functionality without the need for additional plugins or extensions. This simplifies deployment and management processes, reducing potential compatibility and security risks.
3. **Distributed**: JumpServer supports a distributed architecture, allowing easy scaling across multiple nodes for high availability and fault tolerance. This makes it suitable for large-scale deployments and complex network environments.
4. **Multi-Cloud**: JumpServer offers support for various cloud platforms, including AWS, Azure, Google Cloud, etc., enabling users to manage and access assets seamlessly across different cloud environments.
5. **Cloud Storage**: JumpServer supports storing critical data such as audit logs and configuration files in the cloud, ensuring data security and reliability, as well as facilitating cross-region and cross-device access.
6. **Organizational**: JumpServer provides a flexible organizational structure, supporting multi-level organizational hierarchies and permission management. This allows administrators to finely control user access permissions, ensuring asset security and compliance.

## Installation

JumpServer supports multiple installation methods to cater to diverse user scenarios and preferences:

See Docs: https://docs.jumpserver.org/zh/v3/

#### `1` Online
Ideal for users with internet access, this method involves downloading installation scripts or packages directly from the internet. It ensures easy access to the latest updates and dependencies during installation.

Quick installation of JumpServer in just two steps:

1. Prepare a 64-bit Linux host with at least 4 cores and 8 GB of RAM, which has internet access.
2. Execute the following command as the root user for one-click installation of JumpServer.

```sh
curl -sSL https://github.com/jumpserver/jumpserver/releases/latest/download/quick_start.sh | bash
```

#### `2` Offline
Suited for environments without internet connectivity, this method allows users to download all necessary installation files and dependencies beforehand. It ensures seamless installation even in isolated or restricted network environments.

Download offline package: https://community.fit2cloud.com/#/products/jumpserver/downloads

#### `3` Kubernetes (K8s)
JumpServer supports installation on Kubernetes clusters. You can deploy JumpServer as containerized applications on Kubernetes, leveraging the scalability and management features of Kubernetes for running JumpServer.

#### `4` All-in-One
This method provides a simplified installation process where all components of JumpServer are installed on a single server or machine. It's suitable for small-scale deployments or testing purposes where separate component deployment is not required.

#### `5` Enterprise Edition Trial
JumpServer offers a trial version of its enterprise edition, allowing users to test out the enterprise features and functionalities before committing to a full deployment. This trial version typically comes with limited duration or features to provide a glimpse of the capabilities of the enterprise edition.

Each installation method caters to different use cases and deployment scenarios, offering flexibility and options for users based on their requirements and infrastructure setup.

Applying for the Enterprise Edition: https://jumpserver.org/enterprise.html

## Product Architecture & Components
#### Architecture Diagram
Below is the schematic diagram of the JumpServer system architecture, providing a more comprehensive understanding of the product features of JumpServer.
![][image-system-architecture]
_[To-do]: Need to design the graphics._

#### Supporting Components
JumpServer consists of multiple key components, which collectively form the functional framework of JumpServer, providing users with comprehensive capabilities for operations management and security control.
| Project                                                | Status                                                                                                                                                                 | Description                                                                             |
|--------------------------------------------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------|--------------------------------------------------------------------------------------------------------|
| [Lina](https://github.com/jumpserver/lina)             | <a href="https://github.com/jumpserver/lina/releases"><img alt="Lina release" src="https://img.shields.io/github/release/jumpserver/lina.svg" /></a>                   | JumpServer Web UI                                                             
| [Luna](https://github.com/jumpserver/luna)             | <a href="https://github.com/jumpserver/luna/releases"><img alt="Luna release" src="https://img.shields.io/github/release/jumpserver/luna.svg" /></a>                   | JumpServer Web Terminal                                                            |
| [KoKo](https://github.com/jumpserver/koko)             | <a href="https://github.com/jumpserver/koko/releases"><img alt="Koko release" src="https://img.shields.io/github/release/jumpserver/koko.svg" /></a>                   | JumpServer Character Protocol Connector                                                                 |
| [Lion](https://github.com/jumpserver/lion-release)     | <a href="https://github.com/jumpserver/lion-release/releases"><img alt="Lion release" src="https://img.shields.io/github/release/jumpserver/lion-release.svg" /></a>   | JumpServer Graphical Protocol Connector, dependent on [Apache Guacamole](https://guacamole.apache.org/) |
| [Razor](https://github.com/jumpserver/razor)           | <img alt="Chen" src="https://img.shields.io/badge/release-private-red" />                                                                                              | JumpServer RDP Proxy Connector                                                    |
| [Tinker](https://github.com/jumpserver/tinker)         | <img alt="Tinker" src="https://img.shields.io/badge/release-private-red" />                                                                                            | JumpServer Remote Application Connector (Windows)                                                      |
| [Panda](https://github.com/jumpserver/Panda)           | <img alt="Panda" src="https://img.shields.io/badge/release-private-red" />                                                                                             | JumpServer Remote Application Connector (Linux)                                                      |
| [Magnus](https://github.com/jumpserver/magnus-release) | <a href="https://github.com/jumpserver/magnus-release/releases"><img alt="Magnus release" src="https://img.shields.io/github/release/jumpserver/magnus-release.svg" /> | JumpServer Database Proxy Connector                                                     |
| [Chen](https://github.com/jumpserver/chen-release)     | <a href="https://github.com/jumpserver/chen-release/releases"><img alt="Chen release" src="https://img.shields.io/github/release/jumpserver/chen-release.svg" />       | JumpServer Web DB                                                 |
| [Kael](https://github.com/jumpserver/kael)             | <a href="https://github.com/jumpserver/kael/releases"><img alt="Kael release" src="https://img.shields.io/github/release/jumpserver/kael.svg" />                       | JumpServer GPT Assets Connector                                                         |
| [Wisp](https://github.com/jumpserver/wisp)             | <a href="https://github.com/jumpserver/wisp/releases"><img alt="Magnus release" src="https://img.shields.io/github/release/jumpserver/wisp.svg" />                     | JumpServer Inter-Project Communication Component with Core API                                            |
| [Clients](https://github.com/jumpserver/clients)       | <a href="https://github.com/jumpserver/clients/releases"><img alt="Clients release" src="https://img.shields.io/github/release/jumpserver/clients.svg" />              | JumpServer Client                                                                |
| [Installer](https://github.com/jumpserver/installer)   | <a href="https://github.com/jumpserver/installer/releases"><img alt="Installer release" src="https://img.shields.io/github/release/jumpserver/installer.svg" />        | JumpServer Installation Tool                                                                 |


## Features

### `1` User Authentication Supporting Integration with Multiple Single Sign-On Systems

### `2` User Management Based on Role-based Access Control

### `3` Asset Management of Everything is an Asset

### `4` Asset Account Management

### `5` Asset Authorization Management

### `6` Asset Permission Management Based Access Control Logic

### `7` Remote Application Management for Everything

### `8` Support for Multiple Asset Connection Methods

### `9` Comprehensive and Detailed User Behavior Audit System

### `10` Organization Management with Resource Isolation

### `11` Ticket Management

## Contributing
Welcome to submit PR to contribute. Please refer to CONTRIBUTING.md for guidelines.

## Security
JumpServer is a secure product. Please refer to the Basic Security Recommendations for installation and deployment. If you encounter any security-related issues, please contact us directly:

Email: support@fit2cloud.com
Phone: 400-052-0755

## License
Copyright (c) 2014-2024 飞致云 FIT2CLOUD, All rights reserved.

Licensed under The GNU General Public License version 3 (GPLv3) (the "License"); you may not use this file except in compliance with the License. You may obtain a copy of the License at

https://www.gnu.org/licenses/gpl-3.0.html

Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on an " AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the specific language governing permissions and limitations under the License.



<!-- JumpServer official link -->
[official-website-en-link]: https://jumpserver.org/
[docs-link]: https://docs.jumpserver.org/
[community-link]: https://community.fit2cloud.com/#/products/jumpserver/downloads
[demo-link]: https://demo.jumpserver.org/
[discord-link]: https://discord.gg/DVz6Hckx


<!-- JumpServer Other link-->
[license-link]: https://www.gnu.org/licenses/gpl-3.0.html
[docker-link]: https://hub.docker.com/u/jumpserver
[github-release-shield]: https://img.shields.io/github/v/release/jumpserver/jumpserver
[github-release-link]: https://github.com/jumpserver/jumpserver/releases/latest
[github-stars-shield]: https://img.shields.io/github/stars/jumpserver/jumpserver?color=%231890FF&style=flat-square
[github-stars-link]: https://github.com/jumpserver/jumpserver
[github-issues-link]: https://github.com/jumpserver/jumpserver/issues


<!-- Shield link-->
[docker-shield]: https://img.shields.io/docker/pulls/jumpserver/jms_all.svg
[license-shield]: https://img.shields.io/github/license/jumpserver/jumpserver
[demo-shield-badge]: https://img.shields.io/badge/ONLINE-online?style=plastic&logo=jameson&logoColor=white&label=TRY%20JUMPSERVER&labelColor=black&color=%23148f76
[discord-shield-badge]: https://img.shields.io/badge/JOIN_US_NOW-ONLINE?style=plastic&logo=discord&logoColor=white&label=DISCORD&labelColor=black&color=%23404eed
[version-ee-shield-badge]: https://img.shields.io/badge/Enterprise-black?style=flat-square&logo=vagrant

<!-- Image link -->
[image-jumpserver]: https://download.jumpserver.org/images/jumpserver-logo.svg
[image-dashboard]: https://github.com/jumpserver/jumpserver/assets/32935519/014c2230-82d3-4b53-b907-8149ce44bbd0
[image-star]: https://github.com/jumpserver/jumpserver/assets/32935519/76158e65-783d-4f11-81cd-45556a388e63
[image-supported-asset-type]: https://github.com/jumpserver/jumpserver/assets/32935519/8e769007-5449-4e86-b34b-d04e8e484257
[image-system-architecture]: https://github.com/jumpserver/jumpserver/assets/32935519/8a720b4e-19ed-4e3c-a8aa-325d7581005a


