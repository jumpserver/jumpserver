# 安全说明

JumpServer 是一款开源特权访问管理（PAM）产品。为确保系统安全，请参考[基本安全建议](https://docs.fit2cloud.com/jumpserver/faq/security/) 进行部署和配置。

## 版本维护状态

以下为 JumpServer 当前的版本维护状态：

| 版本 | 状态 | 是否支持 |
| --- | --- | --- |
| 5.x | 活跃维护（Active） | 是 |
| 4.10.x | 长期支持（LTS） | 是 |
| 3.10.x | 历史版本（Legacy） | 仅关键问题修复 |
| 3.9.x 及更早版本 | 停止维护（EOL） | 否 |

V3 的维护范围仅限 3.10.x，且仅提供关键问题修复。社区版（CE）的维护截止日期为 **2026 年 12 月 31 日**，企业版（EE）的维护截止日期为 **2028 年 12 月 31 日**。各版本在维护截止后不再提供问题修复和安全更新。

请使用维护中版本系列的最新补丁版本；表中的维护状态不代表该系列的所有历史补丁版本均已修复已知漏洞。已知漏洞及修复版本请查看[安全公告](https://www.jumpserver.org/security.html)，可用版本请查看[发行记录](https://github.com/jumpserver/jumpserver/releases)。

根据 [V2 产品生命周期说明](https://docs.jumpserver.org/zh/v2/faq/v2_timeline/)，V2 社区版已于 2023 年 12 月 31 日结束维护，V2 企业版已于 2025 年 12 月 31 日结束维护。

## 报告安全漏洞

如果您发现 JumpServer 存在安全漏洞，欢迎通过 GitHub Security Advisories 私密提交漏洞报告：

[漏洞报告](https://github.com/jumpserver/jumpserver/security/advisories)

提交时请尽可能提供漏洞描述、影响版本、复现步骤及 PoC，以便我们快速评估和修复。

请勿通过公开的 GitHub Issues、Discussions 或 Pull Requests 披露尚未修复的安全漏洞。

您也可以通过以下邮箱联系我们：

* ibuler@fit2cloud.com
* support@lxware.hk

感谢您帮助 JumpServer 变得更加安全！

⸻

# Security Policy

JumpServer is an open-source Privileged Access Management (PAM) platform. Please follow our [Security Recommendations](https://docs.fit2cloud.com/jumpserver/faq/security/) to ensure a secure deployment.

## Supported Versions

Current version maintenance status:

| Version | Status | Supported |
| --- | --- | --- |
| 5.x | Active | Yes |
| 4.10.x | LTS | Yes |
| 3.10.x | Legacy | Critical fixes only |
| 3.9.x and earlier | EOL | No |

V3 maintenance covers only 3.10.x and is limited to critical fixes. Community Edition (CE) reaches end of life on **December 31, 2026**, and Enterprise Edition (EE) on **December 31, 2028**. Bug fixes and security updates will no longer be provided for each edition after its end-of-life date.

Use the latest patch release of a maintained series. A maintained series does not mean that every historical patch release is free of known vulnerabilities. See the [security announcements](https://www.jumpserver.org/security.html) for known vulnerabilities and fixed versions, and the [releases](https://github.com/jumpserver/jumpserver/releases) for available versions.

As stated in the [V2 lifecycle notice](https://docs.jumpserver.org/zh/v2/faq/v2_timeline/), V2 Community Edition reached end of life on December 31, 2023, and V2 Enterprise Edition on December 31, 2025.

## Reporting a Vulnerability

If you discover a security vulnerability in JumpServer, please report it privately through GitHub Security Advisories:

[Report a Vulnerability](https://github.com/jumpserver/jumpserver/security/advisories)

Please include a description of the vulnerability, affected versions, reproduction steps, and a proof of concept (PoC), if available.

Do not disclose unpatched vulnerabilities through public GitHub Issues, Discussions, or Pull Requests.

Alternatively, you can contact us via email:

* ibuler@fit2cloud.com
* support@lxware.hk

Thank you for helping keep JumpServer secure!

