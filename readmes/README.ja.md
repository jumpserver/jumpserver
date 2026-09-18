<div align="center">
  <a name="readme-top"></a>
  <a href="https://jumpserver.com" target="_blank"><img src="https://download.jumpserver.org/images/jumpserver-logo.svg" alt="JumpServer" width="300" /></a>
  
## オープンソースの PAM プラットフォーム (バスティオン ホスト)

</div>
<br/>

## JumpServer とは？

JumpServer は、AI 機能を備えたオープンソースの特権アクセス管理 (PAM) プラットフォームです。DevOps および IT チームに統一されたワークスペースを提供し、SSH、RDP、Kubernetes、データベース、Web サイト、RemoteApp、VirtualApp などへの安全なアクセスを実現します。

<img alt="JumpServer アーキテクチャ図" src="https://github.com/user-attachments/assets/2bbf0979-4e1e-43ea-8dac-5d3e3bfbf1d1" />

## クイックスタート

クリーンな Linux サーバーを準備します (64 ビット, >= 4c8g)

```sh
curl -sSL https://github.com/jumpserver/jumpserver/releases/latest/download/quick_start.sh | bash
```

ブラウザで JumpServer にアクセスします: `http://your-jumpserver-ip/`
- ユーザー名: `admin`
- パスワード: `ChangeMe`


## スクリーンショット
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

## コンポーネント

JumpServer は、複数の主要コンポーネントで構成されており、これらが集まって JumpServer の機能的なフレームワークを形成し、ユーザーに対して運用管理およびセキュリティ制御の包括的な機能を提供します。

## プロジェクト

### コアプロジェクト

| プロジェクト | バージョン | 説明 |
| --- | --- | --- |
| [JumpServer](https://github.com/jumpserver/jumpserver) | [![tag](https://img.shields.io/github/v/tag/jumpserver/jumpserver?sort=semver&filter=v5.*&label=tag)](https://github.com/jumpserver/jumpserver/tags) | オープンソースの特権アクセス管理プラットフォーム |
| [Lina](https://github.com/jumpserver/lina) | [![tag](https://img.shields.io/github/v/tag/jumpserver/lina?sort=semver&filter=v5.*&label=tag)](https://github.com/jumpserver/lina/tags) | JumpServer Web UI |
| [Luna](https://github.com/jumpserver/luna) | [![tag](https://img.shields.io/github/v/tag/jumpserver/luna?sort=semver&filter=v5.*&label=tag)](https://github.com/jumpserver/luna/tags) | JumpServer Web ターミナルおよびネイティブクライアント |
| [KoKo](https://github.com/jumpserver/koko) | [![tag](https://img.shields.io/github/v/tag/jumpserver/koko?sort=semver&filter=v5.*&label=tag)](https://github.com/jumpserver/koko/tags) | JumpServer 汎用プロトコルコネクターおよびプロキシ |
| [Chen](https://github.com/jumpserver/chen) | [![tag](https://img.shields.io/github/v/tag/jumpserver/chen?sort=semver&filter=v5.*&label=tag)](https://github.com/jumpserver/chen/tags) | JumpServer Web データベースコネクター |
| [Kael](https://github.com/jumpserver/kael) | [![tag](https://img.shields.io/github/v/tag/jumpserver/kael?sort=semver&filter=v5.*&label=tag)](https://github.com/jumpserver/kael/tags) | JumpServer AI コンポーネント |

### エンタープライズ版コンポーネント

| プロジェクト | バージョン | 説明 |
| --- | --- | --- |
| [Tinker](https://github.com/jumpserver/tinker) | ![tag](https://img.shields.io/badge/tag-private-red) | JumpServer Windows アプリケーションコネクター（コミュニティ版で無料利用可能） |
| [Panda](https://github.com/jumpserver/Panda) | ![tag](https://img.shields.io/badge/tag-private-red) | JumpServer エンタープライズ版 Linux アプリケーションコネクター |
| [Razor](https://github.com/jumpserver/razor) | ![tag](https://img.shields.io/badge/tag-private-red) | JumpServer エンタープライズ版 RDP プロトコルプロキシ |
| [Magnus](https://github.com/jumpserver/magnus) | ![tag](https://img.shields.io/badge/tag-private-red) | JumpServer エンタープライズ版データベースプロトコルプロキシ |
| [Nec](https://github.com/jumpserver/nec) | ![tag](https://img.shields.io/badge/tag-private-red) | JumpServer エンタープライズ版 VNC プロトコルプロキシ |

### サポートサービス

| プロジェクト | バージョン | 説明 |
| --- | --- | --- |
| [Video Worker](https://github.com/jumpserver/video-worker) | ![tag](https://img.shields.io/badge/tag-private-red) | JumpServer エンタープライズ版セッション録画トランスコードワーカー |
| [JDMC](https://github.com/jumpserver/jdmc) | ![tag](https://img.shields.io/badge/tag-private-red) | JumpServer エンタープライズ版ホスト運用管理サービス |

### デプロイとツール

| プロジェクト | バージョン | 説明 |
| --- | --- | --- |
| [Installer](https://github.com/jumpserver/installer) | [![tag](https://img.shields.io/github/v/tag/jumpserver/installer?sort=semver&filter=v5.*&label=tag)](https://github.com/jumpserver/installer/tags) | JumpServer インストールおよび管理ツール |
| [Docker Web](https://github.com/jumpserver/docker-web) | [![tag](https://img.shields.io/github/v/tag/jumpserver/docker-web?sort=semver&filter=v5.*&label=tag)](https://github.com/jumpserver/docker-web/tags) | JumpServer Web ゲートウェイおよび静的アセット |

## 貢献

PR を提出して貢献していただけると幸いです。ガイドラインについては [CONTRIBUTING.md][contributing-link] を参照してください。

## ライセンス

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