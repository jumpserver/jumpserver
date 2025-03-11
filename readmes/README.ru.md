<div align="center">
  <a name="readme-top"></a>
  <a href="https://jumpserver.org/index-en.html"><img src="https://download.jumpserver.org/images/jumpserver-logo.svg" alt="JumpServer" width="300" /></a>
  
## Что такое JumpServer?

JumpServer – это инструмент управления привилегированным доступом с открытым исходным кодом (PAM), который предоставляет командам DevOps и IT по требованию безопасный доступ к точкам SSH, RDP, Kubernetes, базам данных и RemoteApp через веб-браузер.

![Обзор JumpServer](https://github.com/jumpserver/jumpserver/assets/32935519/35a371cb-8590-40ed-88ec-f351f8cf9045)

## Быстрый старт

Подготовьте чистый сервер Linux ( 64 бита, >= 4c8g )

```sh
curl -sSL https://github.com/jumpserver/jumpserver/releases/latest/download/quick_start.sh | bash
```

Доступ к JumpServer в вашем браузере по адресу `http://your-jumpserver-ip/`
- Имя пользователя: `admin`
- Пароль: `ChangeMe`

[![Быстрый старт JumpServer](https://github.com/user-attachments/assets/0f32f52b-9935-485e-8534-336c63389612)](https://www.youtube.com/watch?v=UlGYRbKrpgY "Быстрый старт JumpServer")

## Скриншоты

<table style="border-collapse: collapse; border: 1px solid black;">
  <tr>
    <td style="padding: 5px;background-color:#fff;"><img src= "https://github.com/jumpserver/jumpserver/assets/32935519/99fabe5b-0475-4a53-9116-4c370a1426c4" alt="Консоль JumpServer"   /></td>
    <td style="padding: 5px;background-color:#fff;"><img src= "https://github.com/jumpserver/jumpserver/assets/32935519/a424d731-1c70-4108-a7d8-5bbf387dda9a" alt="Аудиты JumpServer"   /></td>
  </tr>

  <tr>
    <td style="padding: 5px;background-color:#fff;"><img src= "https://github.com/jumpserver/jumpserver/assets/32935519/393d2c27-a2d0-4dea-882d-00ed509e00c9" alt="Рабочая среда JumpServer"   /></td>
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

JumpServer состоит из нескольких ключевых компонентов, которые вместе формируют функциональную структуру JumpServer, обеспечивая пользователей комплексными возможностями для управления операциями и контроля безопасности.

| Проект                                                | Статус                                                                                                                                                                 | Описание                                                                                             |
|--------------------------------------------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------------------|
| [Lina](https://github.com/jumpserver/lina)             | <a href="https://github.com/jumpserver/lina/releases"><img alt="Выпуск Lina" src="https://img.shields.io/github/release/jumpserver/lina.svg" /></a>                   | Веб-интерфейс JumpServer                                                                                       |
| [Luna](https://github.com/jumpserver/luna)             | <a href="https://github.com/jumpserver/luna/releases"><img alt="Выпуск Luna" src="https://img.shields.io/github/release/jumpserver/luna.svg" /></a>                   | Веб-терминал JumpServer                                                                                 |
| [KoKo](https://github.com/jumpserver/koko)             | <a href="https://github.com/jumpserver/koko/releases"><img alt="Выпуск Koko" src="https://img.shields.io/github/release/jumpserver/koko.svg" /></a>                   | Коннектор протокола символов JumpServer                                                                 |
| [Lion](https://github.com/jumpserver/lion)             | <a href="https://github.com/jumpserver/lion/releases"><img alt="Выпуск Lion" src="https://img.shields.io/github/release/jumpserver/lion.svg" /></a>                   | Коннектор графического протокола JumpServer                                                                 |
| [Chen](https://github.com/jumpserver/chen)             | <a href="https://github.com/jumpserver/chen/releases"><img alt="Выпуск Chen" src="https://img.shields.io/github/release/jumpserver/chen.svg" />                       | Веб-БД JumpServer                                                                                       |  
| [Razor](https://github.com/jumpserver/razor)           | <img alt="Chen" src="https://img.shields.io/badge/release-private-red" />                                                                                              | Коннектор Proxy RDP JumpServer EE                                                                       |
| [Tinker](https://github.com/jumpserver/tinker)         | <img alt="Tinker" src="https://img.shields.io/badge/release-private-red" />                                                                                            | Коннектор удаленного приложения JumpServer EE (Windows)                                                    |
| [Panda](https://github.com/jumpserver/Panda)           | <img alt="Panda" src="https://img.shields.io/badge/release-private-red" />                                                                                             | Коннектор удаленного приложения JumpServer EE (Linux)                                                      |
| [Magnus](https://github.com/jumpserver/magnus)         | <img alt="Magnus" src="https://img.shields.io/badge/release-private-red" />                                                                                            | Коннектор Proxy базы данных JumpServer EE                                                                  |
| [Nec](https://github.com/jumpserver/nec)               | <img alt="Nec" src="https://img.shields.io/badge/release-private-red" />                                                                                               | Коннектор Proxy VNC JumpServer EE                                                                       |
| [Facelive](https://github.com/jumpserver/facelive)     | <img alt="Facelive" src="https://img.shields.io/badge/release-private-red" />                                                                                          | Удаленное распознавание лиц JumpServer EE                                                                        |


## Участие

Добро пожаловать, чтобы отправить PR для участия. Пожалуйста, обратитесь к [CONTRIBUTING.md][contributing-link] для получения рекомендаций.

## Безопасность

JumpServer – это продукт критической важности. Пожалуйста, обратитесь к Основным рекомендациям по безопасности для установки и развертывания. Если у вас возникли проблемы, связанные с безопасностью, пожалуйста, свяжитесь с нами напрямую:

- Email: support@fit2cloud.com

## Лицензия

Copyright (c) 2014-2025 FIT2CLOUD, Все права защищены.

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

<!-- Image link -->