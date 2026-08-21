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

## local dylib 侦察三件套（2026-08 实战沉淀，RuntimeClassDump.dylib 验证）

| 脚本 | 用途 | 依赖 |
|------|------|------|
| `scripts/dylib_recon.py` | 头/flags/load commands/依赖库/sections/符号表/capstone 反汇编 | macholib + capstone |
| `scripts/objc_meta_scan.py` | ObjC 类→方法/ivar/协议/属性全量 dump，无需 class-dump | macholib |
| `scripts/macho_patch.py` | load command 路径替换 + 全链偏移修正（segments/chained fixups/trie/codesig） | 无 |

**踩坑记录（读这段省两小时）**：
1. fat 二进制：所有裸字节读取必须加 `h.offset` 切片基址；macholib 的 `h.MH_MAGIC` 在 fat 场景显示 CIGAM 值，端序要用磁盘魔数判
2. `section_64.offset` 是 **uint32 不是 uint64**——`<QQQ` 读成 `<QQII` 差一个字段全盘皆输
3. iOS 14+ 二进制类指针带 chained-fixup 编码（高位链标记）：`& 0x3FFFFFFFFFFF` 掩码还原
4. 小方法列表（entsize|0x80000000）：12 字节条目 `{i32 sel;i32 typ;i32 imp}` 每字段相对自身地址；sel 是经 `__objc_selrefs` 槽的间接引用，槽内容才是 fixup 编码的字符串指针
5. struct 格式串 `'<Q'*3` = `'<Q<Q<Q'` 非法——前缀只能出现一次

**objc_meta_scan 完全体（class-dump 等价）**：`python3 scripts/objc_meta_scan.py <bin> -o out.h`
输出可编译风格头文件（@interface/@protocol/category/@property），支持 fat/chained-fixup/相对方法表/selref 间接/元类类方法。
`--text` 回调试文本模式。已知残留：外部类的 category host 显示 ?、混淆 super 会出乱码名——与经典 class-dump 同级瑕疵。
