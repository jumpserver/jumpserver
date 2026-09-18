<div align="center">
  <a name="readme-top"></a>
  <a href="https://jumpserver.com" target="_blank"><img src="https://download.jumpserver.org/images/jumpserver-logo.svg" alt="JumpServer" width="300" /></a>
  
## 오픈 소스 특권 접근 관리(PAM) 플랫폼(배스천 호스트)

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

## JumpServer란?

JumpServer는 AI 기능을 갖춘 오픈 소스 특권 접근 관리(PAM) 플랫폼입니다. DevOps 및 IT 팀이 SSH, RDP, Kubernetes, 데이터베이스, 웹사이트, RemoteApp, VirtualApp 등에 안전하게 접근할 수 있는 통합 작업 공간을 제공합니다.

<img alt="JumpServer 아키텍처 다이어그램" src="https://github.com/user-attachments/assets/2bbf0979-4e1e-43ea-8dac-5d3e3bfbf1d1" />

## 빠른 시작

CPU 코어 4개 이상, 메모리 8 GB 이상을 갖춘 깨끗한 64비트 Linux 서버를 준비하세요.

```sh
curl -sSL https://github.com/jumpserver/jumpserver/releases/latest/download/quick_start.sh | bash
```

브라우저에서 JumpServer에 접속하세요: `http://your-jumpserver-ip/`

- 사용자 이름: `admin`
- 비밀번호: `ChangeMe`

## 스크린샷

<p align="center"><img src="assets/jumpserver-screenshots.gif" alt="콘솔, PAM, 터미널, 원격 데스크톱, 데이터베이스 화면을 차례로 보여 주는 JumpServer 애니메이션" width="95%" /></p>

## 구성 요소

JumpServer의 구성 요소는 역할에 따라 구분됩니다. 핵심 프로젝트는 플랫폼, 웹 인터페이스, 터미널, 프로토콜 연결 및 AI 기능을 제공합니다. 엔터프라이즈 구성 요소는 애플리케이션과 프로토콜 접근을 확장합니다. 지원 서비스는 세션 녹화와 호스트 운영을 담당하고, 배포 도구는 설치와 웹 콘텐츠 제공을 간소화합니다.

### 핵심 프로젝트

<table width="100%">
  <thead>
    <tr>
      <th width="160" align="left">프로젝트</th>
      <th width="135" align="center"><div align="center">버전</div></th>
      <th align="center"><div align="center">설명</div></th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td width="160" align="left" nowrap><a href="https://github.com/jumpserver/jumpserver">JumpServer</a></td>
      <td width="135" align="center"><div align="center"><a href="https://github.com/jumpserver/jumpserver/tags"><img src="https://img.shields.io/github/v/tag/jumpserver/jumpserver?sort=semver&amp;filter=v5.*&amp;label=tag" alt="JumpServer 버전" /></a></div></td>
      <td align="left">오픈 소스 특권 접근 관리 플랫폼</td>
    </tr>
    <tr>
      <td width="160" align="left" nowrap><a href="https://github.com/jumpserver/lina">Lina</a></td>
      <td width="135" align="center"><div align="center"><a href="https://github.com/jumpserver/lina/tags"><img src="https://img.shields.io/github/v/tag/jumpserver/lina?sort=semver&amp;filter=v5.*&amp;label=tag" alt="Lina 버전" /></a></div></td>
      <td align="left">JumpServer 웹 인터페이스</td>
    </tr>
    <tr>
      <td width="160" align="left" nowrap><a href="https://github.com/jumpserver/luna">Luna</a></td>
      <td width="135" align="center"><div align="center"><a href="https://github.com/jumpserver/luna/tags"><img src="https://img.shields.io/github/v/tag/jumpserver/luna?sort=semver&amp;filter=v5.*&amp;label=tag" alt="Luna 버전" /></a></div></td>
      <td align="left">JumpServer 웹 터미널 및 네이티브 클라이언트</td>
    </tr>
    <tr>
      <td width="160" align="left" nowrap><a href="https://github.com/jumpserver/koko">KoKo</a></td>
      <td width="135" align="center"><div align="center"><a href="https://github.com/jumpserver/koko/tags"><img src="https://img.shields.io/github/v/tag/jumpserver/koko?sort=semver&amp;filter=v5.*&amp;label=tag" alt="KoKo 버전" /></a></div></td>
      <td align="left">JumpServer 범용 프로토콜 커넥터 및 프록시</td>
    </tr>
    <tr>
      <td width="160" align="left" nowrap><a href="https://github.com/jumpserver/chen">Chen</a></td>
      <td width="135" align="center"><div align="center"><a href="https://github.com/jumpserver/chen/tags"><img src="https://img.shields.io/github/v/tag/jumpserver/chen?sort=semver&amp;filter=v5.*&amp;label=tag" alt="Chen 버전" /></a></div></td>
      <td align="left">JumpServer 웹 데이터베이스 커넥터</td>
    </tr>
    <tr>
      <td width="160" align="left" nowrap><a href="https://github.com/jumpserver/kael">Kael</a></td>
      <td width="135" align="center"><div align="center"><a href="https://github.com/jumpserver/kael/tags"><img src="https://img.shields.io/github/v/tag/jumpserver/kael?sort=semver&amp;filter=v5.*&amp;label=tag" alt="Kael 버전" /></a></div></td>
      <td align="left">JumpServer AI 구성 요소</td>
    </tr>
  </tbody>
</table>

### 엔터프라이즈 구성 요소

<table width="100%">
  <thead>
    <tr>
      <th width="160" align="left">프로젝트</th>
      <th width="135" align="center"><div align="center">버전</div></th>
      <th align="center"><div align="center">설명</div></th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td width="160" align="left" nowrap><a href="https://github.com/jumpserver/tinker">Tinker</a></td>
      <td width="135" align="center"><div align="center"><img src="https://img.shields.io/badge/tag-private-red" alt="비공개 버전" /></div></td>
      <td align="left">JumpServer Windows 애플리케이션 커넥터(커뮤니티 에디션에서 무료)</td>
    </tr>
    <tr>
      <td width="160" align="left" nowrap><a href="https://github.com/jumpserver/Panda">Panda</a></td>
      <td width="135" align="center"><div align="center"><img src="https://img.shields.io/badge/tag-private-red" alt="비공개 버전" /></div></td>
      <td align="left">JumpServer 엔터프라이즈 에디션 Linux 애플리케이션 커넥터</td>
    </tr>
    <tr>
      <td width="160" align="left" nowrap><a href="https://github.com/jumpserver/razor">Razor</a></td>
      <td width="135" align="center"><div align="center"><img src="https://img.shields.io/badge/tag-private-red" alt="비공개 버전" /></div></td>
      <td align="left">JumpServer 엔터프라이즈 에디션 RDP 프로토콜 프록시</td>
    </tr>
    <tr>
      <td width="160" align="left" nowrap><a href="https://github.com/jumpserver/magnus">Magnus</a></td>
      <td width="135" align="center"><div align="center"><img src="https://img.shields.io/badge/tag-private-red" alt="비공개 버전" /></div></td>
      <td align="left">JumpServer 엔터프라이즈 에디션 데이터베이스 프로토콜 프록시</td>
    </tr>
    <tr>
      <td width="160" align="left" nowrap><a href="https://github.com/jumpserver/nec">Nec</a></td>
      <td width="135" align="center"><div align="center"><img src="https://img.shields.io/badge/tag-private-red" alt="비공개 버전" /></div></td>
      <td align="left">JumpServer 엔터프라이즈 에디션 VNC 프로토콜 프록시</td>
    </tr>
  </tbody>
</table>

### 지원 서비스

<table width="100%">
  <thead>
    <tr>
      <th width="160" align="left">프로젝트</th>
      <th width="135" align="center"><div align="center">버전</div></th>
      <th align="center"><div align="center">설명</div></th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td width="160" align="left" nowrap><a href="https://github.com/jumpserver/video-worker">Video&nbsp;Worker</a></td>
      <td width="135" align="center"><div align="center"><img src="https://img.shields.io/badge/tag-private-red" alt="비공개 버전" /></div></td>
      <td align="left">JumpServer 엔터프라이즈 에디션 세션 녹화 트랜스코딩 서비스</td>
    </tr>
    <tr>
      <td width="160" align="left" nowrap><a href="https://github.com/jumpserver/jdmc">JDMC</a></td>
      <td width="135" align="center"><div align="center"><img src="https://img.shields.io/badge/tag-private-red" alt="비공개 버전" /></div></td>
      <td align="left">JumpServer 엔터프라이즈 에디션 호스트 운영 및 관리 서비스</td>
    </tr>
  </tbody>
</table>

### 배포 및 도구

<table width="100%">
  <thead>
    <tr>
      <th width="160" align="left">프로젝트</th>
      <th width="135" align="center"><div align="center">버전</div></th>
      <th align="center"><div align="center">설명</div></th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td width="160" align="left" nowrap><a href="https://github.com/jumpserver/installer">Installer</a></td>
      <td width="135" align="center"><div align="center"><a href="https://github.com/jumpserver/installer/tags"><img src="https://img.shields.io/github/v/tag/jumpserver/installer?sort=semver&amp;filter=v5.*&amp;label=tag" alt="Installer 버전" /></a></div></td>
      <td align="left">JumpServer 설치 및 관리 도구</td>
    </tr>
    <tr>
      <td width="160" align="left" nowrap><a href="https://github.com/jumpserver/docker-web">Docker&nbsp;Web</a></td>
      <td width="135" align="center"><div align="center"><a href="https://github.com/jumpserver/docker-web/tags"><img src="https://img.shields.io/github/v/tag/jumpserver/docker-web?sort=semver&amp;filter=v5.*&amp;label=tag" alt="Docker Web 버전" /></a></div></td>
      <td align="left">JumpServer 웹 게이트웨이 및 정적 자산</td>
    </tr>
  </tbody>
</table>

## 기여

기여를 환영합니다. 자세한 내용은 [CONTRIBUTING.md][contributing-link]를 참고하세요.

## 라이선스

Copyright (c) 2014-2026 FIT2CLOUD. All rights reserved.

이 프로젝트는 GNU 일반 공중 사용 허가서 버전 3(GPLv3, 이하 '라이선스')에 따라 제공됩니다. 이 파일은 라이선스를 준수하는 경우에만 사용할 수 있습니다. 라이선스 사본은 다음 주소에서 확인할 수 있습니다.

https://www.gnu.org/licenses/gpl-3.0.html

관련 법률에서 요구하거나 서면으로 달리 합의한 경우를 제외하고, 라이선스에 따라 배포되는 소프트웨어는 명시적 또는 묵시적인 어떠한 보증이나 조건 없이 '있는 그대로' 제공됩니다. 권한과 제한 사항은 라이선스의 구체적인 내용을 참고하세요.

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
