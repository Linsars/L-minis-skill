#!/usr/bin/env python3
"""objc_meta_scan.py — 裸字节 ObjC 元数据扫描（无 class-dump，local 模式）
支持: fat 二进制 / 相对方法列表 / chained-fixup 指针掩码
用法: python3 objc_meta_scan.py <binary>"""
import sys, struct
from macholib.MachO import MachO
from macholib.mach_o import *

MASK = 0x00003FFFFFFFFFFF  # chained-fixup 链标记位剥离

def sections_of(raw, h, E):
    BASE = getattr(h, 'offset', 0)
    out, off = {}, BASE + 32
    for lc in h.commands:
        cmd, cd = lc[0], lc[1]
        if cmd.cmd == LC_SEGMENT_64:
            seg = cd.segname.decode().rstrip('\x00')
            so = off + 72
            for _ in range(cd.nsects):
                s = raw[so:so+80]
                if len(s) < 80: break
                sname = s[0:16].split(b'\x00')[0].decode(errors='replace')
                addr, size, fo, _a = struct.unpack(E+'QQII', s[32:56])
                out[f'{seg}.{sname}'] = (addr, size, fo)
                so += 80
        off += cmd.cmdsize
    return out

def main(path):
    m = MachO(path)
    raw = open(path, 'rb').read()
    h = m.headers[0]
    BASE = getattr(h, 'offset', 0)
    E = '<' if struct.unpack('<I', raw[BASE:BASE+4])[0] == 0xfeedfacf else '>'
    U = E

    segs = []
    for lc in h.commands:
        cmd, cd = lc[0], lc[1]
        if cmd.cmd == LC_SEGMENT_64 and cd.filesize > 0:
            segs.append((cd.vmaddr, cd.vmsize, BASE + cd.fileoff))

    def v2f(vm):
        vm &= MASK
        for va, vs, fo in segs:
            if va <= vm < va + vs: return fo + (vm - va)
        return None

    def cstr_at(vm):
        fo = v2f(vm)
        if fo is None: return None
        e = raw.find(b'\x00', fo)
        return raw[fo:e].decode('latin1') if e != -1 else None

    secs = sections_of(raw, h, E)
    hits = [(k, v) for k, v in secs.items() if k.endswith('__objc_classlist')]
    if not hits:
        print('非 ObjC binary（无 __objc_classlist）'); return
    k, (addr_, size, fo) = hits[0]
    n = size // 8
    print(f'== {path}: {n} classes')

    for i in range(n):
        cls_vm = struct.unpack(U+'Q', raw[BASE+fo+i*8:BASE+fo+i*8+8])[0]
        cfo = v2f(cls_vm)
        if cfo is None: continue
        _isa, supervm, _cache, _vtable, ro_vm = struct.unpack(U+'5Q', raw[cfo:cfo+40])
        rfo = v2f(ro_vm)
        if rfo is None: continue
        flags, inst_size = struct.unpack(U+'II', raw[rfo:rfo+8])
        name_vm, meth_vm, prot_vm, ivar_vm, prop_vm = struct.unpack(U+'5Q', raw[rfo+24:rfo+64])
        name = cstr_at(name_vm) or '?'
        print(f'\n=== {name} @ {(cls_vm & MASK):#x} super={(supervm & MASK):#x} instSize={inst_size}')

        if meth_vm:
            mfo = v2f(meth_vm)
            if mfo:
                entsize_raw = struct.unpack(U+'I', raw[mfo:mfo+4])[0]
                count = struct.unpack(U+'I', raw[mfo+4:mfo+8])[0]
                if entsize_raw & 0x80000000:  # 小方法列表：3×int32 自相对字段，name 经 selref 槽间接
                    evm = (meth_vm & MASK) + 8  # 首条目 VM 地址
                    p = mfo + 8
                    for j in range(count):
                        dsel, dtyp, dimp = struct.unpack(U+'iii', raw[p:p+12])
                        def deref_str(vm):
                            fo2 = v2f(vm)
                            if fo2 is None: return None
                            tgt = struct.unpack(U+'Q', raw[fo2:fo2+8])[0] & MASK
                            return cstr_at(tgt)
                        slot_vm = evm + j*12 + 0 + dsel
                        sel = deref_str(slot_vm) or cstr_at(slot_vm) or f'?{dsel}'
                        tvm = evm + j*12 + 4 + dtyp
                        typ = cstr_at(tvm) or deref_str(tvm) or ''
                        imp = (evm + j*12 + 8 + dimp) & MASK
                        print(f'  -[{name} {sel}] {typ} @ {imp:#x}')
                        p += 12
                else:  # 传统指针列表（老二进制 / 已 fixup dump）
                    p = mfo + 8
                    for j in range(count):
                        sel_vm, typ_vm, imp = struct.unpack(U+'3Q', raw[p:p+24])
                        print(f'  -[{name} {cstr_at(sel_vm & MASK) or "?"}] {cstr_at(typ_vm & MASK) or ""} @ {imp:#x}')
                        p += 24
        if prot_vm:
            pfo = v2f(prot_vm)
            if pfo:
                cnt = struct.unpack(U+'I', raw[pfo+4:pfo+8])[0]
                prots = []
                for j in range(cnt):
                    pa = v2f(struct.unpack(U+'Q', raw[pfo+8+j*8:pfo+16+j*8])[0])
                    if pa:
                        pn_vm = struct.unpack(U+'Q', raw[pa+24:pa+32])[0]  # protocol_t.name @ +24
                        pn = cstr_at(pn_vm)
                        if pn: prots.append(pn)
                if prots: print(f'  protocols: {", ".join(prots)}')
        if ivar_vm:
            ifo = v2f(ivar_vm)
            if ifo:
                cnt = struct.unpack(U+'I', raw[ifo+4:ifo+8])[0]
                p = ifo + 8
                for _ in range(cnt):
                    offptr, nm_vm, ty_vm, align, isz = struct.unpack(U+'QQQII', raw[p:p+32])
                    # 实例字节偏移存在 offptr 指向的位置里
                    byte_off = None
                    ofo = v2f(offptr)
                    if ofo is not None: byte_off = struct.unpack(U+'i', raw[ofo:ofo+4])[0]
                    iname = cstr_at(nm_vm) or '?'
                    itype = cstr_at(ty_vm) or '?'
                    print(f'  ivar {iname} : {itype} @ offset {byte_off}')
                    p += 32
        if prop_vm:
            pfo2 = v2f(prop_vm)
            if pfo2:
                cnt = struct.unpack(U+'I', raw[pfo2+4:pfo2+8])[0]
                p = pfo2 + 8
                for _ in range(cnt):
                    nm_vm, ty_vm = struct.unpack(U+'2Q', raw[p:p+16])
                    pn = cstr_at(nm_vm) or '?'
                    pt = cstr_at(ty_vm) or '?'
                    print(f'  property {pn} ({pt})')
                    p += 16

if __name__ == '__main__':
    if len(sys.argv) < 2: sys.exit(__doc__)
    main(sys.argv[1])
