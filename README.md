<div align="center">
  <a name="readme-top"></a>
  <a href="https://jumpserver.com" target="_blank"><img src="https://download.jumpserver.org/images/jumpserver-logo.svg" alt="JumpServer" width="300" /></a>

## An open-source PAM tool (Bastion Host)

[![][license-shield]][license-link]
[![][docs-shield]][docs-link]
[![][deepwiki-shield]][deepwiki-link]
[![][discord-shield]][discord-link]
[![][docker-shield]][docker-link]
[![][github-release-shield]][github-release-link]
[![][github-stars-shield]][github-stars-link]

[English](/README.md) · [中文(简体)](/readmes/README.zh-hans.md) · [中文(繁體)](/readmes/README.zh-hant.md) · [日本語](/readmes/README.ja.md) · [Português (Brasil)](/readmes/README.pt-br.md) · [Español](/readmes/README.es.md) · [Русский](/readmes/README.ru.md) · [한국어](/readmes/README.ko.md)

</div>
<br/>

## What is JumpServer?

JumpServer is a comprehensive open-source Privileged Access Management (PAM) tool and bastion host that provides DevOps and IT teams with secure, auditable, and centralized access to critical infrastructure. Through a modern web browser interface, JumpServer enables on-demand access to SSH, RDP, Kubernetes, Database, and RemoteApp endpoints while maintaining complete session recording and audit trails.

### 🔐 Core Capabilities

**Privileged Access Management (PAM)**
- Centralized credential management and rotation
- Just-in-time access provisioning
- Session-based access controls with time limits
- Comprehensive audit trails and compliance reporting

**Multi-Protocol Support**
- **SSH/SFTP**: Linux/Unix server access with terminal recording
- **RDP**: Windows desktop and server connections
- **Database**: MySQL, PostgreSQL, Oracle, SQL Server, MongoDB, Redis
- **Kubernetes**: Container orchestration platform access
- **Web Applications**: RemoteApp and web-based application access
- **VNC**: Virtual Network Computing for graphical interfaces

**Enterprise Security Features**
- **Multi-Factor Authentication (MFA)**: OTP, SMS, Email, Face Recognition, RADIUS
- **Role-Based Access Control (RBAC)**: Granular permission management
- **Session Recording**: Complete video/text capture of all sessions
- **Command Filtering**: Real-time command blocking and monitoring
- **IP Restrictions**: Geo-location and network-based access controls
- **Watermarking**: Session identification and security overlays

### 🏗️ Architecture & Components

JumpServer follows a microservices architecture with specialized components for different functionalities:

**Core Components (Open Source)**
- **Core**: Django-based API server and management interface
- **Lina**: Modern Vue.js web UI for administration
- **Luna**: Web-based terminal interface for end users
- **KoKo**: Character protocol connector (SSH, Telnet, Database)
- **Lion**: Graphical protocol connector (RDP, VNC)
- **Chen**: Web database management interface

**Enterprise Components (Commercial)**
- **Tinker**: Windows RemoteApp connector
- **Panda**: Linux RemoteApp connector
- **Razor**: Enhanced RDP proxy with advanced features
- **Magnus**: Database proxy with query analysis
- **Nec**: VNC proxy connector
- **Facelive**: AI-powered facial recognition system

### 🎨 User Interface & Experience

**Modern Web Interface**
- **Responsive Design**: Mobile-friendly interface for on-the-go access
- **Dark Theme**: Eye-friendly dark mode with automatic system detection
- **Multi-language Support**: Internationalization for global teams
- **Customizable Dashboard**: Personalized views and quick access panels

### 🛡️ Security & Compliance

**Audit & Monitoring**
- Real-time session monitoring and alerting
- Comprehensive command and file transfer logging
- User behavior analytics and risk assessment
- Integration with SIEM systems via syslog

**Authentication & Authorization**
- LDAP/Active Directory integration
- SAML 2.0 and OAuth 2.0 support
- CAS (Central Authentication Service)
- Custom authentication backends

**Compliance Standards**
- SOX, PCI-DSS, HIPAA compliance support
- Detailed audit reports and evidence collection
- Password policy enforcement
- Session recording retention policies

### 🚀 Use Cases

- **DevOps Teams**: Secure access to production infrastructure
- **IT Operations**: Centralized server and database management
- **Security Teams**: Privileged access monitoring and control
- **Compliance Officers**: Audit trail generation and reporting
- **Cloud Migration**: Hybrid and multi-cloud access management


<picture>
  <source media="(prefers-color-scheme: light)" srcset="https://www.jumpserver.com/images/jumpserver-arch-light.png">
  <source media="(prefers-color-scheme: dark)" srcset="https://www.jumpserver.com/images/jumpserver-arch-dark.png">
  <img src="https://github.com/user-attachments/assets/dd612f3d-c958-4f84-b164-f31b75454d7f" alt="Theme-based Image">
</picture>


## 🚀 Deployment Options

### Quick Start (Recommended)

Prepare a clean Linux Server ( 64 bit, >= 4c8g )

```sh
curl -sSL https://github.com/jumpserver/jumpserver/releases/latest/download/quick_start.sh | bash
```

Access JumpServer in your browser at `http://your-jumpserver-ip/`
- Username: `admin`
- Password: `ChangeMe`

[![JumpServer Quickstart](https://github.com/user-attachments/assets/0f32f52b-9935-485e-8534-336c63389612)](https://www.youtube.com/watch?v=UlGYRbKrpgY "JumpServer Quickstart")

### Docker Compose (Development & Testing)

For development environments or testing purposes, use the included Docker Compose configuration:

```bash
# Clone the repository
git clone https://github.com/jumpserver/jumpserver.git
cd jumpserver

# Copy and configure environment variables
cp .env.example .env
# Edit .env file with your configuration

# Start services
docker-compose up -d

# Check service status
docker-compose ps
```

### Production Deployment

For production environments, consider:
- **High Availability**: Deploy multiple instances with load balancing
- **Database**: Use external PostgreSQL or MySQL cluster
- **Storage**: Configure shared storage for session recordings
- **SSL/TLS**: Implement proper certificate management
- **Monitoring**: Set up comprehensive monitoring and alerting

Refer to the [official documentation](https://jumpserver.com/docs) for detailed production deployment guides.

### Docker Image Publishing

For maintainers and contributors who need to publish Docker images to Docker Hub:

**Linux/macOS:**
```bash
# Make the script executable
chmod +x scripts/docker-publish.sh

# Publish with version tag and latest
./scripts/docker-publish.sh

# Force rebuild even if image exists
./scripts/docker-publish.sh --force

# Skip latest tag
./scripts/docker-publish.sh --skip-latest

# With custom build arguments
./scripts/docker-publish.sh --build-args "--no-cache --platform linux/amd64,linux/arm64"
```

**Windows:**
```cmd
# Publish with version tag and latest
scripts\docker-publish.bat

# Force rebuild even if image exists
scripts\docker-publish.bat --force

# Skip latest tag
scripts\docker-publish.bat --skip-latest
```

**Environment Variables for Authentication:**
```bash
export DOCKER_USERNAME="your-dockerhub-username"
export DOCKER_PASSWORD="your-dockerhub-password"
# OR use access token
export DOCKER_HUB_TOKEN="your-dockerhub-token"
```

The script automatically:
- Extracts version from `pyproject.toml`
- Handles Docker Hub authentication
- Builds images with proper tags
- Pushes to Docker Hub registry
- Supports idempotent operations

## Screenshots
<table style="border-collapse: collapse; border: 1px solid black;">
  <tr>
    <td style="padding: 5px;background-color:#fff;"><img src= "https://github.com/jumpserver/jumpserver/assets/32935519/99fabe5b-0475-4a53-9116-4c370a1426c4" alt="JumpServer Console"   /></td>
    <td style="padding: 5px;background-color:#fff;"><img src= "https://github.com/user-attachments/assets/7c1f81af-37e8-4f07-8ac9-182895e1062e" alt="JumpServer PAM"   /></td>
  </tr>
  <tr>
    <td style="padding: 5px;background-color:#fff;"><img src= "https://github.com/jumpserver/jumpserver/assets/32935519/a424d731-1c70-4108-a7d8-5bbf387dda9a" alt="JumpServer Audits"   /></td>
    <td style="padding: 5px;background-color:#fff;"><img src= "https://github.com/jumpserver/jumpserver/assets/32935519/393d2c27-a2d0-4dea-882d-00ed509e00c9" alt="JumpServer Workbench"   /></td>
  </tr>
  <tr>
    <td style="padding: 5px;background-color:#fff;"><img src= "https://github.com/user-attachments/assets/eaa41f66-8cc8-4f01-a001-0d258501f1c9" alt="JumpServer RBAC"   /></td>
    <td style="padding: 5px;background-color:#fff;"><img src= "https://github.com/jumpserver/jumpserver/assets/32935519/3a2611cd-8902-49b8-b82b-2a6dac851f3e" alt="JumpServer Settings"   /></td>
  </tr>
  <tr>
    <td style="padding: 5px;background-color:#fff;"><img src= "https://github.com/jumpserver/jumpserver/assets/32935519/1e236093-31f7-4563-8eb1-e36d865f1568" alt="JumpServer SSH"   /></td>
    <td style="padding: 5px;background-color:#fff;"><img src= "https://github.com/jumpserver/jumpserver/assets/32935519/69373a82-f7ab-41e8-b763-bbad2ba52167" alt="JumpServer RDP"   /></td>
  </tr>
  <tr>
    <td style="padding: 5px;background-color:#fff;"><img src= "https://github.com/jumpserver/jumpserver/assets/32935519/5bed98c6-cbe8-4073-9597-d53c69dc3957" alt="JumpServer K8s"   /></td>
    <td style="padding: 5px;background-color:#fff;"><img src= "https://github.com/jumpserver/jumpserver/assets/32935519/b80ad654-548f-42bc-ba3d-c1cfdf1b46d6" alt="JumpServer DB"   /></td>
  </tr>
</table>

## Components

JumpServer consists of multiple key components, which collectively form the functional framework of JumpServer, providing users with comprehensive capabilities for operations management and security control.

| Project                                                | Status                                                                                                                                                                 | Description                                                                                             |
|--------------------------------------------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------------------|
| [Lina](https://github.com/jumpserver/lina)             | <a href="https://github.com/jumpserver/lina/releases"><img alt="Lina release" src="https://img.shields.io/github/release/jumpserver/lina.svg" /></a>                   | JumpServer Web UI                                                                                       |
| [Luna](https://github.com/jumpserver/luna)             | <a href="https://github.com/jumpserver/luna/releases"><img alt="Luna release" src="https://img.shields.io/github/release/jumpserver/luna.svg" /></a>                   | JumpServer Web Terminal                                                                                 |
| [KoKo](https://github.com/jumpserver/koko)             | <a href="https://github.com/jumpserver/koko/releases"><img alt="Koko release" src="https://img.shields.io/github/release/jumpserver/koko.svg" /></a>                   | JumpServer Character Protocol Connector                                                                 |
| [Lion](https://github.com/jumpserver/lion)             | <a href="https://github.com/jumpserver/lion/releases"><img alt="Lion release" src="https://img.shields.io/github/release/jumpserver/lion.svg" /></a>                   | JumpServer Graphical Protocol Connector                                                                 |
| [Chen](https://github.com/jumpserver/chen)             | <a href="https://github.com/jumpserver/chen/releases"><img alt="Chen release" src="https://img.shields.io/github/release/jumpserver/chen.svg" />                       | JumpServer Web DB                                                                                       |
| [Tinker](https://github.com/jumpserver/tinker)         | <img alt="Tinker" src="https://img.shields.io/badge/release-private-red" />                                                                                            | JumpServer Remote Application Connector (Windows)                                                    |
| [Panda](https://github.com/jumpserver/Panda)           | <img alt="Panda" src="https://img.shields.io/badge/release-private-red" />                                                                                             | JumpServer EE Remote Application Connector (Linux)                                                      |
| [Razor](https://github.com/jumpserver/razor)           | <img alt="Chen" src="https://img.shields.io/badge/release-private-red" />                                                                                              | JumpServer EE RDP Proxy Connector                                                                       |
| [Magnus](https://github.com/jumpserver/magnus)         | <img alt="Magnus" src="https://img.shields.io/badge/release-private-red" />                                                                                            | JumpServer EE Database Proxy Connector                                                                  |
| [Nec](https://github.com/jumpserver/nec)               | <img alt="Nec" src="https://img.shields.io/badge/release-private-red" />                                                                                               | JumpServer EE VNC Proxy Connector                                                                       |
| [Facelive](https://github.com/jumpserver/facelive)     | <img alt="Facelive" src="https://img.shields.io/badge/release-private-red" />                                                                                          | JumpServer EE Facial Recognition                                                                        |


## Contributing

Welcome to submit PR to contribute. Please refer to [CONTRIBUTING.md][contributing-link] for guidelines.

## License

Copyright (c) 2014-2025 FIT2CLOUD, All rights reserved.

Licensed under The GNU General Public License version 3 (GPLv3) (the "License"); you may not use this file except in compliance with the License. You may obtain a copy of the License at

https://www.gnu.org/licenses/gpl-3.0.html

Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on an " AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the specific language governing permissions and limitations under the License.

<!-- JumpServer official link -->
[docs-link]: https://jumpserver.com/docs
[discord-link]: https://discord.com/invite/W6vYXmAQG2
[deepwiki-link]: https://deepwiki.com/jumpserver/jumpserver/
[contributing-link]: https://github.com/jumpserver/jumpserver/blob/dev/CONTRIBUTING.md

<!-- JumpServer Other link-->
[license-link]: https://www.gnu.org/licenses/gpl-3.0.html
[docker-link]: https://hub.docker.com/u/jumpserver
[github-release-link]: https://github.com/jumpserver/jumpserver/releases/latest
[github-stars-link]: https://github.com/jumpserver/jumpserver
[github-issues-link]: https://github.com/jumpserver/jumpserver/issues

<!-- Shield link-->
[docs-shield]: https://img.shields.io/badge/documentation-148F76
[github-release-shield]: https://img.shields.io/github/v/release/jumpserver/jumpserver
[github-stars-shield]: https://img.shields.io/github/stars/jumpserver/jumpserver?color=%231890FF&style=flat-square
[docker-shield]: https://img.shields.io/docker/pulls/jumpserver/jumpserver.svg
[license-shield]: https://img.shields.io/github/license/jumpserver/jumpserver
[deepwiki-shield]: https://img.shields.io/badge/deepwiki-devin?color=blue
[discord-shield]: https://img.shields.io/discord/1194233267294052363?style=flat&logo=discord&logoColor=%23f5f5f5&labelColor=%235462eb&color=%235462eb
