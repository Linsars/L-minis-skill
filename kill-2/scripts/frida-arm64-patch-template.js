/* Frida + ARM64 内存 Patch 模板 — kill-2
 * 使用场景: 运行时绕过完整性校验、条件分支强制跳转、权限检查 bypass
 * 
 * 收集模式: 单次patch → 验证结果 → 清理痕迹
 */

'use strict';

/* ── 模块 1: ARM64 条件分支 Patch ── */
function patchConditionalBranch(moduleName, offset, patchBytes = null) {
    /*
     * 常用 ARM64 条件分支指令 (B.cond):
     *   B.EQ  0x54000000  →  NOP 0xD503201F (总是继续)
     *   B.NE  0x54000001  →  B  0x14000000 (总是跳转)
     *   CBNZ  X0, label  0xB5000000 →  CBZ X0 0x1A000000 (反转条件)
     *   TBZ   X0, #0      →  TBNZ (反转条件)
     */
    const target = Module.findBaseAddress(moduleName);
    if (!target) return { success: false, reason: 'module_not_found' };

    const addr = target.add(offset);
    const original = ptr(addr).readByteArray(4);
    if (!original) return { success: false, reason: 'read_failed' };

    const patch = patchBytes || [0xD5, 0x03, 0x20, 0x1F]; // NOP
    Memory.patchCode(addr, 4, code => {
        code.writeByteArray(patch);
    });

    return { success: true, original: original, address: addr };
}

/* ── 模块 2: 返回值劫持 ── */
function hookReturnValue(className, methodName, returnValue) {
    /*
     * Hook ObjC 方法并强制返回指定值
     * 适用: 越狱检测、许可证验证、环境检测
     */
    let hook = ObjC.classes[className];
    if (!hook) return { success: false, reason: 'class_not_found' };

    Interceptor.attach(hook[methodName].implementation, {
        onLeave(retval) {
            retval.replace(ptr(returnValue));
        }
    });
    return { success: true };
}

/* ── 模块 3: ARM64 内存搜索 + Patch ── */
function memorySearchAndPatch(module, searchPattern, patchPattern, range = null) {
    /*
     * ARM64 字节级搜索替换
     * 适用于: 签名校验字符串绕过、硬编码函数地址修改
     * 
     * 示例: 替换 "isJailbroken" 的 cmp w0, #0 → mov w0, #0
     *   搜索: cmp w0, #0     0x7100001F
     *   替换: mov w0, #0     0x52800000
     */
    const base = Module.findBaseAddress(module);
    if (!base) return { success: false, reason: 'module_not_found' };

    const size = range || Process.getRangeOfModule(module).size;
    const segment = base.add(ptr(size));
    
    let count = 0;
    const results = [];

    // 逐页搜索 (避免触发 page guard)
    const pageSize = 0x4000;
    for (let addr = base; addr < segment; addr = addr.add(pageSize)) {
        try {
            const search = searchPattern;
            const found = Memory.scanSync(addr, pageSize, search);
            for (const match of found) {
                Memory.patchCode(match.address, patchPattern.length, code => {
                    code.writeByteArray(patchPattern);
                });
                results.push({ address: match.address });
                count++;
            }
        } catch (e) {
            // 跳过不可读页面
            continue;
        }
    }

    return { success: count > 0, patched: count, results: results };
}

/* ── 模块 4: 反反调试 (ptrace/sysctl bypass) ── */
function bypassAntiDebug() {
    // ptrace PT_DENY_ATTACH bypass
    const ptrace = Module.findExportByName(null, 'ptrace');
    if (ptrace) {
        Interceptor.attach(ptrace, {
            onEnter(args) {
                if (args[0].toInt32() === 31) {
                    args[0] = ptr(-1);  // 返回 EFAULT
                }
            }
        });
    }

    // sysctl 调试器检测 bypass
    const sysctl = Module.findExportByName(null, 'sysctl');
    if (sysctl) {
        Interceptor.attach(sysctl, {
            onEnter(args) {
                this.call = false;
                const name = args[0].readPointer();
                if (name.readInt() === 0x0101) {  // CTL_KERN.KERN_PROC
                    this.call = true;
                }
            },
            onLeave(retval) {
                if (this.call) {
                    // 清空进程信息返回
                    retval.replace(ptr(-1));
                }
            }
        });
    }
    return { success: true, modules: ['ptrace', 'sysctl'] };
}

/* ── 模块 5: r2frida 集成 (内存反汇编) ── */
async function disassembleAt(moduleName, offset, count = 10) {
    try {
        const r2 = require('r2frida');
        const target = Module.findBaseAddress(moduleName).add(offset);
        const output = r2.cmd(`pd ${count} @ ${target}`);
        return { disassembly: output };
    } catch (e) {
        // r2frida 不可用, 降级到原始字节读取
        const target = Module.findBaseAddress(moduleName).add(offset);
        const bytes = ptr(target).readByteArray(4 * count);
        return { error: 'r2frida_unavailable', raw_bytes: bytes };
    }
}

// 使用示例:
//
// 1. 无条件绕过越狱检测
// hookReturnValue('JailbreakDetection', '+ isJailbroken', 0x0);
//
// 2. NOP 掉函数开头的条件分支
// patchConditionalBranch('UIKit', 0x12345C);
//
// 3. 搜索并替换硬编码检测字符串
// memorySearchAndPatch('AppModule', '48 00 00 00 6A 61 69 6C', '48 00 00 00 74 72 75 65');
//
// 4. 启动反反调试
// bypassAntiDebug();
