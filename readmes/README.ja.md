<div align="center">
  <a name="readme-top"></a>
  <a href="https://jumpserver.com" target="_blank"><img src="https://download.jumpserver.org/images/jumpserver-logo.svg" alt="JumpServer" width="300" /></a>
  
## オープンソースの特権アクセス管理（PAM）プラットフォーム（踏み台サーバー）

[![][license-shield]][license-link]
[![][docs-shield]][docs-link]
[![][deepwiki-shield]][deepwiki-link]
[![][discord-shield]][discord-link]
[![][docker-shield]][docker-link]
[![][github-release-shield]][github-release-link]
[![][github-stars-shield]][github-stars-link]

[English](/README.md) · [中文(简体)](/readmes/README.zh-hans.md) · [中文(繁體)](/readmes/README.zh-hant.md) · [日本語](/readmes/README.ja.md) · [Português (Brasil)](/readmes/README.pt-br.md) · [Español](/readmes/README.es.md) · [Русский](/readmes/README.ru.md) · [한국어](/readmes/README.ko.md) · [Tiếng Việt](/readmes/README.vi.md)

</div>

<br/>

## JumpServer とは？

JumpServer は AI 機能を備えたオープンソースの特権アクセス管理（PAM）プラットフォームです。DevOps チームと IT チームが、SSH、RDP、Kubernetes、データベース、Web サイト、RemoteApp、VirtualApp などに安全にアクセスできる統合ワークスペースを提供します。

<img alt="JumpServer の構成図" src="https://github.com/user-attachments/assets/2bbf0979-4e1e-43ea-8dac-5d3e3bfbf1d1" />

## クイックスタート

CPU 4 コア以上、メモリ 8 GB 以上のクリーンな 64 ビット Linux サーバーを用意してください。

```sh
curl -sSL https://github.com/jumpserver/jumpserver/releases/latest/download/quick_start.sh | bash
```

ブラウザーで JumpServer にアクセスします： `http://your-jumpserver-ip/`

- ユーザー名: `admin`
- パスワード: `ChangeMe`

## スクリーンショット

<table width="100%" align="center">
  <tr>
    <td width="50%" align="center"><img src="https://github.com/user-attachments/assets/6164c92a-0b19-405a-b79c-73e28a9a1610" alt="JumpServer コンソール" width="100%" /></td>
    <td width="50%" align="center"><img src="https://github.com/user-attachments/assets/12d1206d-b511-4f29-8b00-fd13333f3a21" alt="JumpServer 特権アクセス管理" width="100%" /></td>
  </tr>
  <tr>
    <td width="50%" align="center"><img src="https://github.com/user-attachments/assets/6d12d3c9-5f31-4294-b6e7-7c5b5836f688" alt="JumpServer 監査" width="100%" /></td>
    <td width="50%" align="center"><img src="https://github.com/user-attachments/assets/ba784bc8-e889-4fd6-aaae-0b8b14153da2" alt="JumpServer ワークベンチ" width="100%" /></td>
  </tr>
  <tr>
    <td width="50%" align="center"><img src="https://github.com/user-attachments/assets/d4b10b15-bccb-4a0d-a6e6-74a6439614e0" alt="JumpServer ロールと権限の管理" width="100%" /></td>
    <td width="50%" align="center"><img src="https://github.com/user-attachments/assets/ccbeb96e-9747-4182-bd03-031fb3af8bb2" alt="JumpServer 設定" width="100%" /></td>
  </tr>
  <tr>
    <td width="50%" align="center"><img src="https://github.com/user-attachments/assets/9049888e-16fe-4fbe-b0f2-16bf140379c8" alt="JumpServer SSH" width="100%" /></td>
    <td width="50%" align="center"><img src="https://github.com/user-attachments/assets/133c4af6-90a9-457d-b372-bb53c29260dc" alt="JumpServer RDP" width="100%" /></td>
  </tr>
  <tr>
    <td width="50%" align="center"><img src="https://github.com/user-attachments/assets/ea48738f-b5f8-4a43-a487-ca09b11176e7" alt="JumpServer Kubernetes" width="100%" /></td>
    <td width="50%" align="center"><img src="https://github.com/user-attachments/assets/3407539f-1235-4dcc-adf2-26d7b60dbc67" alt="JumpServer データベース" width="100%" /></td>
  </tr>
</table>

## コンポーネント

JumpServer のコンポーネントは役割ごとに分類されています。コアプロジェクトはプラットフォーム、Web UI、ターミナル、プロトコル接続、AI 機能を提供します。エンタープライズコンポーネントはアプリケーションとプロトコルへのアクセスを拡張します。補助サービスはセッション録画とホスト運用を担い、導入ツールはインストールと Web 配信を簡素化します。

### コアプロジェクト

<table width="100%" align="center">
  <thead>
    <tr>
      <th width="160" align="left">プロジェクト</th>
      <th width="135" align="center"><div align="center">バージョン</div></th>
      <th align="center"><div align="center">説明</div></th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td width="160" align="left" nowrap><a href="https://github.com/jumpserver/jumpserver">JumpServer</a></td>
      <td width="135" align="center"><div align="center"><a href="https://github.com/jumpserver/jumpserver/tags"><img src="https://img.shields.io/github/v/tag/jumpserver/jumpserver?sort=semver&amp;filter=v5.*&amp;label=tag" alt="JumpServer バージョン" /></a></div></td>
      <td align="left">オープンソースの特権アクセス管理プラットフォーム</td>
    </tr>
    <tr>
      <td width="160" align="left" nowrap><a href="https://github.com/jumpserver/lina">Lina</a></td>
      <td width="135" align="center"><div align="center"><a href="https://github.com/jumpserver/lina/tags"><img src="https://img.shields.io/github/v/tag/jumpserver/lina?sort=semver&amp;filter=v5.*&amp;label=tag" alt="Lina バージョン" /></a></div></td>
      <td align="left">JumpServer の Web UI</td>
    </tr>
    <tr>
      <td width="160" align="left" nowrap><a href="https://github.com/jumpserver/luna">Luna</a></td>
      <td width="135" align="center"><div align="center"><a href="https://github.com/jumpserver/luna/tags"><img src="https://img.shields.io/github/v/tag/jumpserver/luna?sort=semver&amp;filter=v5.*&amp;label=tag" alt="Luna バージョン" /></a></div></td>
      <td align="left">JumpServer の Web ターミナルとネイティブクライアント</td>
    </tr>
    <tr>
      <td width="160" align="left" nowrap><a href="https://github.com/jumpserver/koko">KoKo</a></td>
      <td width="135" align="center"><div align="center"><a href="https://github.com/jumpserver/koko/tags"><img src="https://img.shields.io/github/v/tag/jumpserver/koko?sort=semver&amp;filter=v5.*&amp;label=tag" alt="KoKo バージョン" /></a></div></td>
      <td align="left">JumpServer の汎用プロトコルコネクターとプロキシ</td>
    </tr>
    <tr>
      <td width="160" align="left" nowrap><a href="https://github.com/jumpserver/chen">Chen</a></td>
      <td width="135" align="center"><div align="center"><a href="https://github.com/jumpserver/chen/tags"><img src="https://img.shields.io/github/v/tag/jumpserver/chen?sort=semver&amp;filter=v5.*&amp;label=tag" alt="Chen バージョン" /></a></div></td>
      <td align="left">JumpServer の Web データベースコネクター</td>
    </tr>
    <tr>
      <td width="160" align="left" nowrap><a href="https://github.com/jumpserver/kael">Kael</a></td>
      <td width="135" align="center"><div align="center"><a href="https://github.com/jumpserver/kael/tags"><img src="https://img.shields.io/github/v/tag/jumpserver/kael?sort=semver&amp;filter=v5.*&amp;label=tag" alt="Kael バージョン" /></a></div></td>
      <td align="left">JumpServer の AI コンポーネント</td>
    </tr>
  </tbody>
</table>

### エンタープライズコンポーネント

<table width="100%" align="center">
  <thead>
    <tr>
      <th width="160" align="left">プロジェクト</th>
      <th width="135" align="center"><div align="center">バージョン</div></th>
      <th align="center"><div align="center">説明</div></th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td width="160" align="left" nowrap><a href="https://github.com/jumpserver/tinker">Tinker</a></td>
      <td width="135" align="center"><div align="center"><img src="https://img.shields.io/badge/tag-private-red" alt="非公開バージョン" /></div></td>
      <td align="left">JumpServer の Windows アプリケーションコネクター（コミュニティ版では無料）</td>
    </tr>
    <tr>
      <td width="160" align="left" nowrap><a href="https://github.com/jumpserver/Panda">Panda</a></td>
      <td width="135" align="center"><div align="center"><img src="https://img.shields.io/badge/tag-private-red" alt="非公開バージョン" /></div></td>
      <td align="left">JumpServer エンタープライズ版の Linux アプリケーションコネクター</td>
    </tr>
    <tr>
      <td width="160" align="left" nowrap><a href="https://github.com/jumpserver/razor">Razor</a></td>
      <td width="135" align="center"><div align="center"><img src="https://img.shields.io/badge/tag-private-red" alt="非公開バージョン" /></div></td>
      <td align="left">JumpServer エンタープライズ版の RDP プロトコルプロキシ</td>
    </tr>
    <tr>
      <td width="160" align="left" nowrap><a href="https://github.com/jumpserver/magnus">Magnus</a></td>
      <td width="135" align="center"><div align="center"><img src="https://img.shields.io/badge/tag-private-red" alt="非公開バージョン" /></div></td>
      <td align="left">JumpServer エンタープライズ版のデータベースプロトコルプロキシ</td>
    </tr>
    <tr>
      <td width="160" align="left" nowrap><a href="https://github.com/jumpserver/nec">Nec</a></td>
      <td width="135" align="center"><div align="center"><img src="https://img.shields.io/badge/tag-private-red" alt="非公開バージョン" /></div></td>
      <td align="left">JumpServer エンタープライズ版の VNC プロトコルプロキシ</td>
    </tr>
  </tbody>
</table>

### 補助サービス

<table width="100%" align="center">
  <thead>
    <tr>
      <th width="160" align="left">プロジェクト</th>
      <th width="135" align="center"><div align="center">バージョン</div></th>
      <th align="center"><div align="center">説明</div></th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td width="160" align="left" nowrap><a href="https://github.com/jumpserver/video-worker">Video&nbsp;Worker</a></td>
      <td width="135" align="center"><div align="center"><img src="https://img.shields.io/badge/tag-private-red" alt="非公開バージョン" /></div></td>
      <td align="left">JumpServer エンタープライズ版のセッション録画トランスコードサービス</td>
    </tr>
    <tr>
      <td width="160" align="left" nowrap><a href="https://github.com/jumpserver/jdmc">JDMC</a></td>
      <td width="135" align="center"><div align="center"><img src="https://img.shields.io/badge/tag-private-red" alt="非公開バージョン" /></div></td>
      <td align="left">JumpServer エンタープライズ版のホスト運用・管理サービス</td>
    </tr>
  </tbody>
</table>

### 導入とツール

<table width="100%" align="center">
  <thead>
    <tr>
      <th width="160" align="left">プロジェクト</th>
      <th width="135" align="center"><div align="center">バージョン</div></th>
      <th align="center"><div align="center">説明</div></th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td width="160" align="left" nowrap><a href="https://github.com/jumpserver/installer">Installer</a></td>
      <td width="135" align="center"><div align="center"><a href="https://github.com/jumpserver/installer/tags"><img src="https://img.shields.io/github/v/tag/jumpserver/installer?sort=semver&amp;filter=v5.*&amp;label=tag" alt="Installer バージョン" /></a></div></td>
      <td align="left">JumpServer のインストール・管理ツール</td>
    </tr>
    <tr>
      <td width="160" align="left" nowrap><a href="https://github.com/jumpserver/docker-web">Docker&nbsp;Web</a></td>
      <td width="135" align="center"><div align="center"><a href="https://github.com/jumpserver/docker-web/tags"><img src="https://img.shields.io/github/v/tag/jumpserver/docker-web?sort=semver&amp;filter=v5.*&amp;label=tag" alt="Docker Web バージョン" /></a></div></td>
      <td align="left">JumpServer の Web ゲートウェイと静的アセット</td>
    </tr>
  </tbody>
</table>

## コントリビューション

コントリビューションを歓迎します。手順については [CONTRIBUTING.md][contributing-link] を参照してください。

## ライセンス

Copyright (c) 2014-2026 FIT2CLOUD. All rights reserved.

本プロジェクトは GNU General Public License バージョン 3（GPLv3、以下「ライセンス」）に基づいて提供されます。本ファイルはライセンスに従う場合にのみ使用できます。ライセンスの写しは次の URL で入手できます。

https://www.gnu.org/licenses/gpl-3.0.html

適用法令で義務付けられる場合、または書面で別途合意した場合を除き、ライセンスに基づいて配布されるソフトウェアは「現状有姿」で提供され、明示または黙示を問わず、いかなる保証や条件も伴いません。権利と制限の詳細はライセンスを参照してください。

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
