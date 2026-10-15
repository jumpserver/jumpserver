<div align="center">
  <a name="readme-top"></a>
  <a href="https://jumpserver.com" target="_blank"><img src="https://download.jumpserver.org/images/jumpserver-logo.svg" alt="JumpServer" width="300" /></a>
  
## Plataforma PAM de código aberto (bastião)

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

## O que é o JumpServer?

O JumpServer é uma plataforma de gerenciamento de acesso privilegiado (PAM) de código aberto com recursos de IA. Ele oferece às equipes de DevOps e TI um espaço de trabalho unificado para acessar com segurança SSH, RDP, Kubernetes, bancos de dados, sites, RemoteApp, VirtualApp e outros recursos.

<img alt="Diagrama da arquitetura do JumpServer" src="assets/jumpserver-architecture.png" />

## Início rápido

Prepare um servidor Linux de 64 bits limpo, com pelo menos 4 núcleos de CPU e 8 GB de RAM.

```sh
curl -sSL https://github.com/jumpserver/jumpserver/releases/latest/download/quick_start.sh | bash
```

Abra o JumpServer no navegador em `http://your-jumpserver-ip/`

- Usuário: `admin`
- Senha: `ChangeMe`

## Capturas de tela

<p align="center">
  <img src="assets/screenshot-01.png" alt="Painel de PAM do JumpServer" width="49%" />
  <img src="assets/screenshot-02.png" alt="Gerenciamento de ativos do JumpServer" width="49%" />
</p>

<p align="center">
  <img src="assets/screenshot-03.png" alt="Janela de conexão SSH do JumpServer" width="49%" />
  <img src="assets/screenshot-04.png" alt="Pergunta à IA no terminal do JumpServer" width="49%" />
</p>

<p align="center">
  <img src="assets/screenshot-05.png" alt="Assistente de IA do JumpServer" width="49%" />
  <img src="assets/screenshot-06.png" alt="Sessão de área de trabalho remota do JumpServer" width="49%" />
</p>

<p align="center">
  <img src="assets/screenshot-07.png" alt="Painel de ativos do terminal do JumpServer no tema claro" width="49%" />
  <img src="assets/screenshot-08.png" alt="Sessão SSH do JumpServer no tema claro" width="49%" />
</p>

<p align="center">
  <img src="assets/screenshot-09.png" alt="Painel de ativos do terminal do JumpServer no tema escuro" width="49%" />
  <img src="assets/screenshot-10.png" alt="Sessão SSH do JumpServer no tema escuro" width="49%" />
</p>

## Componentes

Os componentes do JumpServer são organizados por função. Os projetos principais oferecem a plataforma, a interface web, o terminal, as conexões de protocolo e os recursos de IA. Os componentes corporativos ampliam o acesso a aplicativos e protocolos. Os serviços de apoio cuidam das gravações de sessões e das operações em hosts, enquanto as ferramentas de implantação facilitam a instalação e a entrega de conteúdo web.

### Projetos principais

<table width="100%">
  <thead>
    <tr>
      <th width="160" align="left">Projeto</th>
      <th width="135" align="center"><div align="center">Versão</div></th>
      <th width="550" align="center"><div align="center">Descrição</div></th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td width="160" align="left" nowrap><a href="https://github.com/jumpserver/jumpserver">JumpServer</a></td>
      <td width="135" align="center"><div align="center"><a href="https://github.com/jumpserver/jumpserver/tags"><img src="https://img.shields.io/github/v/tag/jumpserver/jumpserver?sort=semver&amp;filter=v5.*&amp;label=tag" alt="JumpServer versão" /></a></div></td>
      <td width="550" align="left">Plataforma de gerenciamento de acesso privilegiado de código aberto</td>
    </tr>
    <tr>
      <td width="160" align="left" nowrap><a href="https://github.com/jumpserver/lina">Lina</a></td>
      <td width="135" align="center"><div align="center"><a href="https://github.com/jumpserver/lina/tags"><img src="https://img.shields.io/github/v/tag/jumpserver/lina?sort=semver&amp;filter=v5.*&amp;label=tag" alt="Lina versão" /></a></div></td>
      <td width="550" align="left">Interface web do JumpServer</td>
    </tr>
    <tr>
      <td width="160" align="left" nowrap><a href="https://github.com/jumpserver/luna">Luna</a></td>
      <td width="135" align="center"><div align="center"><a href="https://github.com/jumpserver/luna/tags"><img src="https://img.shields.io/github/v/tag/jumpserver/luna?sort=semver&amp;filter=v5.*&amp;label=tag" alt="Luna versão" /></a></div></td>
      <td width="550" align="left">Terminal web e cliente nativo do JumpServer</td>
    </tr>
    <tr>
      <td width="160" align="left" nowrap><a href="https://github.com/jumpserver/koko">KoKo</a></td>
      <td width="135" align="center"><div align="center"><a href="https://github.com/jumpserver/koko/tags"><img src="https://img.shields.io/github/v/tag/jumpserver/koko?sort=semver&amp;filter=v5.*&amp;label=tag" alt="KoKo versão" /></a></div></td>
      <td width="550" align="left">Conector e proxy de protocolos de uso geral do JumpServer</td>
    </tr>
    <tr>
      <td width="160" align="left" nowrap><a href="https://github.com/jumpserver/chen">Chen</a></td>
      <td width="135" align="center"><div align="center"><a href="https://github.com/jumpserver/chen/tags"><img src="https://img.shields.io/github/v/tag/jumpserver/chen?sort=semver&amp;filter=v5.*&amp;label=tag" alt="Chen versão" /></a></div></td>
      <td width="550" align="left">Conector de bancos de dados web do JumpServer</td>
    </tr>
    <tr>
      <td width="160" align="left" nowrap><a href="https://github.com/jumpserver/kael">Kael</a></td>
      <td width="135" align="center"><div align="center"><a href="https://github.com/jumpserver/kael/tags"><img src="https://img.shields.io/github/v/tag/jumpserver/kael?sort=semver&amp;filter=v5.*&amp;label=tag" alt="Kael versão" /></a></div></td>
      <td width="550" align="left">Componente de IA do JumpServer</td>
    </tr>
  </tbody>
</table>

### Componentes corporativos

<table width="100%">
  <thead>
    <tr>
      <th width="160" align="left">Projeto</th>
      <th width="135" align="center"><div align="center">Versão</div></th>
      <th width="550" align="center"><div align="center">Descrição</div></th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td width="160" align="left" nowrap><a href="https://github.com/jumpserver/tinker">Tinker</a></td>
      <td width="135" align="center"><div align="center"><img src="https://img.shields.io/badge/tag-private-red" alt="Versão privada" /></div></td>
      <td width="550" align="left">Conector de aplicativos Windows do JumpServer (gratuito na edição Community)</td>
    </tr>
    <tr>
      <td width="160" align="left" nowrap><a href="https://github.com/jumpserver/Panda">Panda</a></td>
      <td width="135" align="center"><div align="center"><img src="https://img.shields.io/badge/tag-private-red" alt="Versão privada" /></div></td>
      <td width="550" align="left">Conector de aplicativos Linux do JumpServer Enterprise Edition</td>
    </tr>
    <tr>
      <td width="160" align="left" nowrap><a href="https://github.com/jumpserver/razor">Razor</a></td>
      <td width="135" align="center"><div align="center"><img src="https://img.shields.io/badge/tag-private-red" alt="Versão privada" /></div></td>
      <td width="550" align="left">Proxy do protocolo RDP do JumpServer Enterprise Edition</td>
    </tr>
    <tr>
      <td width="160" align="left" nowrap><a href="https://github.com/jumpserver/magnus">Magnus</a></td>
      <td width="135" align="center"><div align="center"><img src="https://img.shields.io/badge/tag-private-red" alt="Versão privada" /></div></td>
      <td width="550" align="left">Proxy de protocolos de banco de dados do JumpServer Enterprise Edition</td>
    </tr>
    <tr>
      <td width="160" align="left" nowrap><a href="https://github.com/jumpserver/nec">Nec</a></td>
      <td width="135" align="center"><div align="center"><img src="https://img.shields.io/badge/tag-private-red" alt="Versão privada" /></div></td>
      <td width="550" align="left">Proxy do protocolo VNC do JumpServer Enterprise Edition</td>
    </tr>
  </tbody>
</table>

### Serviços de apoio

<table width="100%">
  <thead>
    <tr>
      <th width="160" align="left">Projeto</th>
      <th width="135" align="center"><div align="center">Versão</div></th>
      <th width="550" align="center"><div align="center">Descrição</div></th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td width="160" align="left" nowrap><a href="https://github.com/jumpserver/video-worker">Video&nbsp;Worker</a></td>
      <td width="135" align="center"><div align="center"><img src="https://img.shields.io/badge/tag-private-red" alt="Versão privada" /></div></td>
      <td width="550" align="left">Serviço de transcodificação de gravações de sessões do JumpServer Enterprise Edition</td>
    </tr>
    <tr>
      <td width="160" align="left" nowrap><a href="https://github.com/jumpserver/jdmc">JDMC</a></td>
      <td width="135" align="center"><div align="center"><img src="https://img.shields.io/badge/tag-private-red" alt="Versão privada" /></div></td>
      <td width="550" align="left">Serviço de operações e gerenciamento de hosts do JumpServer Enterprise Edition</td>
    </tr>
  </tbody>
</table>

### Implantação e ferramentas

<table width="100%">
  <thead>
    <tr>
      <th width="160" align="left">Projeto</th>
      <th width="135" align="center"><div align="center">Versão</div></th>
      <th width="550" align="center"><div align="center">Descrição</div></th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td width="160" align="left" nowrap><a href="https://github.com/jumpserver/installer">Installer</a></td>
      <td width="135" align="center"><div align="center"><a href="https://github.com/jumpserver/installer/tags"><img src="https://img.shields.io/github/v/tag/jumpserver/installer?sort=semver&amp;filter=v5.*&amp;label=tag" alt="Installer versão" /></a></div></td>
      <td width="550" align="left">Ferramenta de instalação e gerenciamento do JumpServer</td>
    </tr>
    <tr>
      <td width="160" align="left" nowrap><a href="https://github.com/jumpserver/docker-web">Docker&nbsp;Web</a></td>
      <td width="135" align="center"><div align="center"><a href="https://github.com/jumpserver/docker-web/tags"><img src="https://img.shields.io/github/v/tag/jumpserver/docker-web?sort=semver&amp;filter=v5.*&amp;label=tag" alt="Docker Web versão" /></a></div></td>
      <td width="550" align="left">Gateway web e recursos estáticos do JumpServer</td>
    </tr>
  </tbody>
</table>

## Contribuir

Contribuições são bem-vindas. Consulte [CONTRIBUTING.md][contributing-link] para conhecer as diretrizes.

## Licença

Copyright (c) 2014-2026 FIT2CLOUD. Todos os direitos reservados.

Este projeto é licenciado sob a Licença Pública Geral GNU versão 3 (GPLv3, a «Licença»). Você só pode usar este arquivo em conformidade com a Licença. Uma cópia está disponível em

https://www.gnu.org/licenses/gpl-3.0.html

A menos que exigido pela legislação aplicável ou acordado por escrito, o software distribuído sob a Licença é fornecido «NO ESTADO EM QUE SE ENCONTRA», SEM GARANTIAS OU CONDIÇÕES DE QUALQUER TIPO, expressas ou implícitas. Consulte a Licença para conhecer as permissões e limitações específicas.

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
