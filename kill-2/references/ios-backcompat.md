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

## 诊断要点（2026-08-29 AllPic 实战补充）

- **0x80000018 = LC_LOAD_WEAK_DYLIB**：weak 链接的新框架（FoundationModels/libswiftSpatial 等）在旧系统缺失时 dyld 返回 nil **不崩**，只有 app 未加 #available guard 调到才崩——先查 weak/强链接再定手术范围
- **LC_BUILD_VERSION cmd 可能是 0x32**（Xcode 26 输出），不是教科书 0x2C——别只认一个值；minos=0x00110000 = 17.0。有的包 LC minos 比 Info.plist MinimumOSVersion 低（plist 写 18.0、LC 写 17.0），安装门槛在 plist、运行时门槛在 LC，两边分开看
- **强链接 dylib 存在性**按目标系统逐个查：SwiftData/_SwiftData_SwiftUI/libswiftObservation = iOS 17.0 就有；CoreTransferable = 16.0；AVFAudio 独立 framework = 17.0。别把 iOS 16 当默认目标

## 关键教训

- **原地字节替换最安全**：不改 cmdsize → 不触发 chained fixup 偏移、segment fileoff 连锁问题
- **flags=0x10 是新发现的障碍**：不在 code signature 里，在 Mach-O header 里，ldid 修不了
- 路径替换必须用 null bytes 填充保持二进制大小不变
- 只改主 binary vs 全量修改：先确认哪些 binary 真正受影响（插件/Framework 可能本来兼容）
- 不要修改第三方 bundle（如 TelemetryDeck）的 MinimumOSVersion——保持原样
- zip 打包必须从 Payload/ 所在目录执行，避免多一层目录前缀

## 1 刀最小手术（AllPic 实战验证）

**实验结论**：在 `v1（flags/plist/SC_Info）`基线手术（让 ipa 能装上）的基础上，**仅剩 1 刀**：imports pool 中 `_swift_getExtendedFunctionTypeMetadata` → `_swift_getFunctionTypeMetadata` 的原地改名。

**验证路径**（同一 ipa，删掉 deinit/isSafe 那两刀）：
- 符号池改名：从 imports 表 name_offset 到 symtab pool 的字节偏移，原地写入新名字 + null 填充；dyld 拉新名字的 GOT 槽 → 直接绑到 iOS 17 存在的 6 参版 `_swift_getFunctionTypeMetadata`，x0-x5 直传，其余被忽略
- crontime：启动玩不崩 → 那 8+1 个调用点在实际使用路径**不可达**，1 刀即最小手术
- 若后续使用中触发 deinit/isSafe 相关路径（FoundationModels/LanguageModel 相关），同一套流程可补 stub → ret / ret 1——**但这已是 app 特异性需求**，非最小手术必需

**变体：外挂注入等价方案**（不改主二进制）

**实现路线**：TrollFools/插件 dylib ctor 在 main 前跑，通过 chained fixups 解析 / __got 扫描主镜像的 imports[2117]（名字 `_swift_getExtendedFunctionTypeMetadata`）→ 找到 GOT 槽 vmaddr + slide → mprotect RW → 写入 `_swift_getFunctionTypeMetadata` 地址（dlsym）；
同样地，fishhook `rebind_symbols`（按名字匹配）→ replacement 是转发函数（6 参数透传旧版入口），rebind 4 名字：

- `_swift_getExtendedFunctionTypeMetadata` → 转发到 6 参版
- `_swift_coroFrameAlloc` → replacement = tail call malloc（fake stub 入口）
- `_swift_stdlib_isStackAllocationSafe` → replacement = `mov w0,#1; ret`
- `_swift_task_deinitOnExecutor` → replacement = `ret`

**优势**：主二进制零改动（不需要重签/重装 ipa），同一个注入 dylib 能通杀所有 iOS 26 SDK 编译的 app。且符号层面的绑定即可解决 deinit/isSafe 等需要「行为替换」的调用点，比「1 刀版手术」更全。

**技术权衡**：
- 1 刀版 = 主二进制零改动的「内针」，手术精准、风险低，前提是该 app 实际用不了那 9 个调用点
- 外挂注入版 = 通用钥匙，开销一次性、部署即生效、解决所有 iOS 26 向下兼容需求，但需要 TrollStore/插件生态支持（fishhook 支持 chained fixups 的版本），且注入可能被检测（同所有 tweak）

**示例代码**（外挂 dylib ctor 内）：

```c
// 拿 6 参版符号地址
orig = dlsym(RTLD_DEFAULT, "_swift_getFunctionTypeMetadata");

// fishhook rebind 4 名字（带 chained fixups 支持的版本）或手撸 fixups 解析 → GOT 槽 patch
// 此处伪代码：
rebind_symbols((struct rebinding[1]){{"_swift_getExtendedFunctionTypeMetadata", my_impl, NULL}}, 1);
// 或者手撸遍 LC_DYLD_CHAINED_FIXUPS → find imports name_offset → mprotect RW → 写指针

// 转发实现：
const Metadata *my_getExtended(uint32_t flags, uint32_t diffKind,
                               const void **params, const uint32_t *pflags,
                               const void *result, const void *actor,
                               uint32_t extFlags, const void *thrownError) {
    return orig(flags, diffKind, params, pflags, result, actor);
}
```

**技能归纳**：
- AllPic 实战全链：objectWillChange → Mirror → getExtended → GOT=0 导致 SIGSEGV
- 最小手术 = 1 刀符号池改名；或外挂注入等价方案
- 外挂版全覆盖 4 符号（getExtended/coroFrame/isSafe/deinit）——通用化路线
- 动作准则：先内针 1 刀（deinit/isSafe 不可达即停），再视作用路径补外挂或两刀
