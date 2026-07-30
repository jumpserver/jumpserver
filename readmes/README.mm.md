<div align="center">
  <a name="readme-top"></a>
  <a href="https://jumpserver.com" target="_blank"><img src="https://download.jumpserver.org/images/jumpserver-logo.svg" alt="JumpServer" width="300" /></a>
  
## Open-source PAM Platform (Bastion Host) တစ်ခုဖြစ်ပါသည်

</div>
<br/>

## JumpServer ဆိုတာဘာလဲ?

JumpServer ဆိုသည်မှာ Open-source Privileged Access Management (PAM) Platform တစ်ခုဖြစ်ပြီး DevOps နှင့် Sysadmin များအတွက် SSH, RDP, Kubernetes, Database နှင့် RemoteApp Endpoint များကို Web Browser မှတစ်ဆင့် လုံခြုံစွာနှင့် လိုအပ်သလို ဝင်ရောက်အသုံးပြုနိုင်အောင် ဆောင်ရွက်ပေးပါသည်။


<picture>
  <source media="(prefers-color-scheme: light)" srcset="https://www.jumpserver.com/images/jumpserver-arch-light.png">
  <source media="(prefers-color-scheme: dark)" srcset="https://www.jumpserver.com/images/jumpserver-arch-dark.png">
  <img src="https://github.com/user-attachments/assets/dd612f3d-c958-4f84-b164-f31b75454d7f" alt="Theme-based Image">
</picture>

## 🔑 အဓိက လုပ်ဆောင်ချက်များ (Key Features)

- Multi-Protocol Support: SSH, RDP, Database (MySQL, PostgreSQL, Oracle စသည်), Kubernetes (K8s), Web Application စတာတွေကို Web Browser ကနေတစ်ဆင့် လွယ်ကူစွာ Access လုပ်နိုင်ပါတယ်။

- Identity & Access Management: မတူညီတဲ့ IT Team/Admin တွေအတွက် Role အလိုက် Permission (RBAC) များကို စနစ်တကျ သတ်မှတ်ပေးနိုင်ပါတယ်။

- Session Recording & Auditing: အသုံးပြုသူတွေ ပြုလုပ်ခဲ့သမျှ Session များကို ဗီဒီယို သို့မဟုတ် Text အနေနဲ့ ပြန်လည် Record လုပ်ထားပြီး ဘာတွေလုပ်ဆောင်သွားလဲဆိုတာ Audit လိုက်နိုင်ပါတယ်။

- Real-time Monitoring: လက်ရှိ စနစ်ထဲမှာ မည်သူတွေ ဝင်ရောက် အသုံးပြုနေလဲဆိုတာကို Real-time ကြည့်ရှုနိုင်ပြီး လိုအပ်ပါက Session ကို တိုက်ရိုက် ဖြတ်တောက် (Kill) ပစ်နိုင်ပါတယ်။

- Web-based Terminal: မည်သည့် Software (e.g. Putty, Xshell) မှ ထပ်မံ Install လုပ်စရာမလိုဘဲ Web Browser (Chrome, Firefox စသည်) ကနေ တိုက်ရိုက် အသုံးပြုနိုင်ပါတယ်။

## 💡 ဘာကြောင့် JumpServer ကို အသုံးပြုသင့်တာလဲ?
- Security : Server တိုင်းရဲ့ Root Password / SSH Key များကို Admin တိုင်းဆီ ပေးစရာမလိုဘဲ JumpServer ကနေတစ်ဆင့် Centralized Access ပေးနိုင်ပါတယ်။

- Compliance & Audit: ISO, PCI-DSS အစရှိတဲ့ လုံခြုံရေး စံချိန်စံညွှန်းများအတွက် အသုံးပြုသူများ၏ ပြုလုပ်ချက် (Logs & Videos) များကို တိကျစွာ မှတ်တမ်းတင်ထားနိုင်ပါတယ်။

- Free & Open Source: Community Edition ကို အခမဲ့ ဒေါင်းလုဒ်ဆွဲ၍ ကိုယ်ပိုင် Server များတွင် တပ်ဆင်အသုံးပြုနိုင်ပါတယ်။

## အမြန်စတင်ရန် (Quickstart)

Linux Server (64-bit, အနည်းဆုံး CPU 4 Cores / RAM 8GB) တစ်ခုတွင် အောက်ပါ Command ဖြင့် အလွယ်တကူ တပ်ဆင်နိုင်ပါတယ်။

```sh
curl -sSL [https://github.com/jumpserver/jumpserver/releases/latest/download/quick_start.sh](https://github.com/jumpserver/jumpserver/releases/latest/download/quick_start.sh) | bash
```
တပ်ဆင်ပြီးပါက Browser မှတစ်ဆင့် `http://your-server-ip` သို့ သွားရောက်၍ မူလ Password (`admin` / `ChangeMe`) ဖြင့် ဝင်ရောက် အသုံးပြုနိုင်ပါတယ်။

[![JumpServer Quickstart](https://github.com/user-attachments/assets/0f32f52b-9935-485e-8534-336c63389612)](https://www.youtube.com/watch?v=UlGYRbKrpgY "JumpServer Quickstart")

## Screenshots
<table style="border-collapse: collapse; border: 1px solid black;">
  <tr>
    <td style="padding: 5px;background-color:#fff;"><img src= "https://github.com/jumpserver/jumpserver/assets/32935519/99fabe5b-0475-4a53-9116-4c370a1426c4" alt="JumpServer Console"   /></td>
    <td style="padding: 5px;background-color:#fff;"><img src= "https://github.com/user-attachments/assets/7c1f81af-37e8-4f07-8ac9-182895e1062e" alt="JumpServer PAM"   /></td>    
  </tr>
  <tr>
    <td style="padding: 5px;background-color:#fff;"><img src= "https://github.com/jumpserver/jumpserver/assets/32935519/a424d731-1c70-4108-a7d8-5bbf387dda9a" alt="JumpServer Audits"   /></td>
    <td style="padding: 5px;background-color:#fff;"><img src= "https://github.com/jumpserver/jumpserver/assets/32935519/393d2c27-a2d0-4dea-882d-00ed509e00c9" alt="JumpServer Workbench"   /></td>
  </tr>
  <tr>
    <td style="padding: 5px;background-color:#fff;"><img src= "https://github.com/user-attachments/assets/eaa41f66-8cc8-4f01-a001-0d258501f1c9" alt="JumpServer RBAC"   /></td>     
    <td style="padding: 5px;background-color:#fff;"><img src= "https://github.com/jumpserver/jumpserver/assets/32935519/3a2611cd-8902-49b8-b82b-2a6dac851f3e" alt="JumpServer Settings"   /></td>
  </tr>
  <tr>
    <td style="padding: 5px;background-color:#fff;"><img src= "https://github.com/jumpserver/jumpserver/assets/32935519/1e236093-31f7-4563-8eb1-e36d865f1568" alt="JumpServer SSH"   /></td>
    <td style="padding: 5px;background-color:#fff;"><img src= "https://github.com/jumpserver/jumpserver/assets/32935519/69373a82-f7ab-41e8-b763-bbad2ba52167" alt="JumpServer RDP"   /></td>
  </tr>
  <tr>
    <td style="padding: 5px;background-color:#fff;"><img src= "https://github.com/jumpserver/jumpserver/assets/32935519/5bed98c6-cbe8-4073-9597-d53c69dc3957" alt="JumpServer K8s"   /></td>
    <td style="padding: 5px;background-color:#fff;"><img src= "https://github.com/jumpserver/jumpserver/assets/32935519/b80ad654-548f-42bc-ba3d-c1cfdf1b46d6" alt="JumpServer DB"   /></td>
  </tr>
</table>

## Components

JumpServer consists of multiple key components, which collectively form the functional framework of JumpServer, providing users with comprehensive capabilities for operations management and security control.

| Project                                                | Status                                                                                                                                                                 | Description                                                                                             |
|--------------------------------------------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------------------|
| [Lina](https://github.com/jumpserver/lina)             | <a href="https://github.com/jumpserver/lina/releases"><img alt="Lina release" src="https://img.shields.io/github/release/jumpserver/lina.svg" /></a>                   | JumpServer ရဲ့ Web UI (Frontend Interface) ဖြစ်ပါတယ်။                                                                                       |
| [Luna](https://github.com/jumpserver/luna)             | <a href="https://github.com/jumpserver/luna/releases"><img alt="Luna release" src="https://img.shields.io/github/release/jumpserver/luna.svg" /></a>                   | Web Terminal အတွက် အသုံးပြုသည့် Component ဖြစ်ပါတယ်။                                                                                |
| [KoKo](https://github.com/jumpserver/koko)             | <a href="https://github.com/jumpserver/koko/releases"><img alt="Koko release" src="https://img.shields.io/github/release/jumpserver/koko.svg" /></a>                   | SSH နှင့် Telnet အစရှိသော Command-line Protocol များကို ချိတ်ဆက်ပေးတဲ့ Connector ဖြစ်ပါတယ်။                                                                |
| [Lion](https://github.com/jumpserver/lion)             | <a href="https://github.com/jumpserver/lion/releases"><img alt="Lion release" src="https://img.shields.io/github/release/jumpserver/lion.svg" /></a>                   | RDP, VNC အစရှိသော Graphical (GUI) Protocol များကို ချိတ်ဆက်ပေးတဲ့ Connector ဖြစ်ပါတယ်။                                                            |
| [Chen](https://github.com/jumpserver/chen)             | <a href="https://github.com/jumpserver/chen/releases"><img alt="Chen release" src="https://img.shields.io/github/release/jumpserver/chen.svg" />                       | Database များကို Web-based မှတစ်ဆင့် ချိတ်ဆက်ရန် အသုံးပြုပါတယ်။                                                                                    |  
| [Tinker](https://github.com/jumpserver/tinker)         | <img alt="Tinker" src="https://img.shields.io/badge/release-private-red" />                                                                                            | JumpServer Remote Application Connector (Windows)                                                       |
| [Panda](https://github.com/jumpserver/Panda)           | <img alt="Panda" src="https://img.shields.io/badge/release-private-red" />                                                                                             | JumpServer EE Remote Application Connector (Linux)                                                      |
| [Razor](https://github.com/jumpserver/razor)           | <img alt="Chen" src="https://img.shields.io/badge/release-private-red" />                                                                                              | JumpServer EE RDP Proxy Connector                                                                       |
| [Magnus](https://github.com/jumpserver/magnus)         | <img alt="Magnus" src="https://img.shields.io/badge/release-private-red" />                                                                                            | JumpServer EE Database Proxy Connector                                                                  |
| [Nec](https://github.com/jumpserver/nec)               | <img alt="Nec" src="https://img.shields.io/badge/release-private-red" />                                                                                               | JumpServer EE VNC Proxy Connector                                                                       |
| [Facelive](https://github.com/jumpserver/facelive)     | <img alt="Facelive" src="https://img.shields.io/badge/release-private-red" />                                                                                          | JumpServer EE Facial Recognition                                                                        

## Contributing

Pull Request (PR) များကို ပေးပို့၍ ပါဝင်ကူညီနိုင်ပါသည်။ လမ်းညွှန်ချက်များအတွက် [CONTRIBUTING.md][contributing-link] ကို ဝင်ရောက်ကြည့်ရှုပါ။

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










