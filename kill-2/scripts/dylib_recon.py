#!/usr/bin/env python3
"""dylib_recon.py — Mach-O dylib 全维侦察（local 模式，零外部依赖除 macholib/capstone）
用法: python3 dylib_recon.py <binary> [--disasm N]
输出: header/flags → load commands → 依赖库 → dyld info → sections → 符号表 → capstone 反汇编
合并自 iCloudID/IAPList 实战脚本 (2026-08)"""
import sys, struct
from macholib.MachO import MachO
from macholib.mach_o import *

try:
    from capstone import Cs, CS_ARCH_ARM64, CS_MODE_ARM
    HAS_CS = True
except ImportError:
    HAS_CS = False

def cstr(raw, off):
    e = raw.find(b'\x00', off)
    return raw[off:e].decode('utf-8', 'replace') if e != -1 else '?'

def main(path, disasm_n=128):
    m = MachO(path)
    raw = open(path, 'rb').read()
    h = m.headers[0]
    BASE = getattr(h, 'offset', 0)  # fat 二进制的切片基址
    if BASE: print(f'  [fat] slice @ {BASE:#x}')
    E = '<' if struct.unpack('<I', raw[BASE:BASE+4])[0] == 0xfeedfacf else '>'
    U32, U64 = E+'I', E+'Q'
    print(f'== {path}')
    print(f'magic={h.MH_MAGIC:#x} cputype={h.header.cputype:#x} filetype={h.header.filetype:#x} flags={h.header.flags:#x}')
    if h.header.flags & 0x10:
        print('  ⚠️ flags 含 0x10 (DYLD_IN_CACHE?) — iOS18+ 特征，旧系统需 macho_patch.py 处理')

    # load commands + 依赖库 + dyld info
    off = BASE + 32
    print('\n-- load commands --')
    for lc in h.commands:
        cmd, cd = lc[0], lc[1]
        name = {LC_SEGMENT_64:'LC_SEGMENT_64', LC_SYMTAB:'LC_SYMTAB', LC_DYSYMTAB:'LC_DYSYMTAB',
                LC_LOAD_DYLIB:'LC_LOAD_DYLIB', LC_ID_DYLIB:'LC_ID_DYLIB', LC_REEXPORT_DYLIB:'LC_REEXPORT',
                LC_LAZY_LOAD_DYLIB:'LC_LAZY_LOAD', LC_LOAD_WEAK_DYLIB:'LC_LOAD_WEAK', LC_UUID:'LC_UUID',
                LC_CODE_SIGNATURE:'LC_CODE_SIGNATURE', LC_FUNCTION_STARTS:'LC_FUNCTION_STARTS',
                LC_BUILD_VERSION:'LC_BUILD_VERSION', LC_DYLD_INFO_ONLY:'LC_DYLD_INFO_ONLY'}.get(cmd.cmd, f'LC_{cmd.cmd:#x}')
        extra = ''
        if cmd.cmd in (LC_LOAD_DYLIB, LC_ID_DYLIB, LC_REEXPORT_DYLIB, LC_LAZY_LOAD_DYLIB, LC_LOAD_WEAK_DYLIB):
            extra = ' ' + cstr(raw, off + cd.name)
        elif cmd.cmd == LC_SEGMENT_64:
            sn = cd.segname.decode().rstrip('\x00')
            extra = f' {sn} vm={cd.vmaddr:#x} fileoff={cd.fileoff:#x} filesize={cd.filesize:#x} initprot={cd.initprot:#o}'
        elif cmd.cmd == LC_CODE_SIGNATURE:
            extra = f' dataoff={cd.dataoff:#x} size={cd.datasize:#x}'
        elif cmd.cmd == LC_BUILD_VERSION:
            extra = f' platform={cd.platform} minos={cd.minos>>16}.{(cd.minos>>8)&0xff}.{cd.minos&0xff} sdk={cd.sdk>>16}.{(cd.sdk>>8)&0xff}.{cd.sdk&0xff}'
        print(f'  {name}{extra}')
        off += cmd.cmdsize

    # sections
    print('\n-- key sections --')
    off = BASE + 32
    for lc in h.commands:
        cmd, cd = lc[0], lc[1]
        if cmd.cmd == LC_SEGMENT_64:
            seg = cd.segname.decode().rstrip('\x00')
            so = off + 72
            for _ in range(cd.nsects):
                s = raw[so:so+80]
                if len(s) < 80: break
                sname = s[0:16].split(b'\x00')[0].decode()
                addr, size, fo, _align = struct.unpack(E+'QQII', s[32:56])
                if sname in ('__text','__stubs','__cstring','__objc_methname','__objc_classlist','__objc_data','__objc_const'):
                    print(f'  {seg}.{sname} addr={addr:#x} size={size:#x} fileoff={fo:#x}')
                so += 80
        off += cmd.cmdsize

    # 符号表
    for lc in h.commands:
        cmd, cd = lc[0], lc[1]
        if cmd.cmd != LC_SYMTAB: continue
        strtab = raw[BASE+cd.stroff:BASE+cd.stroff+cd.strsize]
        print(f'\n-- symbols ({cd.nsyms}) --')
        for j in range(min(cd.nsyms, 200)):
            o = BASE + cd.symoff + j*24
            if o+16 > len(raw): break
            n_strx, n_type, n_sect, n_desc, n_val = struct.unpack(E+'IBBHQ', raw[o:o+16])
            if n_strx < len(strtab):
                nm = cstr(strtab, n_strx)
                if nm and not nm.startswith('.'):
                    print(f'  {nm} @ {n_val:#x}')

    # capstone 反汇编 __text 前 N 条
    if disasm_n > 0 and HAS_CS:
        off = 32
        for lc in h.commands:
            cmd, cd = lc[0], lc[1]
            if cmd.cmd != LC_SEGMENT_64: continue
            so = off + 72
            for _ in range(cd.nsects):
                s = raw[so:so+80]
                sname = s[0:16].split(b'\x00')[0].decode()
                addr, size, fo, _align = struct.unpack(E+'QQII', s[32:56])
                if sname == '__text' and BASE+fo < len(raw):
                    md = Cs(CS_ARCH_ARM64, CS_MODE_ARM)
                    print(f'\n-- __text disasm (first {disasm_n}) --')
                    for i, insn in enumerate(md.disasm(raw[BASE+fo:BASE+fo+min(size, disasm_n*4)], addr)):
                        print(f'  {insn.address:#x}: {insn.mnemonic}\t{insn.op_str}')
                        if i >= disasm_n-1: break
                    return
                so += 80
            off += cmd.cmdsize

if __name__ == '__main__':
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    n = int(sys.argv[sys.argv.index('--disasm')+1]) if '--disasm' in sys.argv else 128
    main(sys.argv[1], n)
