<div align="center">
  <a name="readme-top"></a>
  <a href="https://jumpserver.com" target="_blank"><img src="https://download.jumpserver.org/images/jumpserver-logo.svg" alt="JumpServer" width="300" /></a>
  
## Инструмент PAM с открытым исходным кодом (Bastion Host)

</div>
<br/>

## Что такое JumpServer?

JumpServer - это инструмент управления привилегированным доступом (PAM) с открытым исходным кодом, который предоставляет командам DevOps и ИТ безопасный доступ по запросу к конечным точкам SSH, RDP, Kubernetes, базам данных и RemoteApp через веб-браузер.


<picture>
  <source media="(prefers-color-scheme: light)" srcset="https://github.com/user-attachments/assets/dd612f3d-c958-4f84-b164-f31b75454d7f">
  <source media="(prefers-color-scheme: dark)" srcset="https://github.com/user-attachments/assets/28676212-2bc4-4a9f-ae10-3be9320647e3">
  <img src="https://github.com/user-attachments/assets/dd612f3d-c958-4f84-b164-f31b75454d7f" alt="Изображение на основе темы">
</picture>


## Быстрый старт

Подготовьте чистый сервер Linux (64 бит, >= 4c8g)

```sh
curl -sSL https://github.com/jumpserver/jumpserver/releases/latest/download/quick_start.sh | bash
```

Получите доступ к JumpServer в вашем браузере по адресу `http://your-jumpserver-ip/`
- Имя пользователя: `admin`
- Пароль: `ChangeMe`

[![JumpServer Quickstart](https://github.com/user-attachments/assets/0f32f52b-9935-485e-8534-336c63389612)](https://www.youtube.com/watch?v=UlGYRbKrpgY "JumpServer Quickstart")

## Скриншоты
<table style="border-collapse: collapse; border: 1px solid black;">
  <tr>
    <td style="padding: 5px;background-color:#fff;"><img src= "https://github.com/jumpserver/jumpserver/assets/32935519/99fabe5b-0475-4a53-9116-4c370a1426c4" alt="Консоль JumpServer"   /></td>
    <td style="padding: 5px;background-color:#fff;"><img src= "https://github.com/user-attachments/assets/7c1f81af-37e8-4f07-8ac9-182895e1062e" alt="JumpServer PAM"   /></td>    
  </tr>
  <tr>
    <td style="padding: 5px;background-color:#fff;"><img src= "https://github.com/jumpserver/jumpserver/assets/32935519/a424d731-1c70-4108-a7d8-5bbf387dda9a" alt="Аудиты JumpServer"   /></td>
    <td style="padding: 5px;background-color:#fff;"><img src= "https://github.com/jumpserver/jumpserver/assets/32935519/393d2c27-a2d0-4dea-882d-00ed509e00c9" alt="Рабочая станция JumpServer"   /></td>
  </tr>
  <tr>
    <td style="padding: 5px;background-color:#fff;"><img src= "https://github.com/user-attachments/assets/eaa41f66-8cc8-4f01-a001-0d258501f1c9" alt="RBAC JumpServer"   /></td>     
    <td style="padding: 5px;background-color:#fff;"><img src= "https://github.com/jumpserver/jumpserver/assets/32935519/3a2611cd-8902-49b8-b82b-2a6dac851f3e" alt="Настройки JumpServer"   /></td>
  </tr>
  <tr>
    <td style="padding: 5px;background-color:#fff;"><img src= "https://github.com/jumpserver/jumpserver/assets/32935519/1e236093-31f7-4563-8eb1-e36d865f1568" alt="SSH JumpServer"   /></td>
    <td style="padding: 5px;background-color:#fff;"><img src= "https://github.com/jumpserver/jumpserver/assets/32935519/69373a82-f7ab-41e8-b763-bbad2ba52167" alt="RDP JumpServer"   /></td>
  </tr>
  <tr>
    <td style="padding: 5px;background-color:#fff;"><img src= "https://github.com/jumpserver/jumpserver/assets/32935519/5bed98c6-cbe8-4073-9597-d53c69dc3957" alt="K8s JumpServer"   /></td>
    <td style="padding: 5px;background-color:#fff;"><img src= "https://github.com/jumpserver/jumpserver/assets/32935519/b80ad654-548f-42bc-ba3d-c1cfdf1b46d6" alt="DB JumpServer"   /></td>
  </tr>
</table>

## Компоненты

JumpServer состоит из нескольких ключевых компонентов, которые вместе формируют функциональную структуру JumpServer, предоставляя пользователям широкие возможности для управления операциями и контроля безопасности.

| Проект                                                 | Статус                                                                                                                                                                 | Описание                                                                                             |
|--------------------------------------------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------------------|
| [Lina](https://github.com/jumpserver/lina)             | <a href="https://github.com/jumpserver/lina/releases"><img alt="Выпуск Lina" src="https://img.shields.io/github/release/jumpserver/lina.svg" /></a>                   | Веб-интерфейс JumpServer                                                                                |
| [Luna](https://github.com/jumpserver/luna)             | <a href="https://github.com/jumpserver/luna/releases"><img alt="Выпуск Luna" src="https://img.shields.io/github/release/jumpserver/luna.svg" /></a>                   | Веб-терминал JumpServer                                                                                 |
| [KoKo](https://github.com/jumpserver/koko)             | <a href="https://github.com/jumpserver/koko/releases"><img alt="Выпуск Koko" src="https://img.shields.io/github/release/jumpserver/koko.svg" /></a>                   | Коннектор протокола символов JumpServer                                                                 |
| [Lion](https://github.com/jumpserver/lion)             | <a href="https://github.com/jumpserver/lion/releases"><img alt="Выпуск Lion" src="https://img.shields.io/github/release/jumpserver/lion.svg" /></a>                   | Коннектор графического протокола JumpServer                                                             |
| [Chen](https://github.com/jumpserver/chen)             | <a href="https://github.com/jumpserver/chen/releases"><img alt="Выпуск Chen" src="https://img.shields.io/github/release/jumpserver/chen.svg" />                       | Веб-база данных JumpServer                                                                              |  
| [Tinker](https://github.com/jumpserver/tinker)         | <img alt="Tinker" src="https://img.shields.io/badge/release-private-red" />                                                                                            | Коннектор удаленного приложения JumpServer (Windows)                                                  |
| [Panda](https://github.com/jumpserver/Panda)           | <img alt="Panda" src="https://img.shields.io/badge/release-private-red" />                                                                                             | Коннектор удаленного приложения JumpServer EE (Linux)                                                  |
| [Razor](https://github.com/jumpserver/razor)           | <img alt="Chen" src="https://img.shields.io/badge/release-private-red" />                                                                                              | Коннектор прокси RDP JumpServer EE                                                                       |
| [Magnus](https://github.com/jumpserver/magnus)         | <img alt="Magnus" src="https://img.shields.io/badge/release-private-red" />                                                                                            | Коннектор прокси базы данных JumpServer EE                                                                |
| [Nec](https://github.com/jumpserver/nec)               | <img alt="Nec" src="https://img.shields.io/badge/release-private-red" />                                                                                               | Коннектор прокси VNC JumpServer EE                                                                       |
| [Facelive](https://github.com/jumpserver/facelive)     | <img alt="Facelive" src="https://img.shields.io/badge/release-private-red" />                                                                                          | Коннектор распознавания лиц JumpServer EE                                                                |


## Участие

Добро пожаловать, чтобы подать PR для участия. Пожалуйста, ознакомьтесь с [CONTRIBUTING.md][contributing-link] для получения рекомендаций.

## License

Copyright (c) 2014-2025 FIT2CLOUD, All rights reserved.

Licensed under The GNU General Public License version 3 (GPLv3) (the "License"); you may not use this file except in compliance with the License. You may obtain a copy of the License at

https://www.gnu.org/licenses/gpl-3.0.html

Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on an " AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the specific language governing permissions and limitations under the License.

<!-- JumpServer official link -->
[docs-link]: https://jumpserver.com/docs
[discord-link]: https://discord.com/invite/W6vYXmAQG2
[contributing-link]: https://github.com/jumpserver/jumpserver/blob/dev/CONTRIBUTING.md

<!-- JumpServer Other link-->
[license-link]: https://www.gnu.org/licenses/gpl-3.0.html
[docker-link]: https://hub.docker.com/u/jumpserver
[github-release-link]: https://github.com/jumpserver/jumpserver/releases/latest
[github-stars-link]: https://github.com/jumpserver/jumpserver
[github-issues-link]: https://github.com/jumpserver/jumpserver/issues

<!-- Shield link-->
[github-release-shield]: https://img.shields.io/github/v/release/jumpserver/jumpserver
[github-stars-shield]: https://img.shields.io/github/stars/jumpserver/jumpserver?color=%231890FF&style=flat-square
[docker-shield]: https://img.shields.io/docker/pulls/jumpserver/jms_all.svg
[license-shield]: https://img.shields.io/github/license/jumpserver/jumpserver
[discord-shield]: https://img.shields.io/discord/1194233267294052363?style=flat&logo=discord&logoColor=%23f5f5f5&labelColor=%235462eb&color=%235462eb