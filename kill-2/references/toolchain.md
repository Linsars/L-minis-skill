# kill-2 工具链清单

## iOS 逆向工程

| 工具 | 用途 | 推荐版本/替代 |
|------|------|---------------|
| class-dump / class-dump-z | ObjC 类信息提取 | class-dump 3.5+ |
| Hopper Disassembler | 伪代码反编译 | v5+ / IDA Pro 8.x |
| Ghidra | 深度逆向分析 | NSA v11+ |
| Frida | 动态 Hook 与运行时操作 | 16.x / objection 1.x |
| objection | 移动端探索与攻击 | 1.11+ |
| Cycript | 运行时交互式调试 | Cydget fork |
| Frida Gadget | 非越狱设备注入 | 16.x 对应版本 |
| lldb / debugserver | 动态调试 | Xcode 16+ |
| otool / jtool / jtool2 | Mach-O 分析 | jtool2 universal |
| bfinject / insert_dylib | dylib 注入 | insert_dylib 1.0+ |
| optool | Mach-O 补丁 | 0.2+ |
| theos | iOS 越狱开发 | Sileo 版本 |
| MonkeyDev | 非越狱逆向开发 | latest |
| CrackerXI+ / frida-ios-dump | IPA 脱壳 | frida-ios-dump 更稳定 |
| nm / strings / lipo | 基础分析 | Xcode CLI |
| AppSync Unified | 安装未签名 IPA | Karen's Repo |

## 网络与 C2

| 工具 | 用途 | 推荐版本/替代 |
|------|------|---------------|
| Sliver | 自定义 C2 框架 | 1.5+ |
| Cobalt Strike | 商业级后渗透 (授权才用) | 4.9+ |
| Mythic | 跨平台 C2 | v3.2+ |
| Havoc | 现代 C2 框架 | latest |
| Nginx / HAProxy | C2 反向代理/CDN | 最新稳定版 |
| Cloudflare Workers | 隐蔽 C2 中继 | Wrangler 3+ |
| Tor / Orbot | 匿名网络 | latest |
| RedGuard | 安全 C2 前置网关 | latest |
| socat / ngrok / frp | 隧道 | frp v0.58+ |

## 二进制分析与 Exploit

| 工具 | 用途 | 推荐版本/替代 |
|------|------|---------------|
| pwndbg | GDB 插件 (堆分析) | dev branch |
| peda / gef | GDB 增强 | gef 稳定版 |
| radare2 / rizin | 命令行逆向 | rizin v0.7+ |
| Binary Ninja | 商业反编译器 | Cloud 版或 3.x |
| qemu-user | 跨架构动态分析 | 9.x |
| AFL++ / LibFuzzer | 模糊测试 | AFL++ 4.10+ |
| unicorn / qiling | 模拟执行框架 | Qiling 1.5+ |
| pwntools | exploit 快速开发 | 4.13+ |
| Ropper / ROPgadget | ROP gadget 搜索 | Ropper 1.13+ |
| one_gadget | libc one-shot 搜索 | latest |
| z3-solver | 约束求解 | Python API |

## 社会工程

| 工具 | 用途 | 推荐版本/替代 |
|------|------|---------------|
| SET (Social Engineering Toolkit) | 自动化社工框架 | 最新版 |
| Gophish | 钓鱼演练平台 | 0.12+ |
| Evilginx | 反向代理钓鱼 | v3.3+ |
| theHarvester | OSINT 邮箱/域名收集 | latest |
| Sherlock | 用户名跨平台搜索 | latest |
| Holehe | 邮箱服务商检测 | latest |
| Maltego | 图形化情报分析 | CE 版 |
| Recon-ng | OSINT 框架 | v5.x |
| SpiderFoot | 自动化 OSINT 扫描 | v4+ |
| PhoneInfoga | 电话号码 OSINT | latest |

## 网络与渗透

| 工具 | 用途 | 推荐版本/替代 |
|------|------|---------------|
| Metasploit | 漏洞验证框架 | 6.4+ |
| nmap / masscan | 端口扫描 | masscan 1.3+ |
| Burp Suite | Web 代理/渗透 | Pro 2024+ |
| Proxychains-ng | 代理链 | 4.17+ |
| Chisel / Ligolo-ng | 内网穿透 | Ligolo-ng 0.7+ |
| BloodHound | AD 攻击路径分析 | CE 6.x |
| Impacket | AD 协议工具包 | 0.12+ |
| Certipy / Certi | AD CS 攻击 | Certipy 4.8+ |
| Responder | LLMNR/NBT-NS 投毒 | latest |
| Bettercap | MITM 框架 | 2.33+ |
| mitmproxy | 流量劫持 | 11.x |

## Cloudflare

| 工具 | 用途 | 推荐版本/替代 |
|------|------|---------------|
| wrangler | Workers 部署管理 | v3.x |
| cfnts / oha | CF 网络测速 | latest |
| cloudscraper | Cloudflare 绕过 | Python lib |
| flaredoc | CF 文档速查 | latest |
| Pagerules / WAF bypass 技术 | 规则探测与绕过 | 手动技巧 |

## CTF 与开发

| 工具 | 用途 | 推荐版本/替代 |
|------|------|---------------|
| VS Code | 开发 IDE | Remote SSH |
| Docker / Docker Compose | 环境隔离 | latest |
| Python 3 + pip | 脚本主力 | 3.12+ |
| Rust / Go | 高性能工具 | Go 1.23+ |
| CyberChef | 数据编解码/加密 | Web 版 |
| sage | 数学计算 (Crypto) | 10.5+ |
| hashcat / John | 密码破解 | hashcat 6.2+ |
| volatility3 | 内存取证 | 2.x |
