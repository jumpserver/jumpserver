<div align="center">
  <a name="readme-top"></a>
  <a href="https://jumpserver.com" target="_blank"><img src="https://download.jumpserver.org/images/jumpserver-logo.svg" alt="JumpServer" width="300" /></a>
  
## 开源特权访问管理（PAM）平台（堡垒机）

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

## 什么是 JumpServer？

JumpServer 是具备 AI 能力的开源特权访问管理（PAM）平台，为 DevOps 和 IT 团队提供统一的工作空间，安全访问 SSH、RDP、Kubernetes、数据库、网站、RemoteApp、VirtualApp 等资源。

<img alt="JumpServer 架构图" src="https://github.com/user-attachments/assets/2bbf0979-4e1e-43ea-8dac-5d3e3bfbf1d1" />

## 快速开始

准备一台干净的 64 位 Linux 服务器，至少配备 4 核 CPU 和 8 GB 内存。

```sh
curl -sSL https://github.com/jumpserver/jumpserver/releases/latest/download/quick_start.sh | bash
```

在浏览器中访问 JumpServer： `http://your-jumpserver-ip/`

- 用户名: `admin`
- 密码: `ChangeMe`

## 截图

<p align="center"><img src="assets/jumpserver-screenshots.gif" alt="JumpServer 控制台、特权访问管理、终端、远程桌面和数据库会话的循环截图" width="95%" /></p>

## 组件

JumpServer 按职责划分组件。核心项目提供平台、Web 界面、终端、协议连接和 AI 能力；企业版组件扩展应用与协议访问；支撑服务处理会话录像和主机运维；部署工具简化安装与 Web 资源交付。

### 核心项目

<table width="100%">
  <thead>
    <tr>
      <th width="160" align="left">项目</th>
      <th width="135" align="center"><div align="center">版本</div></th>
      <th width="550" align="center"><div align="center">说明</div></th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td width="160" align="left" nowrap><a href="https://github.com/jumpserver/jumpserver">JumpServer</a></td>
      <td width="135" align="center"><div align="center"><a href="https://github.com/jumpserver/jumpserver/tags"><img src="https://img.shields.io/github/v/tag/jumpserver/jumpserver?sort=semver&amp;filter=v5.*&amp;label=tag" alt="JumpServer 版本" /></a></div></td>
      <td width="550" align="left">开源特权访问管理平台</td>
    </tr>
    <tr>
      <td width="160" align="left" nowrap><a href="https://github.com/jumpserver/lina">Lina</a></td>
      <td width="135" align="center"><div align="center"><a href="https://github.com/jumpserver/lina/tags"><img src="https://img.shields.io/github/v/tag/jumpserver/lina?sort=semver&amp;filter=v5.*&amp;label=tag" alt="Lina 版本" /></a></div></td>
      <td width="550" align="left">JumpServer Web 界面</td>
    </tr>
    <tr>
      <td width="160" align="left" nowrap><a href="https://github.com/jumpserver/luna">Luna</a></td>
      <td width="135" align="center"><div align="center"><a href="https://github.com/jumpserver/luna/tags"><img src="https://img.shields.io/github/v/tag/jumpserver/luna?sort=semver&amp;filter=v5.*&amp;label=tag" alt="Luna 版本" /></a></div></td>
      <td width="550" align="left">JumpServer Web 终端与原生客户端</td>
    </tr>
    <tr>
      <td width="160" align="left" nowrap><a href="https://github.com/jumpserver/koko">KoKo</a></td>
      <td width="135" align="center"><div align="center"><a href="https://github.com/jumpserver/koko/tags"><img src="https://img.shields.io/github/v/tag/jumpserver/koko?sort=semver&amp;filter=v5.*&amp;label=tag" alt="KoKo 版本" /></a></div></td>
      <td width="550" align="left">JumpServer 通用协议连接器与代理</td>
    </tr>
    <tr>
      <td width="160" align="left" nowrap><a href="https://github.com/jumpserver/chen">Chen</a></td>
      <td width="135" align="center"><div align="center"><a href="https://github.com/jumpserver/chen/tags"><img src="https://img.shields.io/github/v/tag/jumpserver/chen?sort=semver&amp;filter=v5.*&amp;label=tag" alt="Chen 版本" /></a></div></td>
      <td width="550" align="left">JumpServer Web 数据库连接器</td>
    </tr>
    <tr>
      <td width="160" align="left" nowrap><a href="https://github.com/jumpserver/kael">Kael</a></td>
      <td width="135" align="center"><div align="center"><a href="https://github.com/jumpserver/kael/tags"><img src="https://img.shields.io/github/v/tag/jumpserver/kael?sort=semver&amp;filter=v5.*&amp;label=tag" alt="Kael 版本" /></a></div></td>
      <td width="550" align="left">JumpServer AI 组件</td>
    </tr>
  </tbody>
</table>

### 企业版组件

<table width="100%">
  <thead>
    <tr>
      <th width="160" align="left">项目</th>
      <th width="135" align="center"><div align="center">版本</div></th>
      <th width="550" align="center"><div align="center">说明</div></th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td width="160" align="left" nowrap><a href="https://github.com/jumpserver/tinker">Tinker</a></td>
      <td width="135" align="center"><div align="center"><img src="https://img.shields.io/badge/tag-private-red" alt="私有版本" /></div></td>
      <td width="550" align="left">JumpServer Windows 应用连接器（社区版可免费使用）</td>
    </tr>
    <tr>
      <td width="160" align="left" nowrap><a href="https://github.com/jumpserver/Panda">Panda</a></td>
      <td width="135" align="center"><div align="center"><img src="https://img.shields.io/badge/tag-private-red" alt="私有版本" /></div></td>
      <td width="550" align="left">JumpServer 企业版 Linux 应用连接器</td>
    </tr>
    <tr>
      <td width="160" align="left" nowrap><a href="https://github.com/jumpserver/razor">Razor</a></td>
      <td width="135" align="center"><div align="center"><img src="https://img.shields.io/badge/tag-private-red" alt="私有版本" /></div></td>
      <td width="550" align="left">JumpServer 企业版 RDP 协议代理</td>
    </tr>
    <tr>
      <td width="160" align="left" nowrap><a href="https://github.com/jumpserver/magnus">Magnus</a></td>
      <td width="135" align="center"><div align="center"><img src="https://img.shields.io/badge/tag-private-red" alt="私有版本" /></div></td>
      <td width="550" align="left">JumpServer 企业版数据库协议代理</td>
    </tr>
    <tr>
      <td width="160" align="left" nowrap><a href="https://github.com/jumpserver/nec">Nec</a></td>
      <td width="135" align="center"><div align="center"><img src="https://img.shields.io/badge/tag-private-red" alt="私有版本" /></div></td>
      <td width="550" align="left">JumpServer 企业版 VNC 协议代理</td>
    </tr>
  </tbody>
</table>

### 支撑服务

<table width="100%">
  <thead>
    <tr>
      <th width="160" align="left">项目</th>
      <th width="135" align="center"><div align="center">版本</div></th>
      <th width="550" align="center"><div align="center">说明</div></th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td width="160" align="left" nowrap><a href="https://github.com/jumpserver/video-worker">Video&nbsp;Worker</a></td>
      <td width="135" align="center"><div align="center"><img src="https://img.shields.io/badge/tag-private-red" alt="私有版本" /></div></td>
      <td width="550" align="left">JumpServer 企业版会话录像转码服务</td>
    </tr>
    <tr>
      <td width="160" align="left" nowrap><a href="https://github.com/jumpserver/jdmc">JDMC</a></td>
      <td width="135" align="center"><div align="center"><img src="https://img.shields.io/badge/tag-private-red" alt="私有版本" /></div></td>
      <td width="550" align="left">JumpServer 企业版主机运维与管理服务</td>
    </tr>
  </tbody>
</table>

### 部署与工具

<table width="100%">
  <thead>
    <tr>
      <th width="160" align="left">项目</th>
      <th width="135" align="center"><div align="center">版本</div></th>
      <th width="550" align="center"><div align="center">说明</div></th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td width="160" align="left" nowrap><a href="https://github.com/jumpserver/installer">Installer</a></td>
      <td width="135" align="center"><div align="center"><a href="https://github.com/jumpserver/installer/tags"><img src="https://img.shields.io/github/v/tag/jumpserver/installer?sort=semver&amp;filter=v5.*&amp;label=tag" alt="Installer 版本" /></a></div></td>
      <td width="550" align="left">JumpServer 安装与管理工具</td>
    </tr>
    <tr>
      <td width="160" align="left" nowrap><a href="https://github.com/jumpserver/docker-web">Docker&nbsp;Web</a></td>
      <td width="135" align="center"><div align="center"><a href="https://github.com/jumpserver/docker-web/tags"><img src="https://img.shields.io/github/v/tag/jumpserver/docker-web?sort=semver&amp;filter=v5.*&amp;label=tag" alt="Docker Web 版本" /></a></div></td>
      <td width="550" align="left">JumpServer Web 网关与静态资源</td>
    </tr>
  </tbody>
</table>

## 参与贡献

欢迎提交贡献。请阅读 [CONTRIBUTING.md][contributing-link] 了解贡献指南。

## 许可证

版权所有 (c) 2014-2026 FIT2CLOUD。保留所有权利。

本项目依据 GNU 通用公共许可证第 3 版（GPLv3，以下简称“许可证”）授权；您只能在遵守许可证的前提下使用本文件。许可证副本可从以下地址获取：

https://www.gnu.org/licenses/gpl-3.0.html

除非适用法律要求或另有书面约定，根据许可证分发的软件均按“原样”提供，不附带任何明示或暗示的保证或条件。有关权限和限制，请参阅许可证中的具体规定。

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
