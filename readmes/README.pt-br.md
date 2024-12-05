<div align="center">
  <a name="readme-top"></a>
  <a href="https://jumpserver.org/index-en.html"><img src="https://download.jumpserver.org/images/jumpserver-logo.svg" alt="JumpServer" width="300" /></a>
  
## Uma ferramenta PAM de código aberto (Servidor Bastião)

[![][license-shield]][license-link]
[![][discord-shield]][discord-link]
[![][docker-shield]][docker-link]
[![][github-release-shield]][github-release-link]
[![][github-stars-shield]][github-stars-link]

[Inglês](./README.md) · [中文(简体)](./readmes/README.zh-hans.md) · [中文(繁體)](./readmes/README.zh-hant.md) · [日本語](./readmes/README.ja.md) · [Português (Brasil)](./readmes/README.pt-br.md)

</div>
<br/>

## O que é JumpServer?

JumpServer é uma ferramenta de Gerenciamento de Acesso Privilegiado (PAM) de código aberto que fornece às equipes de DevOps e TI acesso seguro e sob demanda a SSH, RDP, Kubernetes, Banco de Dados e endpoints RemoteApp através de um navegador da web.

![Visão geral do JumpServer](https://github.com/jumpserver/jumpserver/assets/32935519/35a371cb-8590-40ed-88ec-f351f8cf9045)

## Começando Rápido

Prepare um Servidor Linux limpo ( 64 bits, >= 4c8g )

```sh
curl -sSL https://github.com/jumpserver/jumpserver/releases/latest/download/quick_start.sh | bash
```

Acesse o JumpServer no seu navegador em `http://your-jumpserver-ip/`
- Nome de usuário: `admin`
- Senha: `ChangeMe`

[![JumpServer Começando Rápido](https://github.com/user-attachments/assets/0f32f52b-9935-485e-8534-336c63389612)](https://www.youtube.com/watch?v=UlGYRbKrpgY "JumpServer Começando Rápido")

## Capturas de Tela

<table style="border-collapse: collapse; border: 1px solid black;">
  <tr>
    <td style="padding: 5px;background-color:#fff;"><img src= "https://github.com/jumpserver/jumpserver/assets/32935519/99fabe5b-0475-4a53-9116-4c370a1426c4" alt="Console do JumpServer"   /></td>
    <td style="padding: 5px;background-color:#fff;"><img src= "https://github.com/jumpserver/jumpserver/assets/32935519/a424d731-1c70-4108-a7d8-5bbf387dda9a" alt="Auditorias do JumpServer"   /></td>
  </tr>

  <tr>
    <td style="padding: 5px;background-color:#fff;"><img src= "https://github.com/jumpserver/jumpserver/assets/32935519/393d2c27-a2d0-4dea-882d-00ed509e00c9" alt="Banco de Trabalho do JumpServer"   /></td>
    <td style="padding: 5px;background-color:#fff;"><img src= "https://github.com/jumpserver/jumpserver/assets/32935519/3a2611cd-8902-49b8-b82b-2a6dac851f3e" alt="Configurações do JumpServer"   /></td>
  </tr>

  <tr>
    <td style="padding: 5px;background-color:#fff;"><img src= "https://github.com/jumpserver/jumpserver/assets/32935519/1e236093-31f7-4563-8eb1-e36d865f1568" alt="SSH do JumpServer"   /></td>
    <td style="padding: 5px;background-color:#fff;"><img src= "https://github.com/jumpserver/jumpserver/assets/32935519/69373a82-f7ab-41e8-b763-bbad2ba52167" alt="RDP do JumpServer"   /></td>
  </tr>
  <tr>
    <td style="padding: 5px;background-color:#fff;"><img src= "https://github.com/jumpserver/jumpserver/assets/32935519/5bed98c6-cbe8-4073-9597-d53c69dc3957" alt="K8s do JumpServer"   /></td>
    <td style="padding: 5px;background-color:#fff;"><img src= "https://github.com/jumpserver/jumpserver/assets/32935519/b80ad654-548f-42bc-ba3d-c1cfdf1b46d6" alt="DB do JumpServer"   /></td>
  </tr>
</table>

## Componentes

JumpServer consiste em vários componentes chave, que juntos formam a estrutura funcional do JumpServer, fornecendo aos usuários capacidades abrangentes para gerenciamento de operações e controle de segurança.

| Projeto                                                | Status                                                                                                                                                                 | Descrição                                                                                             |
|--------------------------------------------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------------------|
| [Lina](https://github.com/jumpserver/lina)             | <a href="https://github.com/jumpserver/lina/releases"><img alt="Lina release" src="https://img.shields.io/github/release/jumpserver/lina.svg" /></a>                   | Interface Web do JumpServer                                                                             |
| [Luna](https://github.com/jumpserver/luna)             | <a href="https://github.com/jumpserver/luna/releases"><img alt="Luna release" src="https://img.shields.io/github/release/jumpserver/luna.svg" /></a>                   | Terminal Web do JumpServer                                                                               |
| [KoKo](https://github.com/jumpserver/koko)             | <a href="https://github.com/jumpserver/koko/releases"><img alt="Koko release" src="https://img.shields.io/github/release/jumpserver/koko.svg" /></a>                   | Conector do Protocolo de Caracteres do JumpServer                                                      |
| [Lion](https://github.com/jumpserver/lion)             | <a href="https://github.com/jumpserver/lion/releases"><img alt="Lion release" src="https://img.shields.io/github/release/jumpserver/lion.svg" /></a>                   | Conector de Protocolo Gráfico do JumpServer                                                             |
| [Chen](https://github.com/jumpserver/chen)             | <a href="https://github.com/jumpserver/chen/releases"><img alt="Chen release" src="https://img.shields.io/github/release/jumpserver/chen.svg" />                       | Banco de Dados Web do JumpServer                                                                          |  
| [Razor](https://github.com/jumpserver/razor)           | <img alt="Chen" src="https://img.shields.io/badge/release-private-red" />                                                                                              | Conector do Proxy RDP do JumpServer EE                                                                  |
| [Tinker](https://github.com/jumpserver/tinker)         | <img alt="Tinker" src="https://img.shields.io/badge/release-private-red" />                                                                                            | Conector de Aplicação Remota do JumpServer EE (Windows)                                                |
| [Panda](https://github.com/jumpserver/Panda)           | <img alt="Panda" src="https://img.shields.io/badge/release-private-red" />                                                                                             | Conector de Aplicação Remota do JumpServer EE (Linux)                                                  |
| [Magnus](https://github.com/jumpserver/magnus)         | <img alt="Magnus" src="https://img.shields.io/badge/release-private-red" />                                                                                            | Conector do Proxy de Banco de Dados do JumpServer EE                                                    |
| [Nec](https://github.com/jumpserver/nec)               | <img alt="Nec" src="https://img.shields.io/badge/release-private-red" />                                                                                               | Conector do Proxy VNC do JumpServer EE                                                                   |
| [Facelive](https://github.com/jumpserver/facelive)     | <img alt="Facelive" src="https://img.shields.io/badge/release-private-red" />                                                                                          | Reconhecimento Facial do JumpServer EE                                                                    |


## Contribuindo

Bem-vindo para enviar PR para contribuir. Por favor, consulte [CONTRIBUTING.md][contributing-link] para diretrizes.

## Segurança

JumpServer é um produto crítico para a missão. Por favor, consulte as Recomendações Básicas de Segurança para instalação e implantação. Se você encontrar quaisquer problemas relacionados à segurança, entre em contato conosco diretamente:

- E-mail: support@fit2cloud.com

## License

Copyright (c) 2014-2024 FIT2CLOUD, All rights reserved.

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