<div align="center">
  <a name="readme-top"></a>
  <a href="https://jumpserver.com" target="_blank"><img src="https://download.jumpserver.org/images/jumpserver-logo.svg" alt="JumpServer" width="300" /></a>
  
## Платформа PAM с открытым исходным кодом (бастионный хост)

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

## Что такое JumpServer?

JumpServer — платформа управления привилегированным доступом (PAM) с открытым исходным кодом и возможностями ИИ. Она предоставляет командам DevOps и ИТ единое рабочее пространство для безопасного доступа к SSH, RDP, Kubernetes, базам данных, веб-сайтам, RemoteApp, VirtualApp и другим ресурсам.

<img alt="Схема архитектуры JumpServer" src="https://github.com/user-attachments/assets/2bbf0979-4e1e-43ea-8dac-5d3e3bfbf1d1" />

## Быстрый старт

Подготовьте чистый 64-разрядный сервер Linux как минимум с 4 ядрами ЦП и 8 ГБ оперативной памяти.

```sh
curl -sSL https://github.com/jumpserver/jumpserver/releases/latest/download/quick_start.sh | bash
```

Откройте JumpServer в браузере по адресу `http://your-jumpserver-ip/`

- Имя пользователя: `admin`
- Пароль: `ChangeMe`

## Снимки экрана

![Анимированная серия снимков JumpServer: консоль, PAM, терминал, удалённый рабочий стол и сеансы баз данных](assets/jumpserver-screenshots.gif)

## Компоненты

Компоненты JumpServer сгруппированы по назначению. Основные проекты обеспечивают работу платформы, веб-интерфейса, терминала, протокольных подключений и функций ИИ. Корпоративные компоненты расширяют доступ к приложениям и протоколам. Вспомогательные службы обрабатывают записи сеансов и операции с хостами, а инструменты развёртывания упрощают установку и доставку веб-ресурсов.

### Основные проекты

<table width="100%" align="center">
  <thead>
    <tr>
      <th width="160" align="left">Проект</th>
      <th width="135" align="center"><div align="center">Версия</div></th>
      <th align="center"><div align="center">Описание</div></th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td width="160" align="left" nowrap><a href="https://github.com/jumpserver/jumpserver">JumpServer</a></td>
      <td width="135" align="center"><div align="center"><a href="https://github.com/jumpserver/jumpserver/tags"><img src="https://img.shields.io/github/v/tag/jumpserver/jumpserver?sort=semver&amp;filter=v5.*&amp;label=tag" alt="JumpServer версия" /></a></div></td>
      <td align="left">Платформа управления привилегированным доступом с открытым исходным кодом</td>
    </tr>
    <tr>
      <td width="160" align="left" nowrap><a href="https://github.com/jumpserver/lina">Lina</a></td>
      <td width="135" align="center"><div align="center"><a href="https://github.com/jumpserver/lina/tags"><img src="https://img.shields.io/github/v/tag/jumpserver/lina?sort=semver&amp;filter=v5.*&amp;label=tag" alt="Lina версия" /></a></div></td>
      <td align="left">Веб-интерфейс JumpServer</td>
    </tr>
    <tr>
      <td width="160" align="left" nowrap><a href="https://github.com/jumpserver/luna">Luna</a></td>
      <td width="135" align="center"><div align="center"><a href="https://github.com/jumpserver/luna/tags"><img src="https://img.shields.io/github/v/tag/jumpserver/luna?sort=semver&amp;filter=v5.*&amp;label=tag" alt="Luna версия" /></a></div></td>
      <td align="left">Веб-терминал и нативный клиент JumpServer</td>
    </tr>
    <tr>
      <td width="160" align="left" nowrap><a href="https://github.com/jumpserver/koko">KoKo</a></td>
      <td width="135" align="center"><div align="center"><a href="https://github.com/jumpserver/koko/tags"><img src="https://img.shields.io/github/v/tag/jumpserver/koko?sort=semver&amp;filter=v5.*&amp;label=tag" alt="KoKo версия" /></a></div></td>
      <td align="left">Универсальный протокольный коннектор и прокси JumpServer</td>
    </tr>
    <tr>
      <td width="160" align="left" nowrap><a href="https://github.com/jumpserver/chen">Chen</a></td>
      <td width="135" align="center"><div align="center"><a href="https://github.com/jumpserver/chen/tags"><img src="https://img.shields.io/github/v/tag/jumpserver/chen?sort=semver&amp;filter=v5.*&amp;label=tag" alt="Chen версия" /></a></div></td>
      <td align="left">Веб-коннектор баз данных JumpServer</td>
    </tr>
    <tr>
      <td width="160" align="left" nowrap><a href="https://github.com/jumpserver/kael">Kael</a></td>
      <td width="135" align="center"><div align="center"><a href="https://github.com/jumpserver/kael/tags"><img src="https://img.shields.io/github/v/tag/jumpserver/kael?sort=semver&amp;filter=v5.*&amp;label=tag" alt="Kael версия" /></a></div></td>
      <td align="left">Компонент ИИ JumpServer</td>
    </tr>
  </tbody>
</table>

### Корпоративные компоненты

<table width="100%" align="center">
  <thead>
    <tr>
      <th width="160" align="left">Проект</th>
      <th width="135" align="center"><div align="center">Версия</div></th>
      <th align="center"><div align="center">Описание</div></th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td width="160" align="left" nowrap><a href="https://github.com/jumpserver/tinker">Tinker</a></td>
      <td width="135" align="center"><div align="center"><img src="https://img.shields.io/badge/tag-private-red" alt="Закрытая версия" /></div></td>
      <td align="left">Коннектор приложений Windows для JumpServer (бесплатно для редакции Community)</td>
    </tr>
    <tr>
      <td width="160" align="left" nowrap><a href="https://github.com/jumpserver/Panda">Panda</a></td>
      <td width="135" align="center"><div align="center"><img src="https://img.shields.io/badge/tag-private-red" alt="Закрытая версия" /></div></td>
      <td align="left">Коннектор приложений Linux для JumpServer Enterprise Edition</td>
    </tr>
    <tr>
      <td width="160" align="left" nowrap><a href="https://github.com/jumpserver/razor">Razor</a></td>
      <td width="135" align="center"><div align="center"><img src="https://img.shields.io/badge/tag-private-red" alt="Закрытая версия" /></div></td>
      <td align="left">Прокси протокола RDP для JumpServer Enterprise Edition</td>
    </tr>
    <tr>
      <td width="160" align="left" nowrap><a href="https://github.com/jumpserver/magnus">Magnus</a></td>
      <td width="135" align="center"><div align="center"><img src="https://img.shields.io/badge/tag-private-red" alt="Закрытая версия" /></div></td>
      <td align="left">Прокси протоколов баз данных для JumpServer Enterprise Edition</td>
    </tr>
    <tr>
      <td width="160" align="left" nowrap><a href="https://github.com/jumpserver/nec">Nec</a></td>
      <td width="135" align="center"><div align="center"><img src="https://img.shields.io/badge/tag-private-red" alt="Закрытая версия" /></div></td>
      <td align="left">Прокси протокола VNC для JumpServer Enterprise Edition</td>
    </tr>
  </tbody>
</table>

### Вспомогательные службы

<table width="100%" align="center">
  <thead>
    <tr>
      <th width="160" align="left">Проект</th>
      <th width="135" align="center"><div align="center">Версия</div></th>
      <th align="center"><div align="center">Описание</div></th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td width="160" align="left" nowrap><a href="https://github.com/jumpserver/video-worker">Video&nbsp;Worker</a></td>
      <td width="135" align="center"><div align="center"><img src="https://img.shields.io/badge/tag-private-red" alt="Закрытая версия" /></div></td>
      <td align="left">Служба перекодирования записей сеансов JumpServer Enterprise Edition</td>
    </tr>
    <tr>
      <td width="160" align="left" nowrap><a href="https://github.com/jumpserver/jdmc">JDMC</a></td>
      <td width="135" align="center"><div align="center"><img src="https://img.shields.io/badge/tag-private-red" alt="Закрытая версия" /></div></td>
      <td align="left">Служба эксплуатации и управления хостами JumpServer Enterprise Edition</td>
    </tr>
  </tbody>
</table>

### Развёртывание и инструменты

<table width="100%" align="center">
  <thead>
    <tr>
      <th width="160" align="left">Проект</th>
      <th width="135" align="center"><div align="center">Версия</div></th>
      <th align="center"><div align="center">Описание</div></th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td width="160" align="left" nowrap><a href="https://github.com/jumpserver/installer">Installer</a></td>
      <td width="135" align="center"><div align="center"><a href="https://github.com/jumpserver/installer/tags"><img src="https://img.shields.io/github/v/tag/jumpserver/installer?sort=semver&amp;filter=v5.*&amp;label=tag" alt="Installer версия" /></a></div></td>
      <td align="left">Инструмент установки и управления JumpServer</td>
    </tr>
    <tr>
      <td width="160" align="left" nowrap><a href="https://github.com/jumpserver/docker-web">Docker&nbsp;Web</a></td>
      <td width="135" align="center"><div align="center"><a href="https://github.com/jumpserver/docker-web/tags"><img src="https://img.shields.io/github/v/tag/jumpserver/docker-web?sort=semver&amp;filter=v5.*&amp;label=tag" alt="Docker Web версия" /></a></div></td>
      <td align="left">Веб-шлюз и статические ресурсы JumpServer</td>
    </tr>
  </tbody>
</table>

## Участие в разработке

Мы приветствуем ваш вклад. Правила участия описаны в [CONTRIBUTING.md][contributing-link].

## Лицензия

Copyright (c) 2014-2026 FIT2CLOUD. Все права защищены.

Проект распространяется на условиях GNU General Public License версии 3 (GPLv3, далее «Лицензия»). Использовать этот файл можно только в соответствии с Лицензией. Её текст доступен по адресу

https://www.gnu.org/licenses/gpl-3.0.html

Если иное не требуется применимым законодательством или не согласовано в письменной форме, программное обеспечение, распространяемое на условиях Лицензии, предоставляется «КАК ЕСТЬ» БЕЗ КАКИХ-ЛИБО ГАРАНТИЙ ИЛИ УСЛОВИЙ, явных или подразумеваемых. Конкретные права и ограничения изложены в Лицензии.

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
