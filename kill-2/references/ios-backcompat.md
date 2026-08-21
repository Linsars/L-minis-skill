# iOS App 向下兼容逆向技术（iOS 18+ SDK → 旧系统运行）

> 来源：Working Copy / Blink 实战（2026-08）。配合 WF5 TrollStore 部署流程使用。

## 核心原理

iOS 18+ SDK（Xcode 26）编译的 binary 在旧系统上运行有两个障碍：

1. **`__DATA_CONST` flags=0x10**：iOS 18+ 新增，旧 kernel 强制只读 → ObjC fixup SIGBUS
2. **缺少新框架**：如 `libswiftSpatial.dylib`，`__swift_FORCE_LOAD` 强制加载

## 手术步骤

1. **修复 `__DATA_CONST` flags**：`0x10` → `0x0`（Mach-O LC_SEGMENT_64 的 flags 字段）
2. **替换 load command 路径**：系统路径 → `@rpath/stub.dylib`（原地字节替换，不改 cmdsize）
3. **改 MinimumOSVersion**：Info.plist 里降到目标版本
4. **删 _CodeSignature / SC_Info**：让 TrollStore ldid 重签

## 工具

- `macho_patch.py`（/var/minis/workspace/）：自动完成步骤 1+2
- Python zipfile + plistlib：完成步骤 3+4+5

## 关键教训

- **原地字节替换最安全**：不改 cmdsize → 不触发 chained fixup 偏移、segment fileoff 连锁问题
- **flags=0x10 是新发现的障碍**：不在 code signature 里，在 Mach-O header 里，ldid 修不了
- 路径替换必须用 null bytes 填充保持二进制大小不变
- 只改主 binary vs 全量修改：先确认哪些 binary 真正受影响（插件/Framework 可能本来兼容）
- 不要修改第三方 bundle（如 TelemetryDeck）的 MinimumOSVersion——保持原样
- zip 打包必须从 Payload/ 所在目录执行，避免多一层目录前缀
