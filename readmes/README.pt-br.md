<div align="center">
  <a name="readme-top"></a>
  <a href="https://jumpserver.com" target="_blank"><img src="https://download.jumpserver.org/images/jumpserver-logo.svg" alt="JumpServer" width="300" /></a>
  
## Uma plataforma de PAM de código aberto (Bastion Host)

</div>
<br/>

## O que é JumpServer?

JumpServer é uma plataforma de gerenciamento de acesso privilegiado (PAM) de código aberto com recursos de IA que oferece às equipes de DevOps e TI um espaço de trabalho unificado para acessar com segurança SSH, RDP, Kubernetes, bancos de dados, sites, RemoteApp, VirtualApp e muito mais.

<img alt="Diagrama de arquitetura do JumpServer" src="https://github.com/user-attachments/assets/2bbf0979-4e1e-43ea-8dac-5d3e3bfbf1d1" />

## Início rápido

Prepare um Servidor Linux limpo ( 64 bits, >= 4c8g )

```sh
curl -sSL https://github.com/jumpserver/jumpserver/releases/latest/download/quick_start.sh | bash
```

Acesse o JumpServer em seu navegador em `http://your-jumpserver-ip/`
- Nome de usuário: `admin`
- Senha: `ChangeMe`


## Capturas de tela
<table style="border-collapse: collapse; border: 1px solid black;">
  <tr>
    <td style="padding: 5px;background-color:#fff;"><img src= "https://github.com/user-attachments/assets/6164c92a-0b19-405a-b79c-73e28a9a1610" alt="Console do JumpServer"   /></td>
    <td style="padding: 5px;background-color:#fff;"><img src= "https://github.com/user-attachments/assets/12d1206d-b511-4f29-8b00-fd13333f3a21" alt="JumpServer PAM"   /></td>
  </tr>
  <tr>
    <td style="padding: 5px;background-color:#fff;"><img src= "https://github.com/user-attachments/assets/6d12d3c9-5f31-4294-b6e7-7c5b5836f688" alt="Auditorias do JumpServer"   /></td>
    <td style="padding: 5px;background-color:#fff;"><img src= "https://github.com/user-attachments/assets/ba784bc8-e889-4fd6-aaae-0b8b14153da2" alt="Banco de Trabalho do JumpServer"   /></td>
  </tr>
  <tr>
    <td style="padding: 5px;background-color:#fff;"><img src= "https://github.com/user-attachments/assets/d4b10b15-bccb-4a0d-a6e6-74a6439614e0" alt="RBAC do JumpServer"   /></td>
    <td style="padding: 5px;background-color:#fff;"><img src= "https://github.com/user-attachments/assets/ccbeb96e-9747-4182-bd03-031fb3af8bb2" alt="Configurações do JumpServer"   /></td>
  </tr>
  <tr>
    <td style="padding: 5px;background-color:#fff;"><img src= "https://github.com/user-attachments/assets/9049888e-16fe-4fbe-b0f2-16bf140379c8" alt="RBAC do JumpServer"   /></td>
    <td style="padding: 5px;background-color:#fff;"><img src= "https://github.com/user-attachments/assets/133c4af6-90a9-457d-b372-bb53c29260dc" alt="Configurações do JumpServer"   /></td>
  </tr>
  <tr>
    <td style="padding: 5px;background-color:#fff;"><img src= "https://github.com/user-attachments/assets/ea48738f-b5f8-4a43-a487-ca09b11176e7" alt="RBAC do JumpServer"   /></td>
    <td style="padding: 5px;background-color:#fff;"><img src= "https://github.com/user-attachments/assets/3407539f-1235-4dcc-adf2-26d7b60dbc67" alt="Configurações do JumpServer"   /></td>
  </tr>
</table>

## Componentes

JumpServer consiste em múltiplos componentes principais, que coletivamente formam a estrutura funcional do JumpServer, proporcionando aos usuários capacidades abrangentes para gerenciamento de operações e controle de segurança.

## Projetos

### Projetos principais

| Projeto | Versão | Descrição |
| --- | --- | --- |
| [JumpServer](https://github.com/jumpserver/jumpserver) | [![tag](https://img.shields.io/github/v/tag/jumpserver/jumpserver?sort=semver&filter=v5.*&label=tag)](https://github.com/jumpserver/jumpserver/tags) | Plataforma de gerenciamento de acesso privilegiado de código aberto |
| [Lina](https://github.com/jumpserver/lina) | [![tag](https://img.shields.io/github/v/tag/jumpserver/lina?sort=semver&filter=v5.*&label=tag)](https://github.com/jumpserver/lina/tags) | Interface web do JumpServer |
| [Luna](https://github.com/jumpserver/luna) | [![tag](https://img.shields.io/github/v/tag/jumpserver/luna?sort=semver&filter=v5.*&label=tag)](https://github.com/jumpserver/luna/tags) | Terminal web e cliente nativo do JumpServer |
| [KoKo](https://github.com/jumpserver/koko) | [![tag](https://img.shields.io/github/v/tag/jumpserver/koko?sort=semver&filter=v5.*&label=tag)](https://github.com/jumpserver/koko/tags) | Conector e proxy de protocolos de uso geral do JumpServer |
| [Chen](https://github.com/jumpserver/chen) | [![tag](https://img.shields.io/github/v/tag/jumpserver/chen?sort=semver&filter=v5.*&label=tag)](https://github.com/jumpserver/chen/tags) | Conector web de bancos de dados do JumpServer |
| [Kael](https://github.com/jumpserver/kael) | [![tag](https://img.shields.io/github/v/tag/jumpserver/kael?sort=semver&filter=v5.*&label=tag)](https://github.com/jumpserver/kael/tags) | Componente de IA do JumpServer |

### Componentes empresariais

| Projeto | Versão | Descrição |
| --- | --- | --- |
| [Tinker](https://github.com/jumpserver/tinker) | ![tag](https://img.shields.io/badge/tag-private-red) | Conector de aplicativos Windows do JumpServer (gratuito para a edição comunitária) |
| [Panda](https://github.com/jumpserver/Panda) | ![tag](https://img.shields.io/badge/tag-private-red) | Conector de aplicativos Linux da edição empresarial do JumpServer |
| [Razor](https://github.com/jumpserver/razor) | ![tag](https://img.shields.io/badge/tag-private-red) | Proxy do protocolo RDP da edição empresarial do JumpServer |
| [Magnus](https://github.com/jumpserver/magnus) | ![tag](https://img.shields.io/badge/tag-private-red) | Proxy de protocolos de bancos de dados da edição empresarial do JumpServer |
| [Nec](https://github.com/jumpserver/nec) | ![tag](https://img.shields.io/badge/tag-private-red) | Proxy do protocolo VNC da edição empresarial do JumpServer |

### Serviços de apoio

| Projeto | Versão | Descrição |
| --- | --- | --- |
| [Video Worker](https://github.com/jumpserver/video-worker) | ![tag](https://img.shields.io/badge/tag-private-red) | Serviço de transcodificação de gravações de sessões da edição empresarial do JumpServer |
| [JDMC](https://github.com/jumpserver/jdmc) | ![tag](https://img.shields.io/badge/tag-private-red) | Serviço de operações e gerenciamento de hosts da edição empresarial do JumpServer |

### Implantação e ferramentas

| Projeto | Versão | Descrição |
| --- | --- | --- |
| [Installer](https://github.com/jumpserver/installer) | [![tag](https://img.shields.io/github/v/tag/jumpserver/installer?sort=semver&filter=v5.*&label=tag)](https://github.com/jumpserver/installer/tags) | Ferramenta de instalação e gerenciamento do JumpServer |
| [Docker Web](https://github.com/jumpserver/docker-web) | [![tag](https://img.shields.io/github/v/tag/jumpserver/docker-web?sort=semver&filter=v5.*&label=tag)](https://github.com/jumpserver/docker-web/tags) | Gateway web e recursos estáticos do JumpServer |

## Contribuindo

Bem-vindo para enviar PR para contribuir. Consulte [CONTRIBUTING.md][contributing-link] para diretrizes.

## License

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