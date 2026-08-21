---
name: ios-reverse-engineering
version: 1.0.0
description: iOS 逆向工程执行工具链。适用于 IPA 拆包解析、class-dump 头部分析、API 端点发现、SDK 指纹识别、保护机制检测、密钥扫描、Ghidra 深度反编译。本地 Python 做初步分析，深度分析通过 GitHub Actions macOS runner 执行。触发词：「iOS 逆向」「IPA 分析」「class-dump」「Mach-O」「iOS 反编译」「脱壳」「App 分析」「frida」「iOS hook」「iOS 安全审计」「越狱检测」。
---

# SKILL: iOS Reverse Engineering — 执行工具链

> kill-2 的 WF1（iOS逆向）提供「做什么、为什么切换路径」，本 skill 提供「怎么执行」。

## 一、分层分析策略

```
IPA 获取
  ├── 本地 Python (iSH) 快速分析
  │     ├── 解压 IPA (zip)
  │     ├── Info.plist 解析 (bundle ID/版本/权限声明)
  │     ├── 字符串扫描 (URL/密钥/endpoint)
  │     ├── SDK/框架指纹识别 (签名匹配)
  │     └── 初步报告输出 (JSON/Markdown)
  │
  └── GitHub Actions (macOS runner) 深度分析
        ├── class-dump 头部导出
        ├── otool 依赖分析 + 保护检测
        ├── codesign 签名验证
        ├── Ghidra 反编译 (可选)
        └── 完整安全审计报告
```

## 二、本地 Python 分析工具

见 `scripts/ios-quick-scan.py` — 独立可用，无外部依赖，属于 `local` 模式。功能：
- IPA 解压 & 结构分析
- Info.plist 提取
- URL scheme / Universal Link 发现
- 硬编码 API endpoint 正则扫描
- 云密钥模式匹配 (AWS/Azure/GCP/Firebase/Stripe)
- SDK 签名数据库匹配
- 保护机制启发式检测

输出：`<appname>-quick-report.json`

## 三、GitHub Actions 深度分析

当需要 class-dump / otool / Ghidra 分析时，切 `github-macos`：

```
minis 内操作:
1. 上传 IPA 到可公网访问的位置，或由 workflow 自己 curl 拉取
2. 触发 GH Actions workflow:
   gh workflow run ios-recon-gha.yml -f ipa_url=<https-url> -f artifact_name=ios-recon
3. 等待结果，下载 artifact 到 /var/minis/workspace/
```

workflow 模板见 `workflows/ios-recon-gha.yml`

## 失败模式与检查点

| 触发条件 | 一线修复 | 仍失败 → 兜底 |
|---|---|---|
| quick-scan.py 报错或输出为空 | 检查 IPA 是否 FairPlay 加密壳——加密包只能解析 plist/明文字符串 | 标记需脱壳，转已脱壳来源或 device-only |
| `gh workflow run` 404 | 确认 workflow 在默认分支且 Actions 已启用 | 本地跑 `scripts/ios-recon.sh` 的可执行部分 |
| artifact 下载为空 | `gh run view --log` 读完整日志定位（禁止只看单条错误） | 降级 `otool -oV` + `strings` 出报告 |
| class-dump 输出空/乱码 | Swift-only binary 不被 class-dump 支持 | 转 Ghidra 反编译或 frida 运行时枚举 |

**🔴 检查点**：
- 上传 IPA 到公网 URL 前 → 🛑 STOP：确认非客户敏感资产且有测试授权
- 检测到加密壳 → 不要继续堆静态分析，先解决脱壳来源

## 反模式（绝不做）

- 不对 App Store 加密 IPA 直接跑 class-dump（必然空输出，先确认脱壳状态）
- 不在 iSH 本地装 Ghidra/Java 重活（深度分析走 github-macos 分流）
- 不跳过 quick-scan 直接上 GH Actions（local 能做的先做，省 runner 时长）
- 不把 device-only 步骤写进 CI workflow（runner 上没有真机，frida -U 必败）

## 四、device-only 步骤

以下步骤需要真实设备/真实进程，不在 OpenMinis 本地直接运行：
- `frida -U/-H` 动态附加与类枚举
- `lldb` / `debugserver` 真机附加
- TrollStore / TrollFools 注入与 entitlements 行为验证
- Surge MITM 真流量解密/重写

## 五、参考来源

基础脚本源自 [incogbyte/iOS-reverse-engineering-claude-skill](https://github.com/incogbyte/iOS-reverse-engineering-claude-skill) — 包含 9 个 Shell 脚本 + 5 个 Ghidra Java 脚本。本地 Python 版是原版逻辑的移植适配。

## 六、触发条件

- "分析这个 IPA / App"
- "这个 App 有后门吗"
- "提取这个 App 的 API endpoint"
- "检测这个 App 的保护机制"
- "找这个 App 里的密钥"
- "反编译这个 Mach-O"
