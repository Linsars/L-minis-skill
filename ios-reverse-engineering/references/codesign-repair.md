# CoreTrust 签名修复手册

<!-- verified 2026-09-03 TrollStore 2.1.1 修改版三二进制修复，用户实测通过 -->
<!-- 根因：修改版在 CoreTrust 重签后又动了二进制字节（__LINKEDIT 区），页哈希过期但 CMS 对 CD 的签名依然"有效" -->

## 一、症状识别

崩溃日志（.ips）特征，全部满足才进本流程：
- `termination: CODESIGNING / Invalid Page`，exception codes `0x32`
- 崩溃线程栈固定：`dyld4::JustInTimeLoader::applyFixups → forEachBindTarget → forEachChainedFixupTarget`
- fault 地址 = `__LINKEDIT` 段首 +0x8（chained fixups header），dyld 读该页解析绑定时被内核杀
- `codeSigningMonitor: 2`（无越狱严格模式）；越狱激活时同二进制能开（AMFI 被补丁，但仍校验页哈希——所以改字节不重签在越狱下也会崩，见 LiquidAss 案例）

关键区分：
| 现象 | 定性 | 路径 |
|---|---|---|
| 页哈希 bad=N（N 小，1~几十页） | 内容被改后未重签（后签名修改/传输损坏） | 本流程定点修复 |
| 页哈希 bad≈全部 | 二进制完全不同源（拿错文件/架构不匹配） | 停，重新确认目标 |
| 无 CMS / 纯 ldid adhoc（slot0 单 CD、flags=0x2） | 非 CoreTrust 形态，无越狱本来开不了 | 需完整 fastPathSign 流程，不是修复 |

## 二、Mach-O 内嵌签名结构事实（实测）

- SuperBlob `0xfade0cc0`；CodeDirectory `0xfade0c02`；BlobWrapper `0xfade0b01`（包 CMS DER）
- **CoreTrust bypass 形态双 CD**：slot 0 = 合成模板 CD（SHA1、identifier `com.icraze.gtatracker`、固定 32469B、逐字节等于 fastPathSign 的 AppStoreCodeDirectory.h 模板）→ 校验器必须跳过；slot 0x1000 = 真 CD（SHA-256，identifier `<bundle>.ed802085`、team `T8ALTGMVXN`）→ 内核逐页验它
- **内核页哈希只算到 codeLimit 截尾**（最后一页 = `codeLimit % page_size`，签名区不在内）。自研校验器必须同样截尾，否则最后一页永远 false mismatch
- 特殊 slot（entitlements/info.plist 等）从 hashOffset **负向**编址，内容没动就别碰
- CD version ≥0x20300 时 codeLimit64 字段优先于 32 位 codeLimit
- CMS signedAttrs 必含：contentType(pkcs7-data)、signingTime、messageDigest(=SHA256(primary CD))、`1.2.840.113635.100.9.1`（XML plist cdhashes，SHA256 截断到 20B）、`1.2.840.113635.100.9.2`（DER：SHA1 CDHash 20B + SHA256 CDHash 32B）
- CMS 含 signingTime → 重签字节必然不同，但只要结构同长同链即等价

## 三、修复流程

```bash
# 0) 编译重签器（iSH：apk add openssl-dev build-base 一次即可）
cc -O2 cms_resign.c -o /tmp/cms_resign $(pkg-config --cflags --libs openssl)

# 1) 校验定位坏页
python3 codesign_check.py <binary>
# 输出 "BAD page=N" 即坏页清单；bad=0 则无需修复

# 2) 定点修复（更新坏页哈希 + 重签 CMS，长度不变）
python3 repair_coretrust.py <binary> <binary.fixed>

# 3) 交付前三重验证（必须全过）
python3 final_validate.py   # 页哈希 bad=0 + cdhash 双写核对 + openssl cms verify
```

`repair_coretrust.py` 内部约束：CMS 重签输出与旧 CMS **必须等长**，不等长直接报错退出（等长才能原位替换，不动 load commands）。若遇到不等长场景（如重建整套签名），那是完整 fastPathSign 流程，不要用本定点工具。

## 四、落盘通道（Filza 权限实测 2026-09-03）

<!-- verified: Filza WebDAV 3.7.7 -->
- **Filza WebDAV 服务进程以 mobile 身份跑**：对 `/var/containers/Bundle/Application/<UUID>/<App>.app/`（root 属主）PUT/MOVE/DELETE 全 403/500；`/var/mobile` 可写（PUT 201）；`Depth: 2` 不支持（501，只支持 0/1）；大文件用 `mkfifo + curl -T` 流式（>100MB 直读会 MemoryError）
- **Filza 图形界面走 root helper 提权**：WebDAV 403 ≠ GUI 无权限。GUI 可直接把文件覆盖进 root 属主的 .app 目录（实测 TrollStore.app 三二进制覆盖成功）
- 推论：WebDAV 只能用于读 + 写 /var/mobile；写 .app 包目录交给用户 GUI 操作，别浪费时间找 WebDAV 写入法
- 教训：**同一 app 不同通道权限身份不同，探测一个通道的 403 不能代表全部通道**

## 五、验证标准（交付门禁）

1. `codesign_check.py`：所有可校验 CD bad=0（合成模板 CD 报 `synthetic=CoreTrust-bypass-template` 属正常）
2. cdhash 联动：SHA1(primary CD) 与 SHA256(alternate CD) 必须出现在新 CMS 的两个 cdhashes 属性里
3. `openssl cms -verify -binary -inform DER -in <cms> -content <primary.cd> -noverify` → Verification successful（**必须 -binary**，否则 OpenSSL 按 MIME 规范化内容导致 digest 不匹配假失败）
4. 文件长度与修复前一致；`cmp` 确认仅签名区字节不同
5. 设备实测：点图标能开即闭环；失败则回滚 .bak 后重新定性

## 六、资产索引

- 工具：`scripts/codesign-repair/`（本 skill）
- 实战案例源文件：`/var/minis/workspace/trollstore-repair/`（original/ 坏件、fixed/ 修复件、STATUS.md 过程记录）
- 对照来源：opa334/TrollStore `Exploits/fastPathSign/src/`（coretrust_bug.c 的 update_signature_blob 是 cms_resign.c 的复刻蓝本）
