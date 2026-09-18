<div align="center">
  <a name="readme-top"></a>
  <a href="https://jumpserver.com" target="_blank"><img src="https://download.jumpserver.org/images/jumpserver-logo.svg" alt="JumpServer" width="300" /></a>
  
## Una plataforma PAM de código abierto (Bastion Host)

</div>
<br/>

## ¿Qué es JumpServer?

JumpServer es una plataforma de gestión de acceso privilegiado (PAM) de código abierto con capacidades de IA que proporciona a los equipos de DevOps y TI un espacio de trabajo unificado para acceder de forma segura a SSH, RDP, Kubernetes, bases de datos, sitios web, RemoteApp, VirtualApp y más.

<img alt="Diagrama de arquitectura de JumpServer" src="https://github.com/user-attachments/assets/2bbf0979-4e1e-43ea-8dac-5d3e3bfbf1d1" />

## Inicio rápido

Prepare un servidor Linux limpio (64 bits, >= 4c8g)

```sh
curl -sSL https://github.com/jumpserver/jumpserver/releases/latest/download/quick_start.sh | bash
```

Acceda a JumpServer en su navegador en `http://su-ip-jumpserver/`
- Nombre de usuario: `admin`
- Contraseña: `ChangeMe`


## Capturas de pantalla
<table style="border-collapse: collapse; border: 1px solid black;">
  <tr>
    <td style="padding: 5px;background-color:#fff;"><img src= "https://github.com/user-attachments/assets/6164c92a-0b19-405a-b79c-73e28a9a1610" alt="Consola JumpServer"   /></td>
    <td style="padding: 5px;background-color:#fff;"><img src= "https://github.com/user-attachments/assets/12d1206d-b511-4f29-8b00-fd13333f3a21" alt="JumpServer PAM"   /></td>
  </tr>
  <tr>
    <td style="padding: 5px;background-color:#fff;"><img src= "https://github.com/user-attachments/assets/6d12d3c9-5f31-4294-b6e7-7c5b5836f688" alt="Auditorías JumpServer"   /></td>
    <td style="padding: 5px;background-color:#fff;"><img src= "https://github.com/user-attachments/assets/ba784bc8-e889-4fd6-aaae-0b8b14153da2" alt="JumpServer Workbench"   /></td>
  </tr>
  <tr>
    <td style="padding: 5px;background-color:#fff;"><img src= "https://github.com/user-attachments/assets/d4b10b15-bccb-4a0d-a6e6-74a6439614e0" alt="RBAC de JumpServer"   /></td>
    <td style="padding: 5px;background-color:#fff;"><img src= "https://github.com/user-attachments/assets/ccbeb96e-9747-4182-bd03-031fb3af8bb2" alt="Configuraciones de JumpServer"   /></td>
  </tr>
  <tr>
    <td style="padding: 5px;background-color:#fff;"><img src= "https://github.com/user-attachments/assets/9049888e-16fe-4fbe-b0f2-16bf140379c8" alt="RBAC de JumpServer"   /></td>
    <td style="padding: 5px;background-color:#fff;"><img src= "https://github.com/user-attachments/assets/133c4af6-90a9-457d-b372-bb53c29260dc" alt="Configuraciones de JumpServer"   /></td>
  </tr>
  <tr>
    <td style="padding: 5px;background-color:#fff;"><img src= "https://github.com/user-attachments/assets/ea48738f-b5f8-4a43-a487-ca09b11176e7" alt="RBAC de JumpServer"   /></td>
    <td style="padding: 5px;background-color:#fff;"><img src= "https://github.com/user-attachments/assets/3407539f-1235-4dcc-adf2-26d7b60dbc67" alt="Configuraciones de JumpServer"   /></td>
  </tr>
</table>

## Componentes

JumpServer consta de múltiples componentes clave, que en conjunto forman el marco funcional de JumpServer, proporcionando a los usuarios capacidades integrales para la gestión de operaciones y el control de seguridad.

## Proyectos

### Proyectos principales

| Proyecto | Versión | Descripción |
| --- | --- | --- |
| [JumpServer](https://github.com/jumpserver/jumpserver) | [![tag](https://img.shields.io/github/v/tag/jumpserver/jumpserver?sort=semver&filter=v5.*&label=tag)](https://github.com/jumpserver/jumpserver/tags) | Plataforma de gestión de acceso privilegiado de código abierto |
| [Lina](https://github.com/jumpserver/lina) | [![tag](https://img.shields.io/github/v/tag/jumpserver/lina?sort=semver&filter=v5.*&label=tag)](https://github.com/jumpserver/lina/tags) | Interfaz web de JumpServer |
| [Luna](https://github.com/jumpserver/luna) | [![tag](https://img.shields.io/github/v/tag/jumpserver/luna?sort=semver&filter=v5.*&label=tag)](https://github.com/jumpserver/luna/tags) | Terminal web y cliente nativo de JumpServer |
| [KoKo](https://github.com/jumpserver/koko) | [![tag](https://img.shields.io/github/v/tag/jumpserver/koko?sort=semver&filter=v5.*&label=tag)](https://github.com/jumpserver/koko/tags) | Conector y proxy de protocolos de propósito general de JumpServer |
| [Chen](https://github.com/jumpserver/chen) | [![tag](https://img.shields.io/github/v/tag/jumpserver/chen?sort=semver&filter=v5.*&label=tag)](https://github.com/jumpserver/chen/tags) | Conector web de bases de datos de JumpServer |
| [Kael](https://github.com/jumpserver/kael) | [![tag](https://img.shields.io/github/v/tag/jumpserver/kael?sort=semver&filter=v5.*&label=tag)](https://github.com/jumpserver/kael/tags) | Componente de IA de JumpServer |

### Componentes empresariales

| Proyecto | Versión | Descripción |
| --- | --- | --- |
| [Tinker](https://github.com/jumpserver/tinker) | ![tag](https://img.shields.io/badge/tag-private-red) | Conector de aplicaciones Windows de JumpServer (gratuito para la edición comunitaria) |
| [Panda](https://github.com/jumpserver/Panda) | ![tag](https://img.shields.io/badge/tag-private-red) | Conector de aplicaciones Linux de la edición empresarial de JumpServer |
| [Razor](https://github.com/jumpserver/razor) | ![tag](https://img.shields.io/badge/tag-private-red) | Proxy del protocolo RDP de la edición empresarial de JumpServer |
| [Magnus](https://github.com/jumpserver/magnus) | ![tag](https://img.shields.io/badge/tag-private-red) | Proxy de protocolos de bases de datos de la edición empresarial de JumpServer |
| [Nec](https://github.com/jumpserver/nec) | ![tag](https://img.shields.io/badge/tag-private-red) | Proxy del protocolo VNC de la edición empresarial de JumpServer |

### Servicios de apoyo

| Proyecto | Versión | Descripción |
| --- | --- | --- |
| [Video Worker](https://github.com/jumpserver/video-worker) | ![tag](https://img.shields.io/badge/tag-private-red) | Servicio de transcodificación de grabaciones de sesiones de la edición empresarial de JumpServer |
| [JDMC](https://github.com/jumpserver/jdmc) | ![tag](https://img.shields.io/badge/tag-private-red) | Servicio de operaciones y gestión de hosts de la edición empresarial de JumpServer |

### Despliegue y herramientas

| Proyecto | Versión | Descripción |
| --- | --- | --- |
| [Installer](https://github.com/jumpserver/installer) | [![tag](https://img.shields.io/github/v/tag/jumpserver/installer?sort=semver&filter=v5.*&label=tag)](https://github.com/jumpserver/installer/tags) | Herramienta de instalación y gestión de JumpServer |
| [Docker Web](https://github.com/jumpserver/docker-web) | [![tag](https://img.shields.io/github/v/tag/jumpserver/docker-web?sort=semver&filter=v5.*&label=tag)](https://github.com/jumpserver/docker-web/tags) | Puerta de enlace web y recursos estáticos de JumpServer |

## Contribuyendo

Bienvenido a enviar PR para contribuir. Por favor, consulte [CONTRIBUTING.md][contributing-link] para obtener pautas.

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