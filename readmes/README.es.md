<div align="center">
  <a name="readme-top"></a>
  <a href="https://jumpserver.com" target="_blank"><img src="https://download.jumpserver.org/images/jumpserver-logo.svg" alt="JumpServer" width="300" /></a>
  
## Plataforma PAM de código abierto (bastión)

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

## ¿Qué es JumpServer?

JumpServer es una plataforma de gestión de accesos privilegiados (PAM) de código abierto con funciones de IA. Ofrece a los equipos de DevOps y TI un espacio de trabajo unificado para acceder de forma segura a SSH, RDP, Kubernetes, bases de datos, sitios web, RemoteApp, VirtualApp y otros recursos.

<img alt="Diagrama de arquitectura de JumpServer" src="https://github.com/user-attachments/assets/2bbf0979-4e1e-43ea-8dac-5d3e3bfbf1d1" />

## Inicio rápido

Prepare un servidor Linux de 64 bits limpio, con al menos 4 núcleos de CPU y 8 GB de RAM.

```sh
curl -sSL https://github.com/jumpserver/jumpserver/releases/latest/download/quick_start.sh | bash
```

Abra JumpServer en el navegador en `http://your-jumpserver-ip/`

- Usuario: `admin`
- Contraseña: `ChangeMe`

## Capturas de pantalla

<table width="100%" align="center">
  <tr>
    <td width="50%" align="center"><img src="https://github.com/user-attachments/assets/6164c92a-0b19-405a-b79c-73e28a9a1610" alt="JumpServer Consola" width="100%" /></td>
    <td width="50%" align="center"><img src="https://github.com/user-attachments/assets/12d1206d-b511-4f29-8b00-fd13333f3a21" alt="JumpServer Gestión de accesos privilegiados" width="100%" /></td>
  </tr>
  <tr>
    <td width="50%" align="center"><img src="https://github.com/user-attachments/assets/6d12d3c9-5f31-4294-b6e7-7c5b5836f688" alt="JumpServer Auditorías" width="100%" /></td>
    <td width="50%" align="center"><img src="https://github.com/user-attachments/assets/ba784bc8-e889-4fd6-aaae-0b8b14153da2" alt="JumpServer Espacio de trabajo" width="100%" /></td>
  </tr>
  <tr>
    <td width="50%" align="center"><img src="https://github.com/user-attachments/assets/d4b10b15-bccb-4a0d-a6e6-74a6439614e0" alt="JumpServer Roles y permisos" width="100%" /></td>
    <td width="50%" align="center"><img src="https://github.com/user-attachments/assets/ccbeb96e-9747-4182-bd03-031fb3af8bb2" alt="JumpServer Configuración" width="100%" /></td>
  </tr>
  <tr>
    <td width="50%" align="center"><img src="https://github.com/user-attachments/assets/9049888e-16fe-4fbe-b0f2-16bf140379c8" alt="JumpServer SSH" width="100%" /></td>
    <td width="50%" align="center"><img src="https://github.com/user-attachments/assets/133c4af6-90a9-457d-b372-bb53c29260dc" alt="JumpServer RDP" width="100%" /></td>
  </tr>
  <tr>
    <td width="50%" align="center"><img src="https://github.com/user-attachments/assets/ea48738f-b5f8-4a43-a487-ca09b11176e7" alt="JumpServer Kubernetes" width="100%" /></td>
    <td width="50%" align="center"><img src="https://github.com/user-attachments/assets/3407539f-1235-4dcc-adf2-26d7b60dbc67" alt="JumpServer Bases de datos" width="100%" /></td>
  </tr>
</table>

## Componentes

Los componentes de JumpServer se organizan según su función. Los proyectos principales proporcionan la plataforma, la interfaz web, la terminal, las conexiones de protocolo y las funciones de IA. Los componentes empresariales amplían el acceso a aplicaciones y protocolos. Los servicios auxiliares gestionan las grabaciones de sesiones y las operaciones de los hosts, mientras que las herramientas de despliegue facilitan la instalación y la entrega web.

### Proyectos principales

<table width="100%" align="center">
  <thead>
    <tr>
      <th width="160" align="left">Proyecto</th>
      <th width="135" align="center"><div align="center">Versión</div></th>
      <th align="center"><div align="center">Descripción</div></th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td width="160" align="left" nowrap><a href="https://github.com/jumpserver/jumpserver">JumpServer</a></td>
      <td width="135" align="center"><div align="center"><a href="https://github.com/jumpserver/jumpserver/tags"><img src="https://img.shields.io/github/v/tag/jumpserver/jumpserver?sort=semver&amp;filter=v5.*&amp;label=tag" alt="JumpServer versión" /></a></div></td>
      <td align="left">Plataforma de gestión de accesos privilegiados de código abierto</td>
    </tr>
    <tr>
      <td width="160" align="left" nowrap><a href="https://github.com/jumpserver/lina">Lina</a></td>
      <td width="135" align="center"><div align="center"><a href="https://github.com/jumpserver/lina/tags"><img src="https://img.shields.io/github/v/tag/jumpserver/lina?sort=semver&amp;filter=v5.*&amp;label=tag" alt="Lina versión" /></a></div></td>
      <td align="left">Interfaz web de JumpServer</td>
    </tr>
    <tr>
      <td width="160" align="left" nowrap><a href="https://github.com/jumpserver/luna">Luna</a></td>
      <td width="135" align="center"><div align="center"><a href="https://github.com/jumpserver/luna/tags"><img src="https://img.shields.io/github/v/tag/jumpserver/luna?sort=semver&amp;filter=v5.*&amp;label=tag" alt="Luna versión" /></a></div></td>
      <td align="left">Terminal web y cliente nativo de JumpServer</td>
    </tr>
    <tr>
      <td width="160" align="left" nowrap><a href="https://github.com/jumpserver/koko">KoKo</a></td>
      <td width="135" align="center"><div align="center"><a href="https://github.com/jumpserver/koko/tags"><img src="https://img.shields.io/github/v/tag/jumpserver/koko?sort=semver&amp;filter=v5.*&amp;label=tag" alt="KoKo versión" /></a></div></td>
      <td align="left">Conector y proxy de protocolos de uso general de JumpServer</td>
    </tr>
    <tr>
      <td width="160" align="left" nowrap><a href="https://github.com/jumpserver/chen">Chen</a></td>
      <td width="135" align="center"><div align="center"><a href="https://github.com/jumpserver/chen/tags"><img src="https://img.shields.io/github/v/tag/jumpserver/chen?sort=semver&amp;filter=v5.*&amp;label=tag" alt="Chen versión" /></a></div></td>
      <td align="left">Conector de bases de datos web de JumpServer</td>
    </tr>
    <tr>
      <td width="160" align="left" nowrap><a href="https://github.com/jumpserver/kael">Kael</a></td>
      <td width="135" align="center"><div align="center"><a href="https://github.com/jumpserver/kael/tags"><img src="https://img.shields.io/github/v/tag/jumpserver/kael?sort=semver&amp;filter=v5.*&amp;label=tag" alt="Kael versión" /></a></div></td>
      <td align="left">Componente de IA de JumpServer</td>
    </tr>
  </tbody>
</table>

### Componentes empresariales

<table width="100%" align="center">
  <thead>
    <tr>
      <th width="160" align="left">Proyecto</th>
      <th width="135" align="center"><div align="center">Versión</div></th>
      <th align="center"><div align="center">Descripción</div></th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td width="160" align="left" nowrap><a href="https://github.com/jumpserver/tinker">Tinker</a></td>
      <td width="135" align="center"><div align="center"><img src="https://img.shields.io/badge/tag-private-red" alt="Versión privada" /></div></td>
      <td align="left">Conector de aplicaciones Windows de JumpServer (gratuito en la edición Community)</td>
    </tr>
    <tr>
      <td width="160" align="left" nowrap><a href="https://github.com/jumpserver/Panda">Panda</a></td>
      <td width="135" align="center"><div align="center"><img src="https://img.shields.io/badge/tag-private-red" alt="Versión privada" /></div></td>
      <td align="left">Conector de aplicaciones Linux de JumpServer Enterprise Edition</td>
    </tr>
    <tr>
      <td width="160" align="left" nowrap><a href="https://github.com/jumpserver/razor">Razor</a></td>
      <td width="135" align="center"><div align="center"><img src="https://img.shields.io/badge/tag-private-red" alt="Versión privada" /></div></td>
      <td align="left">Proxy del protocolo RDP de JumpServer Enterprise Edition</td>
    </tr>
    <tr>
      <td width="160" align="left" nowrap><a href="https://github.com/jumpserver/magnus">Magnus</a></td>
      <td width="135" align="center"><div align="center"><img src="https://img.shields.io/badge/tag-private-red" alt="Versión privada" /></div></td>
      <td align="left">Proxy de protocolos de bases de datos de JumpServer Enterprise Edition</td>
    </tr>
    <tr>
      <td width="160" align="left" nowrap><a href="https://github.com/jumpserver/nec">Nec</a></td>
      <td width="135" align="center"><div align="center"><img src="https://img.shields.io/badge/tag-private-red" alt="Versión privada" /></div></td>
      <td align="left">Proxy del protocolo VNC de JumpServer Enterprise Edition</td>
    </tr>
  </tbody>
</table>

### Servicios auxiliares

<table width="100%" align="center">
  <thead>
    <tr>
      <th width="160" align="left">Proyecto</th>
      <th width="135" align="center"><div align="center">Versión</div></th>
      <th align="center"><div align="center">Descripción</div></th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td width="160" align="left" nowrap><a href="https://github.com/jumpserver/video-worker">Video&nbsp;Worker</a></td>
      <td width="135" align="center"><div align="center"><img src="https://img.shields.io/badge/tag-private-red" alt="Versión privada" /></div></td>
      <td align="left">Servicio de transcodificación de grabaciones de sesiones de JumpServer Enterprise Edition</td>
    </tr>
    <tr>
      <td width="160" align="left" nowrap><a href="https://github.com/jumpserver/jdmc">JDMC</a></td>
      <td width="135" align="center"><div align="center"><img src="https://img.shields.io/badge/tag-private-red" alt="Versión privada" /></div></td>
      <td align="left">Servicio de operaciones y administración de hosts de JumpServer Enterprise Edition</td>
    </tr>
  </tbody>
</table>

### Despliegue y herramientas

<table width="100%" align="center">
  <thead>
    <tr>
      <th width="160" align="left">Proyecto</th>
      <th width="135" align="center"><div align="center">Versión</div></th>
      <th align="center"><div align="center">Descripción</div></th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td width="160" align="left" nowrap><a href="https://github.com/jumpserver/installer">Installer</a></td>
      <td width="135" align="center"><div align="center"><a href="https://github.com/jumpserver/installer/tags"><img src="https://img.shields.io/github/v/tag/jumpserver/installer?sort=semver&amp;filter=v5.*&amp;label=tag" alt="Installer versión" /></a></div></td>
      <td align="left">Herramienta de instalación y administración de JumpServer</td>
    </tr>
    <tr>
      <td width="160" align="left" nowrap><a href="https://github.com/jumpserver/docker-web">Docker&nbsp;Web</a></td>
      <td width="135" align="center"><div align="center"><a href="https://github.com/jumpserver/docker-web/tags"><img src="https://img.shields.io/github/v/tag/jumpserver/docker-web?sort=semver&amp;filter=v5.*&amp;label=tag" alt="Docker Web versión" /></a></div></td>
      <td align="left">Puerta de enlace web y recursos estáticos de JumpServer</td>
    </tr>
  </tbody>
</table>

## Contribuir

Se agradecen las contribuciones. Consulte [CONTRIBUTING.md][contributing-link] para conocer las directrices.

## Licencia

Copyright (c) 2014-2026 FIT2CLOUD. Todos los derechos reservados.

Este proyecto se distribuye bajo la Licencia Pública General de GNU, versión 3 (GPLv3, la «Licencia»). Solo puede utilizar este archivo de conformidad con la Licencia. Puede obtener una copia en

https://www.gnu.org/licenses/gpl-3.0.html

Salvo que lo exija la ley aplicable o se acuerde por escrito, el software distribuido bajo la Licencia se proporciona «TAL CUAL», SIN GARANTÍAS NI CONDICIONES DE NINGÚN TIPO, expresas o implícitas. Consulte la Licencia para conocer los permisos y las limitaciones específicos.

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
