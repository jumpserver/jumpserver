<div align="center">
  <a name="readme-top"></a>
  <a href="https://jumpserver.com" target="_blank"><img src="assets/jumpserver-logo.svg" alt="JumpServer" width="300" /></a>

## Une plateforme PAM open source (bastion)

[![][license-shield]][license-link]
[![][docs-shield]][docs-link]
[![][deepwiki-shield]][deepwiki-link]
[![][discord-shield]][discord-link]
[![][docker-shield]][docker-link]
[![][github-release-shield]][github-release-link]
[![][github-stars-shield]][github-stars-link]

[English](/README.md) · [中文(简体)](/readmes/README.zh-hans.md) · [中文(繁體)](/readmes/README.zh-hant.md) · [日本語](/readmes/README.ja.md) · [Português (Brasil)](/readmes/README.pt-br.md) · [Español](/readmes/README.es.md) · [Français](/readmes/README.fr.md) · [Русский](/readmes/README.ru.md) · [한국어](/readmes/README.ko.md) · [Tiếng Việt](/readmes/README.vi.md)

</div>

<br/>

## Qu’est-ce que JumpServer ?

JumpServer est une plateforme open source de gestion des accès à privilèges (PAM) dotée de fonctionnalités d’intelligence artificielle. Elle offre aux équipes DevOps et informatiques un espace de travail unifié pour accéder en toute sécurité à SSH, RDP, Kubernetes, des bases de données, des sites web, RemoteApp, VirtualApp et bien plus encore.

<img alt="Schéma d’architecture de JumpServer" src="assets/jumpserver-architecture.gif" />

## Démarrage rapide

Préparez un serveur Linux 64 bits vierge disposant d’au moins 4 cœurs de processeur et 8 Go de RAM.

```sh
curl -sSL https://github.com/jumpserver/jumpserver/releases/latest/download/quick_start.sh | bash
```

Ouvrez `https://<jumpserver-host>/` dans votre navigateur et remplacez `<jumpserver-host>` par l’adresse IP ou le nom de domaine de l’hôte exécutant JumpServer.

- Nom d’utilisateur : `admin`
- Mot de passe : `ChangeMe`

## Captures d’écran

<p align="center">
  <img src="assets/screenshot-01.png" alt="Tableau de bord PAM de JumpServer" title="Tableau de bord PAM de JumpServer" width="49%" />
  <img src="assets/screenshot-02.png" alt="Gestion des actifs dans JumpServer" title="Gestion des actifs dans JumpServer" width="49%" />
</p>

<p align="center">
  <img src="assets/screenshot-03.png" alt="Boîte de dialogue de connexion SSH de JumpServer" title="Boîte de dialogue de connexion SSH de JumpServer" width="49%" />
  <img src="assets/screenshot-04.png" alt="Invite IA dans le terminal JumpServer" title="Invite IA dans le terminal JumpServer" width="49%" />
</p>

<p align="center">
  <img src="assets/screenshot-05.png" alt="Assistant IA de JumpServer" title="Assistant IA de JumpServer" width="49%" />
  <img src="assets/screenshot-06.png" alt="Session de bureau à distance JumpServer" title="Session de bureau à distance JumpServer" width="49%" />
</p>

<p align="center">
  <img src="assets/screenshot-07.png" alt="KoKo TUI asset browser with searchable authorized assets" title="KoKo TUI asset browser with searchable authorized assets" width="49%" />
  <img src="assets/screenshot-08.png" alt="KoKo TUI multi-session manager for switching between active SSH sessions" title="KoKo TUI multi-session manager for switching between active SSH sessions" width="49%" />
</p>

<p align="center">
  <img src="assets/screenshot-09.png" alt="KoKo classic text-mode home screen with connection shortcuts" title="KoKo classic text-mode home screen with connection shortcuts" width="49%" />
  <img src="assets/screenshot-10.png" alt="KoKo classic text-mode asset list with authorized SSH targets" title="KoKo classic text-mode asset list with authorized SSH targets" width="49%" />
</p>

## Composants

JumpServer regroupe ses composants selon leur rôle. Les projets principaux fournissent la plateforme, l’interface web, le terminal, les connexions aux protocoles et les fonctionnalités d’IA. Les composants Enterprise étendent l’accès aux applications et aux protocoles. Les services complémentaires gèrent les enregistrements de session et l’exploitation des hôtes, tandis que les outils de déploiement simplifient l’installation et la mise à disposition sur le web.

### Projets principaux

<table width="100%">
  <thead>
    <tr>
      <th width="160" align="left">Projet</th>
      <th width="135" align="center"><div align="center">Version</div></th>
      <th width="550" align="center"><div align="center">Description</div></th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td width="160" align="left" nowrap><a href="https://github.com/jumpserver/jumpserver">JumpServer</a></td>
      <td width="135" align="center"><div align="center"><a href="https://github.com/jumpserver/jumpserver/tags"><img src="https://img.shields.io/github/v/tag/jumpserver/jumpserver?sort=semver&amp;filter=v5.*&amp;label=tag" alt="Version de JumpServer" /></a></div></td>
      <td width="550" align="left">Plateforme open source de gestion des accès à privilèges</td>
    </tr>
    <tr>
      <td width="160" align="left" nowrap><a href="https://github.com/jumpserver/lina">Lina</a></td>
      <td width="135" align="center"><div align="center"><a href="https://github.com/jumpserver/lina/tags"><img src="https://img.shields.io/github/v/tag/jumpserver/lina?sort=semver&amp;filter=v5.*&amp;label=tag" alt="Version de Lina" /></a></div></td>
      <td width="550" align="left">Interface web de JumpServer</td>
    </tr>
    <tr>
      <td width="160" align="left" nowrap><a href="https://github.com/jumpserver/luna">Luna</a></td>
      <td width="135" align="center"><div align="center"><a href="https://github.com/jumpserver/luna/tags"><img src="https://img.shields.io/github/v/tag/jumpserver/luna?sort=semver&amp;filter=v5.*&amp;label=tag" alt="Version de Luna" /></a></div></td>
      <td width="550" align="left">Terminal web et client natif de JumpServer</td>
    </tr>
    <tr>
      <td width="160" align="left" nowrap><a href="https://github.com/jumpserver/koko">KoKo</a></td>
      <td width="135" align="center"><div align="center"><a href="https://github.com/jumpserver/koko/tags"><img src="https://img.shields.io/github/v/tag/jumpserver/koko?sort=semver&amp;filter=v5.*&amp;label=tag" alt="Version de KoKo" /></a></div></td>
      <td width="550" align="left">Connecteur et proxy polyvalents pour les protocoles de JumpServer</td>
    </tr>
    <tr>
      <td width="160" align="left" nowrap><a href="https://github.com/jumpserver/chen">Chen</a></td>
      <td width="135" align="center"><div align="center"><a href="https://github.com/jumpserver/chen/tags"><img src="https://img.shields.io/github/v/tag/jumpserver/chen?sort=semver&amp;filter=v5.*&amp;label=tag" alt="Version de Chen" /></a></div></td>
      <td width="550" align="left">Connecteur web aux bases de données de JumpServer</td>
    </tr>
    <tr>
      <td width="160" align="left" nowrap><a href="https://github.com/jumpserver/kael">Kael</a></td>
      <td width="135" align="center"><div align="center"><a href="https://github.com/jumpserver/kael/tags"><img src="https://img.shields.io/github/v/tag/jumpserver/kael?sort=semver&amp;filter=v5.*&amp;label=tag" alt="Version de Kael" /></a></div></td>
      <td width="550" align="left">Composant IA de JumpServer</td>
    </tr>
  </tbody>
</table>

### Composants Enterprise

<table width="100%">
  <thead>
    <tr>
      <th width="160" align="left">Projet</th>
      <th width="135" align="center"><div align="center">Version</div></th>
      <th width="550" align="center"><div align="center">Description</div></th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td width="160" align="left" nowrap><a href="https://github.com/jumpserver/tinker">Tinker</a></td>
      <td width="135" align="center"><div align="center"><img src="https://img.shields.io/badge/tag-private-red" alt="Version privée" /></div></td>
      <td width="550" align="left">Connecteur d’applications Windows de JumpServer (gratuit pour l’édition Community)</td>
    </tr>
    <tr>
      <td width="160" align="left" nowrap><a href="https://github.com/jumpserver/Panda">Panda</a></td>
      <td width="135" align="center"><div align="center"><img src="https://img.shields.io/badge/tag-private-red" alt="Version privée" /></div></td>
      <td width="550" align="left">Connecteur d’applications Linux de JumpServer Enterprise Edition</td>
    </tr>
    <tr>
      <td width="160" align="left" nowrap><a href="https://github.com/jumpserver/razor">Razor</a></td>
      <td width="135" align="center"><div align="center"><img src="https://img.shields.io/badge/tag-private-red" alt="Version privée" /></div></td>
      <td width="550" align="left">Proxy du protocole RDP de JumpServer Enterprise Edition</td>
    </tr>
    <tr>
      <td width="160" align="left" nowrap><a href="https://github.com/jumpserver/magnus">Magnus</a></td>
      <td width="135" align="center"><div align="center"><img src="https://img.shields.io/badge/tag-private-red" alt="Version privée" /></div></td>
      <td width="550" align="left">Proxy des protocoles de bases de données de JumpServer Enterprise Edition</td>
    </tr>
    <tr>
      <td width="160" align="left" nowrap><a href="https://github.com/jumpserver/nec">Nec</a></td>
      <td width="135" align="center"><div align="center"><img src="https://img.shields.io/badge/tag-private-red" alt="Version privée" /></div></td>
      <td width="550" align="left">Proxy du protocole VNC de JumpServer Enterprise Edition</td>
    </tr>
  </tbody>
</table>

### Services complémentaires

<table width="100%">
  <thead>
    <tr>
      <th width="160" align="left">Projet</th>
      <th width="135" align="center"><div align="center">Version</div></th>
      <th width="550" align="center"><div align="center">Description</div></th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td width="160" align="left" nowrap><a href="https://github.com/jumpserver/video-worker">Video&nbsp;Worker</a></td>
      <td width="135" align="center"><div align="center"><img src="https://img.shields.io/badge/tag-private-red" alt="Version privée" /></div></td>
      <td width="550" align="left">Service de transcodage des enregistrements de session de JumpServer Enterprise Edition</td>
    </tr>
    <tr>
      <td width="160" align="left" nowrap><a href="https://github.com/jumpserver/jdmc">JDMC</a></td>
      <td width="135" align="center"><div align="center"><img src="https://img.shields.io/badge/tag-private-red" alt="Version privée" /></div></td>
      <td width="550" align="left">Service d’exploitation et de gestion des hôtes de JumpServer Enterprise Edition</td>
    </tr>
  </tbody>
</table>

### Déploiement et outils

<table width="100%">
  <thead>
    <tr>
      <th width="160" align="left">Projet</th>
      <th width="135" align="center"><div align="center">Version</div></th>
      <th width="550" align="center"><div align="center">Description</div></th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td width="160" align="left" nowrap><a href="https://github.com/jumpserver/installer">Installer</a></td>
      <td width="135" align="center"><div align="center"><a href="https://github.com/jumpserver/installer/tags"><img src="https://img.shields.io/github/v/tag/jumpserver/installer?sort=semver&amp;filter=v5.*&amp;label=tag" alt="Version de l’outil d’installation" /></a></div></td>
      <td width="550" align="left">Outil d’installation et d’administration de JumpServer</td>
    </tr>
    <tr>
      <td width="160" align="left" nowrap><a href="https://github.com/jumpserver/docker-web">Docker&nbsp;Web</a></td>
      <td width="135" align="center"><div align="center"><a href="https://github.com/jumpserver/docker-web/tags"><img src="https://img.shields.io/github/v/tag/jumpserver/docker-web?sort=semver&amp;filter=v5.*&amp;label=tag" alt="Version de Docker Web" /></a></div></td>
      <td width="550" align="left">Passerelle web et ressources statiques de JumpServer</td>
    </tr>
  </tbody>
</table>

## Contribution

Les contributions sont les bienvenues. Consultez [CONTRIBUTING.md][contributing-link] pour connaître les directives.

## Licence

Copyright (c) 2014-2026 FIT2CLOUD. Tous droits réservés.

Ce projet est distribué sous la licence GNU General Public License version 3 (GPLv3, la « Licence »). Vous ne pouvez utiliser ce fichier que conformément à la Licence. Vous pouvez en obtenir une copie à l’adresse suivante :

https://www.gnu.org/licenses/gpl-3.0.html

Sauf disposition contraire de la législation applicable ou accord écrit, le logiciel distribué sous la Licence est fourni « EN L’ÉTAT », SANS GARANTIE NI CONDITION D’AUCUNE SORTE, expresse ou implicite. Consultez la Licence pour connaître les autorisations et limitations spécifiques.

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
