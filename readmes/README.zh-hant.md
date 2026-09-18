<div align="center">
  <a name="readme-top"></a>
  <a href="https://jumpserver.com" target="_blank"><img src="https://download.jumpserver.org/images/jumpserver-logo.svg" alt="JumpServer" width="300" /></a>
  
## 一個開源的 PAM 平台 (堡壘主機)

</div>
<br/>

## JumpServer 是什麼？

JumpServer 是一個具備 AI 能力的開源特權訪問管理 (PAM) 平台，為 DevOps 和 IT 團隊提供統一的工作空間，以安全訪問 SSH、RDP、Kubernetes、數據庫、網站、RemoteApp、VirtualApp 等資源。

<img alt="JumpServer 架構圖" src="https://github.com/user-attachments/assets/2bbf0979-4e1e-43ea-8dac-5d3e3bfbf1d1" />

## 快速開始

準備一台乾淨的 Linux 伺服器 (64 位，>= 4c8g)

```sh
curl -sSL https://github.com/jumpserver/jumpserver/releases/latest/download/quick_start.sh | bash
```

在您的瀏覽器中訪問 JumpServer，地址為 `http://your-jumpserver-ip/`
- 用戶名：`admin`
- 密碼：`ChangeMe`


## 畫面截圖
<table style="border-collapse: collapse; border: 1px solid black;">
  <tr>
    <td style="padding: 5px;background-color:#fff;"><img src= "https://github.com/user-attachments/assets/6164c92a-0b19-405a-b79c-73e28a9a1610" alt="JumpServer 控制台"   /></td>
    <td style="padding: 5px;background-color:#fff;"><img src= "https://github.com/user-attachments/assets/12d1206d-b511-4f29-8b00-fd13333f3a21" alt="JumpServer PAM"   /></td>
  </tr>
  <tr>
    <td style="padding: 5px;background-color:#fff;"><img src= "https://github.com/user-attachments/assets/6d12d3c9-5f31-4294-b6e7-7c5b5836f688" alt="JumpServer 審計"   /></td>
    <td style="padding: 5px;background-color:#fff;"><img src= "https://github.com/user-attachments/assets/ba784bc8-e889-4fd6-aaae-0b8b14153da2" alt="JumpServer 工作台"   /></td>
  </tr>
  <tr>
    <td style="padding: 5px;background-color:#fff;"><img src= "https://github.com/user-attachments/assets/d4b10b15-bccb-4a0d-a6e6-74a6439614e0" alt="JumpServer RBAC"   /></td>
    <td style="padding: 5px;background-color:#fff;"><img src= "https://github.com/user-attachments/assets/ccbeb96e-9747-4182-bd03-031fb3af8bb2" alt="JumpServer 設定"   /></td>
  </tr>
  <tr>
    <td style="padding: 5px;background-color:#fff;"><img src= "https://github.com/user-attachments/assets/9049888e-16fe-4fbe-b0f2-16bf140379c8" alt="JumpServer RBAC"   /></td>
    <td style="padding: 5px;background-color:#fff;"><img src= "https://github.com/user-attachments/assets/133c4af6-90a9-457d-b372-bb53c29260dc" alt="JumpServer 設定"   /></td>
  </tr>
  <tr>
    <td style="padding: 5px;background-color:#fff;"><img src= "https://github.com/user-attachments/assets/ea48738f-b5f8-4a43-a487-ca09b11176e7" alt="JumpServer RBAC"   /></td>
    <td style="padding: 5px;background-color:#fff;"><img src= "https://github.com/user-attachments/assets/3407539f-1235-4dcc-adf2-26d7b60dbc67" alt="JumpServer 設定"   /></td>
  </tr>
</table>

## 組件

JumpServer 由多個關鍵組件組成，這些組件共同構成了 JumpServer 的功能框架，為用戶提供全面的操作管理和安全控制能力。

## 項目

### 核心項目

| 項目 | 版本 | 描述 |
| --- | --- | --- |
| [JumpServer](https://github.com/jumpserver/jumpserver) | [![tag](https://img.shields.io/github/v/tag/jumpserver/jumpserver?sort=semver&filter=v5.*&label=tag)](https://github.com/jumpserver/jumpserver/tags) | 開源特權訪問管理平台 |
| [Lina](https://github.com/jumpserver/lina) | [![tag](https://img.shields.io/github/v/tag/jumpserver/lina?sort=semver&filter=v5.*&label=tag)](https://github.com/jumpserver/lina/tags) | JumpServer 網頁 UI |
| [Luna](https://github.com/jumpserver/luna) | [![tag](https://img.shields.io/github/v/tag/jumpserver/luna?sort=semver&filter=v5.*&label=tag)](https://github.com/jumpserver/luna/tags) | JumpServer 網頁終端和原生客戶端 |
| [KoKo](https://github.com/jumpserver/koko) | [![tag](https://img.shields.io/github/v/tag/jumpserver/koko?sort=semver&filter=v5.*&label=tag)](https://github.com/jumpserver/koko/tags) | JumpServer 通用協議連接器和代理 |
| [Chen](https://github.com/jumpserver/chen) | [![tag](https://img.shields.io/github/v/tag/jumpserver/chen?sort=semver&filter=v5.*&label=tag)](https://github.com/jumpserver/chen/tags) | JumpServer 網頁數據庫連接器 |
| [Kael](https://github.com/jumpserver/kael) | [![tag](https://img.shields.io/github/v/tag/jumpserver/kael?sort=semver&filter=v5.*&label=tag)](https://github.com/jumpserver/kael/tags) | JumpServer AI 組件 |

### 企業版組件

| 項目 | 版本 | 描述 |
| --- | --- | --- |
| [Tinker](https://github.com/jumpserver/tinker) | ![tag](https://img.shields.io/badge/tag-private-red) | JumpServer Windows 應用連接器（社群版免費使用） |
| [Panda](https://github.com/jumpserver/Panda) | ![tag](https://img.shields.io/badge/tag-private-red) | JumpServer 企業版 Linux 應用連接器 |
| [Razor](https://github.com/jumpserver/razor) | ![tag](https://img.shields.io/badge/tag-private-red) | JumpServer 企業版 RDP 協議代理 |
| [Magnus](https://github.com/jumpserver/magnus) | ![tag](https://img.shields.io/badge/tag-private-red) | JumpServer 企業版數據庫協議代理 |
| [Nec](https://github.com/jumpserver/nec) | ![tag](https://img.shields.io/badge/tag-private-red) | JumpServer 企業版 VNC 協議代理 |

### 配套服務

| 項目 | 版本 | 描述 |
| --- | --- | --- |
| [Video Worker](https://github.com/jumpserver/video-worker) | ![tag](https://img.shields.io/badge/tag-private-red) | JumpServer 企業版會話錄影轉碼服務 |
| [JDMC](https://github.com/jumpserver/jdmc) | ![tag](https://img.shields.io/badge/tag-private-red) | JumpServer 企業版主機維運管理服務 |

### 部署與工具

| 項目 | 版本 | 描述 |
| --- | --- | --- |
| [Installer](https://github.com/jumpserver/installer) | [![tag](https://img.shields.io/github/v/tag/jumpserver/installer?sort=semver&filter=v5.*&label=tag)](https://github.com/jumpserver/installer/tags) | JumpServer 安裝和管理工具 |
| [Docker Web](https://github.com/jumpserver/docker-web) | [![tag](https://img.shields.io/github/v/tag/jumpserver/docker-web?sort=semver&filter=v5.*&label=tag)](https://github.com/jumpserver/docker-web/tags) | JumpServer Web 閘道和靜態資源 |

## 貢獻

歡迎提交 PR 以貢獻。請參考 [CONTRIBUTING.md][contributing-link] 獲取指南。

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
[docker-shield]: https://img.shields.io/docker/pulls/jumpserver/jms_all.svg
[license-shield]: https://img.shields.io/github/license/jumpserver/jumpserver
[deepwiki-shield]: https://img.shields.io/badge/deepwiki-devin?color=blue
[discord-shield]: https://img.shields.io/discord/1194233267294052363?style=flat&logo=discord&logoColor=%23f5f5f5&labelColor=%235462eb&color=%235462eb