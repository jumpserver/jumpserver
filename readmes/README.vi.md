<div align="center">
  <a name="readme-top"></a>
  <a href="https://jumpserver.com" target="_blank"><img src="https://download.jumpserver.org/images/jumpserver-logo.svg" alt="JumpServer" width="300" /></a>
  
## Nền tảng PAM mã nguồn mở (máy chủ bastion)

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

## JumpServer là gì?

JumpServer là nền tảng quản lý truy cập đặc quyền (PAM) mã nguồn mở có tích hợp AI. Nền tảng cung cấp cho các nhóm DevOps và CNTT một không gian làm việc thống nhất để truy cập an toàn vào SSH, RDP, Kubernetes, cơ sở dữ liệu, trang web, RemoteApp, VirtualApp và nhiều tài nguyên khác.

<img alt="Sơ đồ kiến trúc JumpServer" src="https://github.com/user-attachments/assets/2bbf0979-4e1e-43ea-8dac-5d3e3bfbf1d1" />

## Bắt đầu nhanh

Chuẩn bị một máy chủ Linux 64 bit mới, có ít nhất 4 nhân CPU và 8 GB RAM.

```sh
curl -sSL https://github.com/jumpserver/jumpserver/releases/latest/download/quick_start.sh | bash
```

Mở JumpServer trong trình duyệt tại `http://your-jumpserver-ip/`

- Tên đăng nhập: `admin`
- Mật khẩu: `ChangeMe`

## Ảnh chụp màn hình

<table width="100%" align="center">
  <tr>
    <td width="50%" align="center"><img src="https://github.com/user-attachments/assets/6164c92a-0b19-405a-b79c-73e28a9a1610" alt="Bảng điều khiển JumpServer" width="100%" /></td>
    <td width="50%" align="center"><img src="https://github.com/user-attachments/assets/12d1206d-b511-4f29-8b00-fd13333f3a21" alt="Quản lý truy cập đặc quyền JumpServer" width="100%" /></td>
  </tr>
  <tr>
    <td width="50%" align="center"><img src="https://github.com/user-attachments/assets/6d12d3c9-5f31-4294-b6e7-7c5b5836f688" alt="Kiểm toán JumpServer" width="100%" /></td>
    <td width="50%" align="center"><img src="https://github.com/user-attachments/assets/ba784bc8-e889-4fd6-aaae-0b8b14153da2" alt="Không gian làm việc JumpServer" width="100%" /></td>
  </tr>
  <tr>
    <td width="50%" align="center"><img src="https://github.com/user-attachments/assets/d4b10b15-bccb-4a0d-a6e6-74a6439614e0" alt="Quản lý vai trò và quyền JumpServer" width="100%" /></td>
    <td width="50%" align="center"><img src="https://github.com/user-attachments/assets/ccbeb96e-9747-4182-bd03-031fb3af8bb2" alt="Cài đặt JumpServer" width="100%" /></td>
  </tr>
  <tr>
    <td width="50%" align="center"><img src="https://github.com/user-attachments/assets/9049888e-16fe-4fbe-b0f2-16bf140379c8" alt="JumpServer SSH" width="100%" /></td>
    <td width="50%" align="center"><img src="https://github.com/user-attachments/assets/133c4af6-90a9-457d-b372-bb53c29260dc" alt="JumpServer RDP" width="100%" /></td>
  </tr>
  <tr>
    <td width="50%" align="center"><img src="https://github.com/user-attachments/assets/ea48738f-b5f8-4a43-a487-ca09b11176e7" alt="JumpServer Kubernetes" width="100%" /></td>
    <td width="50%" align="center"><img src="https://github.com/user-attachments/assets/3407539f-1235-4dcc-adf2-26d7b60dbc67" alt="Cơ sở dữ liệu JumpServer" width="100%" /></td>
  </tr>
</table>

## Thành phần

Các thành phần của JumpServer được nhóm theo vai trò. Các dự án cốt lõi cung cấp nền tảng, giao diện web, terminal, kết nối giao thức và khả năng AI. Các thành phần dành cho doanh nghiệp mở rộng quyền truy cập vào ứng dụng và giao thức. Các dịch vụ hỗ trợ xử lý bản ghi phiên làm việc và vận hành máy chủ, còn các công cụ triển khai giúp đơn giản hóa việc cài đặt và phân phối nội dung web.

### Dự án cốt lõi

<table width="100%" align="center">
  <thead>
    <tr>
      <th width="160" align="left">Dự án</th>
      <th width="135" align="center"><div align="center">Phiên bản</div></th>
      <th align="center"><div align="center">Mô tả</div></th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td width="160" align="left" nowrap><a href="https://github.com/jumpserver/jumpserver">JumpServer</a></td>
      <td width="135" align="center"><div align="center"><a href="https://github.com/jumpserver/jumpserver/tags"><img src="https://img.shields.io/github/v/tag/jumpserver/jumpserver?sort=semver&amp;filter=v5.*&amp;label=tag" alt="Phiên bản JumpServer" /></a></div></td>
      <td align="left">Nền tảng quản lý truy cập đặc quyền mã nguồn mở</td>
    </tr>
    <tr>
      <td width="160" align="left" nowrap><a href="https://github.com/jumpserver/lina">Lina</a></td>
      <td width="135" align="center"><div align="center"><a href="https://github.com/jumpserver/lina/tags"><img src="https://img.shields.io/github/v/tag/jumpserver/lina?sort=semver&amp;filter=v5.*&amp;label=tag" alt="Phiên bản Lina" /></a></div></td>
      <td align="left">Giao diện web của JumpServer</td>
    </tr>
    <tr>
      <td width="160" align="left" nowrap><a href="https://github.com/jumpserver/luna">Luna</a></td>
      <td width="135" align="center"><div align="center"><a href="https://github.com/jumpserver/luna/tags"><img src="https://img.shields.io/github/v/tag/jumpserver/luna?sort=semver&amp;filter=v5.*&amp;label=tag" alt="Phiên bản Luna" /></a></div></td>
      <td align="left">Terminal web và ứng dụng khách gốc của JumpServer</td>
    </tr>
    <tr>
      <td width="160" align="left" nowrap><a href="https://github.com/jumpserver/koko">KoKo</a></td>
      <td width="135" align="center"><div align="center"><a href="https://github.com/jumpserver/koko/tags"><img src="https://img.shields.io/github/v/tag/jumpserver/koko?sort=semver&amp;filter=v5.*&amp;label=tag" alt="Phiên bản KoKo" /></a></div></td>
      <td align="left">Bộ kết nối và proxy giao thức đa dụng của JumpServer</td>
    </tr>
    <tr>
      <td width="160" align="left" nowrap><a href="https://github.com/jumpserver/chen">Chen</a></td>
      <td width="135" align="center"><div align="center"><a href="https://github.com/jumpserver/chen/tags"><img src="https://img.shields.io/github/v/tag/jumpserver/chen?sort=semver&amp;filter=v5.*&amp;label=tag" alt="Phiên bản Chen" /></a></div></td>
      <td align="left">Bộ kết nối cơ sở dữ liệu trên web của JumpServer</td>
    </tr>
    <tr>
      <td width="160" align="left" nowrap><a href="https://github.com/jumpserver/kael">Kael</a></td>
      <td width="135" align="center"><div align="center"><a href="https://github.com/jumpserver/kael/tags"><img src="https://img.shields.io/github/v/tag/jumpserver/kael?sort=semver&amp;filter=v5.*&amp;label=tag" alt="Phiên bản Kael" /></a></div></td>
      <td align="left">Thành phần AI của JumpServer</td>
    </tr>
  </tbody>
</table>

### Thành phần doanh nghiệp

<table width="100%" align="center">
  <thead>
    <tr>
      <th width="160" align="left">Dự án</th>
      <th width="135" align="center"><div align="center">Phiên bản</div></th>
      <th align="center"><div align="center">Mô tả</div></th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td width="160" align="left" nowrap><a href="https://github.com/jumpserver/tinker">Tinker</a></td>
      <td width="135" align="center"><div align="center"><img src="https://img.shields.io/badge/tag-private-red" alt="Phiên bản riêng tư" /></div></td>
      <td align="left">Bộ kết nối ứng dụng Windows của JumpServer (miễn phí cho phiên bản Cộng đồng)</td>
    </tr>
    <tr>
      <td width="160" align="left" nowrap><a href="https://github.com/jumpserver/Panda">Panda</a></td>
      <td width="135" align="center"><div align="center"><img src="https://img.shields.io/badge/tag-private-red" alt="Phiên bản riêng tư" /></div></td>
      <td align="left">Bộ kết nối ứng dụng Linux của JumpServer Enterprise Edition</td>
    </tr>
    <tr>
      <td width="160" align="left" nowrap><a href="https://github.com/jumpserver/razor">Razor</a></td>
      <td width="135" align="center"><div align="center"><img src="https://img.shields.io/badge/tag-private-red" alt="Phiên bản riêng tư" /></div></td>
      <td align="left">Proxy giao thức RDP của JumpServer Enterprise Edition</td>
    </tr>
    <tr>
      <td width="160" align="left" nowrap><a href="https://github.com/jumpserver/magnus">Magnus</a></td>
      <td width="135" align="center"><div align="center"><img src="https://img.shields.io/badge/tag-private-red" alt="Phiên bản riêng tư" /></div></td>
      <td align="left">Proxy giao thức cơ sở dữ liệu của JumpServer Enterprise Edition</td>
    </tr>
    <tr>
      <td width="160" align="left" nowrap><a href="https://github.com/jumpserver/nec">Nec</a></td>
      <td width="135" align="center"><div align="center"><img src="https://img.shields.io/badge/tag-private-red" alt="Phiên bản riêng tư" /></div></td>
      <td align="left">Proxy giao thức VNC của JumpServer Enterprise Edition</td>
    </tr>
  </tbody>
</table>

### Dịch vụ hỗ trợ

<table width="100%" align="center">
  <thead>
    <tr>
      <th width="160" align="left">Dự án</th>
      <th width="135" align="center"><div align="center">Phiên bản</div></th>
      <th align="center"><div align="center">Mô tả</div></th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td width="160" align="left" nowrap><a href="https://github.com/jumpserver/video-worker">Video&nbsp;Worker</a></td>
      <td width="135" align="center"><div align="center"><img src="https://img.shields.io/badge/tag-private-red" alt="Phiên bản riêng tư" /></div></td>
      <td align="left">Dịch vụ chuyển mã bản ghi phiên làm việc của JumpServer Enterprise Edition</td>
    </tr>
    <tr>
      <td width="160" align="left" nowrap><a href="https://github.com/jumpserver/jdmc">JDMC</a></td>
      <td width="135" align="center"><div align="center"><img src="https://img.shields.io/badge/tag-private-red" alt="Phiên bản riêng tư" /></div></td>
      <td align="left">Dịch vụ vận hành và quản lý máy chủ của JumpServer Enterprise Edition</td>
    </tr>
  </tbody>
</table>

### Triển khai và công cụ

<table width="100%" align="center">
  <thead>
    <tr>
      <th width="160" align="left">Dự án</th>
      <th width="135" align="center"><div align="center">Phiên bản</div></th>
      <th align="center"><div align="center">Mô tả</div></th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td width="160" align="left" nowrap><a href="https://github.com/jumpserver/installer">Installer</a></td>
      <td width="135" align="center"><div align="center"><a href="https://github.com/jumpserver/installer/tags"><img src="https://img.shields.io/github/v/tag/jumpserver/installer?sort=semver&amp;filter=v5.*&amp;label=tag" alt="Phiên bản Installer" /></a></div></td>
      <td align="left">Công cụ cài đặt và quản lý JumpServer</td>
    </tr>
    <tr>
      <td width="160" align="left" nowrap><a href="https://github.com/jumpserver/docker-web">Docker&nbsp;Web</a></td>
      <td width="135" align="center"><div align="center"><a href="https://github.com/jumpserver/docker-web/tags"><img src="https://img.shields.io/github/v/tag/jumpserver/docker-web?sort=semver&amp;filter=v5.*&amp;label=tag" alt="Phiên bản Docker Web" /></a></div></td>
      <td align="left">Cổng web và tài nguyên tĩnh của JumpServer</td>
    </tr>
  </tbody>
</table>

## Đóng góp

Chúng tôi hoan nghênh mọi đóng góp. Xem [CONTRIBUTING.md][contributing-link] để biết hướng dẫn.

## Giấy phép

Bản quyền (c) 2014-2026 FIT2CLOUD. Bảo lưu mọi quyền.

Dự án được cấp phép theo Giấy phép Công cộng GNU phiên bản 3 (GPLv3, sau đây gọi là "Giấy phép"); bạn chỉ được sử dụng tệp này khi tuân thủ Giấy phép. Bạn có thể xem bản sao của Giấy phép tại

https://www.gnu.org/licenses/gpl-3.0.html

Trừ khi pháp luật hiện hành yêu cầu hoặc có thỏa thuận bằng văn bản, phần mềm được phân phối theo Giấy phép được cung cấp "NGUYÊN TRẠNG", KHÔNG KÈM BẤT KỲ BẢO ĐẢM HAY ĐIỀU KIỆN NÀO, dù rõ ràng hay ngụ ý. Xem Giấy phép để biết các quy định cụ thể về quyền và giới hạn.

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
