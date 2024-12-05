<div align="center">
  <a name="readme-top"></a>
  <a href="https://jumpserver.org/index-en.html"><img src="https://download.jumpserver.org/images/jumpserver-logo.svg" alt="JumpServer" width="300" /></a>
  
## JumpServerとは？

JumpServerは、DevOpsおよびITチームに対して、ウェブブラウザを介してSSH、RDP、Kubernetes、データベース、リモートアプリケーションエンドポイントにオンデマンドで安全にアクセスすることを提供するオープンソースの特権アクセス管理（PAM）ツールです。

![JumpServerの概要](https://github.com/jumpserver/jumpserver/assets/32935519/35a371cb-8590-40ed-88ec-f351f8cf9045)

## クイックスタート

クリーンなLinuxサーバーを準備します（64ビット、>= 4c8g）

```sh
curl -sSL https://github.com/jumpserver/jumpserver/releases/latest/download/quick_start.sh | bash
```

ブラウザでJumpServerにアクセスします `http://your-jumpserver-ip/`
- ユーザー名: `admin`
- パスワード: `ChangeMe`

[![JumpServerクイックスタート](https://github.com/user-attachments/assets/0f32f52b-9935-485e-8534-336c63389612)](https://www.youtube.com/watch?v=UlGYRbKrpgY "JumpServerクイックスタート")

## スクリーンショット

<table style="border-collapse: collapse; border: 1px solid black;">
  <tr>
    <td style="padding: 5px;background-color:#fff;"><img src= "https://github.com/jumpserver/jumpserver/assets/32935519/99fabe5b-0475-4a53-9116-4c370a1426c4" alt="JumpServerコンソール"   /></td>
    <td style="padding: 5px;background-color:#fff;"><img src= "https://github.com/jumpserver/jumpserver/assets/32935519/a424d731-1c70-4108-a7d8-5bbf387dda9a" alt="JumpServer監査"   /></td>
  </tr>

  <tr>
    <td style="padding: 5px;background-color:#fff;"><img src= "https://github.com/jumpserver/jumpserver/assets/32935519/393d2c27-a2d0-4dea-882d-00ed509e00c9" alt="JumpServerワークベンチ"   /></td>
    <td style="padding: 5px;background-color:#fff;"><img src= "https://github.com/jumpserver/jumpserver/assets/32935519/3a2611cd-8902-49b8-b82b-2a6dac851f3e" alt="JumpServer設定"   /></td>
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

## コンポーネント

JumpServerは複数の重要なコンポーネントで構成されており、これらは合わせてJumpServerの機能フレームワークを形成し、ユーザーに操作管理とセキュリティ制御の包括的な機能を提供します。

| プロジェクト                                               | ステータス                                                                                                                                                                 | 説明                                                                                                 |
|--------------------------------------------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------|-----------------------------------------------------------------------------------------------------|
| [Lina](https://github.com/jumpserver/lina)             | <a href="https://github.com/jumpserver/lina/releases"><img alt="Linaリリース" src="https://img.shields.io/github/release/jumpserver/lina.svg" /></a>                   | JumpServer Web UI                                                                                     |
| [Luna](https://github.com/jumpserver/luna)             | <a href="https://github.com/jumpserver/luna/releases"><img alt="Lunaリリース" src="https://img.shields.io/github/release/jumpserver/luna.svg" /></a>                   | JumpServer Webターミナル                                                                              |
| [KoKo](https://github.com/jumpserver/koko)             | <a href="https://github.com/jumpserver/koko/releases"><img alt="Kokoリリース" src="https://img.shields.io/github/release/jumpserver/koko.svg" /></a>                   | JumpServerキャラクタープロトコルコネクタ                                                             |
| [Lion](https://github.com/jumpserver/lion)             | <a href="https://github.com/jumpserver/lion/releases"><img alt="Lionリリース" src="https://img.shields.io/github/release/jumpserver/lion.svg" /></a>                   | JumpServerグラフィカルプロトコルコネクタ                                                             |
| [Chen](https://github.com/jumpserver/chen)             | <a href="https://github.com/jumpserver/chen/releases"><img alt="Chenリリース" src="https://img.shields.io/github/release/jumpserver/chen.svg" />                       | JumpServer Web DB                                                                                     |  
| [Razor](https://github.com/jumpserver/razor)           | <img alt="Chen" src="https://img.shields.io/badge/release-private-red" />                                                                                              | JumpServer EE RDPプロキシコネクタ                                                                     |
| [Tinker](https://github.com/jumpserver/tinker)         | <img alt="Tinker" src="https://img.shields.io/badge/release-private-red" />                                                                                            | JumpServer EEリモートアプリケーションコネクタ（Windows）                                            |
| [Panda](https://github.com/jumpserver/Panda)           | <img alt="Panda" src="https://img.shields.io/badge/release-private-red" />                                                                                             | JumpServer EEリモートアプリケーションコネクタ（Linux）                                              |
| [Magnus](https://github.com/jumpserver/magnus)         | <img alt="Magnus" src="https://img.shields.io/badge/release-private-red" />                                                                                            | JumpServer EEデータベースプロキシコネクタ                                                               |
| [Nec](https://github.com/jumpserver/nec)               | <img alt="Nec" src="https://img.shields.io/badge/release-private-red" />                                                                                               | JumpServer EE VNCプロキシコネクタ                                                                      |
| [Facelive](https://github.com/jumpserver/facelive)     | <img alt="Facelive" src="https://img.shields.io/badge/release-private-red" />                                                                                          | JumpServer EE顔認識                                                                                  |


## コントリビューティング

PRを提出して貢献することを歓迎します。ガイドラインについては[CONTRIBUTING.md][contributing-link]を参照してください。

## セキュリティ

JumpServerはミッションクリティカルな製品です。インストールおよびデプロイに関する基本的なセキュリティ推奨事項を参照してください。セキュリティ関連の問題が発生した場合は、直接ご連絡ください。

- メール: support@fit2cloud.com

## License

Copyright (c) 2014-2024 FIT2CLOUD, All rights reserved.

Licensed under The GNU General Public License version 3 (GPLv3) (the "License"); you may not use this file except in compliance with the License. You may obtain a copy of the License at

https://www.gnu.org/licenses/gpl-3.0.html

Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on an " AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the specific language governing permissions and limitations under the License.