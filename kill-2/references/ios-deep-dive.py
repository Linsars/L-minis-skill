#!/usr/bin/env python3
"""
iOS 逆向深度特化 — 参考知识源 for kill-2 WF1
按需加载 (技能按需加载协议): 遇到 iOS 逆向、TrollStore、tweak 开发、Mach-O 分析时读取。
"""
# ── 这是 Python 格式的说明文件，内容全在 docstring 里 ──
"""
【TrollStore / 巨魔生态】

1. CoreTrust 漏洞原理 (opa334)
   - permasign: 利用 CoreTrust 漏洞让任意签名应用被系统信任
   - arbitrary entitlements: 签名时不验证 entitlement 合法性
   - 实现方式: ldid -S <ent.plist> 注入任意 com.apple.security.*
   
2. TrollStore 2/3 持久化机制
   - 通过 pocd (persistence of CoreTrust Daemon) 维持
   - root helper: 通过 install .tipa 获取高权限执行
   - 不会因重启丢失: 签名缓存在 CoreTrust 层持久化
   
3. 非越狱环境下 tweak 注入 (TrollFools)
   - dylib 注入: 通过 insert_dylib 或 @executable_path 注入
   - Cycript/Frida Gadget 嵌入 IPA 重签
   
4. TrollStore 高权限应用开发
   - entitlements 伪造: com.apple.private.*, com.apple.security.*
   - bootstrap 加载: 通过 TSUtil 和 TSRegister
   
参考: https://github.com/opa334/TrollStore (核心)
     https://github.com/alfiecg24/TrollInstallerX
     
【越狱 Tweak 开发 (Theos + Logos)】

1. Theos 项目结构
   - $(THEOS)/makefiles/ 通用 Makefile
   - nic.pl 模板选择: tweak_iphone (rootless/rootful/roothide)
   - control: Package ID, Depends, Conflicts, Priority
   
2. Logos 高级用法
   - %hook / %end: 方法 hook
   - %group / %ingroup: 条件编译
   - %ctor: 构造函数优先级控制
   - MSHookFunction: C/C++ 函数 hook
   - %hookf: C 函数 hook (基于 MSHookFunction)
   
3. 后端切换
   - Substitute (CoolStar): 默认现代越狱后端
   - libhooker (CoolStar): 替代 Cydia Substrate
   - Substrate (saurik): 经典后端
   
4. rootless 兼容
   - 路径: /var/jb/ 替代 /
   - 布局: 基位于 /var/jb/Library/MobileSubstrate/DynamicLibraries/
   
5. 系统进程 hook 模板
   - SpringBoard: UI 主进程 (Banner/Alert/SpringBoard hooks)
   - UIKit: UI 框架 (UIView/UIViewController/UINavigationController)
   - Preferences: 设置应用 (PSListController/PSViewController)

参考: Theos docs (https://theos.dev/docs)
     iPhoneDevWiki (https://iphonedev.wiki)
     opa334/Dopamine (https://github.com/opa334/Dopamine)

【Surge 脚本 (JavaScript Core MITM)】

1. Surge 脚本生命周期
   $surge.on('request', ...)  → 请求拦截
   $surge.on('response', ...) → 响应拦截
   $done()                     → 完成修改

2. 核心 API
   - $request.scheme / hostname / path / headers / body
   - $response.statusCode / headers / body
   - $session.socket.sessionConfig (session 级控制)
   - $network.getProxy / dnsResolve / fetch (网络工具)

3. 流式大文件处理
   - body = $request.bodyBytes ? $request.body.toLocaleString() : ''
   - 分块处理: 不要一次加载 >10MB body
   
4. .sgmodule 模块化规则
   - 模块 = 规则 + 脚本 + MITM
   - 动态加载: #!include 引用子模块
   
参考: Surge 官方知识库 (https://docs.nssurge.com)
     Surge Community (https://community.nssurge.com)

【Mach-O / ARM64 逆向】

1. Mach-O 结构
   - Fat Header: fat_magic, nfat_arch (多架构支持)
   - Mach Header: magic (MH_MAGIC_64), cputype (CPU_TYPE_ARM64), filetype
   - Load Commands: LC_SEGMENT_64, LC_SYMTAB, LC_DYSYMTAB, LC_ENCRYPTION_INFO
   - __TEXT: __text(代码), __cstring, __objc_methname, __objc_classname
   - __DATA: __objc_classlist, __objc_protolist, __objc_ivars
   - dyld chained fixups: 新式 rebase/bind (iOS 15+)
   - LC_ENCRYPTION_INFO: cryptid=1 表示 FairPlay 加密

2. ARM64 关键指令
   - ADRP/ADD: 地址加载 (PIE 位置无关的关键)
   - BL/BLR: 函数调用 (hook 点)
   - STP/LDP: 栈操作 (函数 prologue/epilogue)
   - RET/BR: 返回/跳转
   - PACIB/AUTIB: PAC 签名验证
   
3. 常用命令
   otool  -l <binary>         # Load Commands
   otool  -L <binary>         # 依赖库
   otool  -hv <binary>        # 架构+加密
   otool  -tV <binary>        # 反汇编 __TEXT 段
   jtool2 --analyze <binary>  # 全面分析
   jtool2 --sign <binary>     # 签名
   nm     <binary>            # 符号表
   nm -gU <binary>            # 外部符号
   strings - <binary>         # 字符串提取
   lipo   -thin arm64 -o out <binary>  # 提取单架构
   lipo   -info <binary>      # 架构信息
   class-dump -H <binary> -o out/  # ObjC 头文件
   objdump -macho -disassemble <binary>  # LLVM 反汇编

4. PAC 指针认证 bypass
   - PAC (Pointer Authentication Code): ARMv8.3 安全扩展
   - 绕过: PAC striping (A12-A15), PAC bypass via kernel exploit
   - 调试: 通过 LLDB pac_mask 判断 PAC 启用状态
   
参考: Advanced Apple Debugging & Reverse Engineering (书籍)
     r2wiki iOS section (https://wiki.radare.org/)
     jtool2: http://newosxbook.com/tools/jtool2.html

【内存反汇编与运行时操控】

1. Frida + r2frida
   - r2frida <device-id> <pid>   # radare2 联动
   - 内存搜索: /v <value> /w <hex> /x <masked bytes>
   - 内存修改: w <hex> @ <addr>
   
2. radare2 / Ghidra 内存联动
   - r2 -a arm64 -b 64 <file>      # 打开文件
   - aac / afl / pdf @ func        # 分析/函数列表/反汇编
   - Ghidra: headless 模式分析 + Frida runtime 验证
   
3. LLDB 批量自动化
   - lldb -b -o "script import script.py" <binary>
   - Python script: lldb.SBProcess / SBTarget / SBBreakpoint
   - 批量 dump: memory read --outfile dump.bin <addr> <size>
   
4. Heap Feng Shui / ROP
   - 堆风水: 通过 zone heap 布局控制 object 地址
   - ROP: gadget 搜索 (ropper / ROPgadget), chain 绕过 DEP
   - JIT spraying: JavaScriptCore JIT page 写 shellcode
   
5. 反反调试
   - ptrace(PT_DENY_ATTACH) → Frida: Interceptor.attach(ptrace)
   - sysctl 检测: NSGetEnviron / kinfo_proc 检查
   - syscall inline hook: 通过 mprotect(NX) + 指令 patch
   
参考: r2frida (https://github.com/nowsecure/r2frida)
     Frida docs (https://frida.re/docs/)
     LLDB Python API

【实战心智模型 — iOS 逆向特化】

1. 流程铁律
   静态 Mach-O 分析 (header+strings+class-dump)
   → 动态 Frida 枚举 (ObjC/Swift classes, methods)
   → 内存 dump + 反汇编验证
   → 编写 bypass/tweak/hook
   → Surge MITM 验证流量
   → TrollStore 持久化部署

2. 关键思维
   - 永远假设 App 有强完整性校验 (Jailbreak Detection, FairPlay, MSC)
   - 优先 hook 底层函数而非表层 UI
   - 内存补丁优于静态 patch
   - TrollStore 高权限模式下优先 entitlements 伪造而非 full jailbreak

3. 反检测哲学
   - 最小 hook 表面: 只 hook 必要函数
   - 随机化 hook 时机: 延迟 hook 至 app 启动后随机秒
   - 多 fallback 路径: hook 点失败自动切备用方法
   - C2 流量伪装: 结合 Cloudflare Workers 做中继隐藏流量
"""
