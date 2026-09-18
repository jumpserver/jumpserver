<div align="center">
  <a name="readme-top"></a>
  <a href="https://jumpserver.com" target="_blank"><img src="https://download.jumpserver.org/images/jumpserver-logo.svg" alt="JumpServer" width="300" /></a>
  
## 오픈 소스 PAM 플랫폼(점프 서버)
</div>

<br/>

## JumpServer란 무엇인가요?

JumpServer는 AI 기능을 갖춘 오픈 소스 특권 액세스 관리(PAM) 플랫폼으로, DevOps 및 IT 팀이 SSH, RDP, Kubernetes, 데이터베이스, 웹사이트, RemoteApp, VirtualApp 등에 안전하게 액세스할 수 있는 통합 작업 공간을 제공합니다.

<img alt="JumpServer 아키텍처 다이어그램" src="https://github.com/user-attachments/assets/2bbf0979-4e1e-43ea-8dac-5d3e3bfbf1d1" />

## 빠른 시작

깨끗한 리눅스 서버를 준비하세요 ( 64 비트, >= 4c8g )

```sh
curl -sSL https://github.com/jumpserver/jumpserver/releases/latest/download/quick_start.sh | bash
```

브라우저에서 점프서버에 액세스하기: `http://your-jumpserver-ip/`
- 사용자 이름: `admin`
- 비밀번호: `ChangeMe`

## 스크린샷
<table style="border-collapse: collapse; border: 1px solid black;">
  <tr>
    <td style="padding: 5px;background-color:#fff;"><img src= "https://github.com/user-attachments/assets/6164c92a-0b19-405a-b79c-73e28a9a1610" alt="JumpServer Console"   /></td>
    <td style="padding: 5px;background-color:#fff;"><img src= "https://github.com/user-attachments/assets/12d1206d-b511-4f29-8b00-fd13333f3a21" alt="JumpServer PAM"   /></td>
  </tr>
  <tr>
    <td style="padding: 5px;background-color:#fff;"><img src= "https://github.com/user-attachments/assets/6d12d3c9-5f31-4294-b6e7-7c5b5836f688" alt="JumpServer Audits"   /></td>
    <td style="padding: 5px;background-color:#fff;"><img src= "https://github.com/user-attachments/assets/ba784bc8-e889-4fd6-aaae-0b8b14153da2" alt="JumpServer Workbench"   /></td>
  </tr>
  <tr>
    <td style="padding: 5px;background-color:#fff;"><img src= "https://github.com/user-attachments/assets/d4b10b15-bccb-4a0d-a6e6-74a6439614e0" alt="JumpServer RBAC"   /></td>
    <td style="padding: 5px;background-color:#fff;"><img src= "https://github.com/user-attachments/assets/ccbeb96e-9747-4182-bd03-031fb3af8bb2" alt="JumpServer Settings"   /></td>
  </tr>
  <tr>
    <td style="padding: 5px;background-color:#fff;"><img src= "https://github.com/user-attachments/assets/9049888e-16fe-4fbe-b0f2-16bf140379c8" alt="JumpServer RBAC"   /></td>
    <td style="padding: 5px;background-color:#fff;"><img src= "https://github.com/user-attachments/assets/133c4af6-90a9-457d-b372-bb53c29260dc" alt="JumpServer Settings"   /></td>
  </tr>
  <tr>
    <td style="padding: 5px;background-color:#fff;"><img src= "https://github.com/user-attachments/assets/ea48738f-b5f8-4a43-a487-ca09b11176e7" alt="JumpServer RBAC"   /></td>
    <td style="padding: 5px;background-color:#fff;"><img src= "https://github.com/user-attachments/assets/3407539f-1235-4dcc-adf2-26d7b60dbc67" alt="JumpServer Settings"   /></td>
  </tr>
</table>

## 구성 요소

점프서버는 여러 핵심 구성 요소로 이루어져 있으며, 이는 점프서버의 기능적 프레임워크를 형성하여 사용자가 운영 관리 및 보안 제어를 위한 포괄적인 기능을 제공합니다.

## 프로젝트

### 핵심 프로젝트

| 프로젝트 | 버전 | 설명 |
| --- | --- | --- |
| [JumpServer](https://github.com/jumpserver/jumpserver) | [![tag](https://img.shields.io/github/v/tag/jumpserver/jumpserver?sort=semver&filter=v5.*&label=tag)](https://github.com/jumpserver/jumpserver/tags) | 오픈 소스 특권 액세스 관리 플랫폼 |
| [리나](https://github.com/jumpserver/lina) | [![tag](https://img.shields.io/github/v/tag/jumpserver/lina?sort=semver&filter=v5.*&label=tag)](https://github.com/jumpserver/lina/tags) | JumpServer 웹 UI |
| [루나](https://github.com/jumpserver/luna) | [![tag](https://img.shields.io/github/v/tag/jumpserver/luna?sort=semver&filter=v5.*&label=tag)](https://github.com/jumpserver/luna/tags) | JumpServer 웹 터미널 및 네이티브 클라이언트 |
| [코코](https://github.com/jumpserver/koko) | [![tag](https://img.shields.io/github/v/tag/jumpserver/koko?sort=semver&filter=v5.*&label=tag)](https://github.com/jumpserver/koko/tags) | JumpServer 범용 프로토콜 커넥터 및 프록시 |
| [첸](https://github.com/jumpserver/chen) | [![tag](https://img.shields.io/github/v/tag/jumpserver/chen?sort=semver&filter=v5.*&label=tag)](https://github.com/jumpserver/chen/tags) | JumpServer 웹 데이터베이스 커넥터 |
| [Kael](https://github.com/jumpserver/kael) | [![tag](https://img.shields.io/github/v/tag/jumpserver/kael?sort=semver&filter=v5.*&label=tag)](https://github.com/jumpserver/kael/tags) | JumpServer AI 구성 요소 |

### 엔터프라이즈 에디션 구성 요소

| 프로젝트 | 버전 | 설명 |
| --- | --- | --- |
| [팅커](https://github.com/jumpserver/tinker) | ![tag](https://img.shields.io/badge/tag-private-red) | JumpServer Windows 애플리케이션 커넥터(커뮤니티 에디션에서 무료 사용 가능) |
| [판다](https://github.com/jumpserver/Panda) | ![tag](https://img.shields.io/badge/tag-private-red) | JumpServer 엔터프라이즈 에디션 Linux 애플리케이션 커넥터 |
| [레이저](https://github.com/jumpserver/razor) | ![tag](https://img.shields.io/badge/tag-private-red) | JumpServer 엔터프라이즈 에디션 RDP 프로토콜 프록시 |
| [마그누스](https://github.com/jumpserver/magnus) | ![tag](https://img.shields.io/badge/tag-private-red) | JumpServer 엔터프라이즈 에디션 데이터베이스 프로토콜 프록시 |
| [넥](https://github.com/jumpserver/nec) | ![tag](https://img.shields.io/badge/tag-private-red) | JumpServer 엔터프라이즈 에디션 VNC 프로토콜 프록시 |

### 지원 서비스

| 프로젝트 | 버전 | 설명 |
| --- | --- | --- |
| [Video Worker](https://github.com/jumpserver/video-worker) | ![tag](https://img.shields.io/badge/tag-private-red) | JumpServer 엔터프라이즈 에디션 세션 녹화 트랜스코딩 워커 |
| [JDMC](https://github.com/jumpserver/jdmc) | ![tag](https://img.shields.io/badge/tag-private-red) | JumpServer 엔터프라이즈 에디션 호스트 운영 및 관리 서비스 |

### 배포 및 도구

| 프로젝트 | 버전 | 설명 |
| --- | --- | --- |
| [Installer](https://github.com/jumpserver/installer) | [![tag](https://img.shields.io/github/v/tag/jumpserver/installer?sort=semver&filter=v5.*&label=tag)](https://github.com/jumpserver/installer/tags) | JumpServer 설치 및 관리 도구 |
| [Docker Web](https://github.com/jumpserver/docker-web) | [![tag](https://img.shields.io/github/v/tag/jumpserver/docker-web?sort=semver&filter=v5.*&label=tag)](https://github.com/jumpserver/docker-web/tags) | JumpServer 웹 게이트웨이 및 정적 리소스 |

## 기여하기

기여를 위해 PR을 제출하는 것을 환영합니다. 가이드라인은 [CONTRIBUTING.md][contributing-link]를 참조하세요.

## 라이센스

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
[docker-shield]: https://img.shields.io/docker/pulls/jumpserver/jms_all.svg
[license-shield]: https://img.shields.io/github/license/jumpserver/jumpserver
[deepwiki-shield]: https://img.shields.io/badge/deepwiki-devin?color=blue
[discord-shield]: https://img.shields.io/discord/1194233267294052363?style=flat&logo=discord&logoColor=%23f5f5f5&labelColor=%235462eb&color=%235462eb