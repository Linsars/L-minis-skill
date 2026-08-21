#!/usr/bin/env python3
"""objc_meta_scan.py — 静态 ObjC 元数据扫描器（local 模式 class-dump 等价物）
支持: fat 二进制 / 相对方法列表 / chained-fixup / 分类 / 协议完整声明 / 头文件输出
用法: python3 objc_meta_scan.py <binary> [-o out.h] [--text]
实战验证: RuntimeClassDump.dylib (fat, 25类/211方法)"""
import sys, struct
from macholib.MachO import MachO
from macholib.mach_o import *

MASK = 0x00003FFFFFFFFFFF
SCALARS = {'v':'void','B':'_Bool','c':'char','C':'unsigned char','s':'short','S':'unsigned short',
           'i':'int','I':'unsigned int','l':'long','L':'unsigned long','q':'long long',
           'Q':'unsigned long long','f':'float','d':'double','@':'id',':':'SEL','#':'Class',
           '*':'char *','?':'void *'}

# ---------- 二进制层 ----------
class Bin:
    def __init__(self, path):
        self.m = MachO(path)
        self.raw = open(path,'rb').read()
        h = self.h = self.m.headers[0]
        self.BASE = getattr(h, 'offset', 0)
        self.E = '<' if struct.unpack('<I', self.raw[self.BASE:self.BASE+4])[0] == 0xfeedfacf else '>'
        self.segs = []
        for lc in h.commands:
            cmd, cd = lc[0], lc[1]
            if cmd.cmd == LC_SEGMENT_64 and cd.filesize > 0:
                self.segs.append((cd.vmaddr, cd.vmsize, self.BASE + cd.fileoff))
        self.sections = {}
        off = self.BASE + 32
        for lc in h.commands:
            cmd, cd = lc[0], lc[1]
            if cmd.cmd == LC_SEGMENT_64:
                seg = cd.segname.decode().rstrip('\x00')
                so = off + 72
                for _ in range(cd.nsects):
                    s = self.raw[so:so+80]
                    if len(s) < 80: break
                    sname = s[0:16].split(b'\x00')[0].decode(errors='replace')
                    addr, size, fo, _al = struct.unpack(self.E+'QQII', s[32:56])
                    self.sections[f'{seg}.{sname}'] = (addr, size, fo)
                    so += 80
            off += cmd.cmdsize

    def v2f(self, vm):
        if not vm: return None
        vm &= MASK
        for va, vs, fo in self.segs:
            if va <= vm < va + vs: return fo + (vm - va)
        return None

    def rd(self, vm, n):
        fo = self.v2f(vm)
        return self.raw[fo:fo+n] if fo is not None else None

    def u(self, fmt, vm):
        b = self.rd(vm, struct.calcsize(fmt))
        return struct.unpack(self.E+fmt, b) if b else None

    def q(self, vm):
        r = self.u('Q', vm)
        return (r[0] & MASK) if r is not None else None

    def fu(self, fmt, fo):
        return struct.unpack(self.E+fmt, self.raw[fo:fo+struct.calcsize(fmt)])
    def fcstr(self, fo):
        if fo is None: return None
        e = self.raw.find(b'\x00', fo)
        return self.raw[fo:e].decode('latin1') if e != -1 else None

    def cstr(self, vm):
        fo = self.v2f(vm)
        if fo is None: return None
        e = self.raw.find(b'\x00', fo)
        return self.raw[fo:e].decode('latin1') if e != -1 else None

# ---------- 方法列表（双格式） ----------
def read_methods(b, list_vm):
    lm = list_vm & MASK
    er = b.u('I', lm)
    if er is None: return []
    ent_raw = er[0]
    count = b.u('I', lm+4)[0]
    out = []
    if ent_raw & 0x80000000:  # 小方法列表：12B 自相对，sel 经 selref 槽间接
        evm = lm + 8
        for j in range(count):
            fo12 = b.v2f(evm+j*12)
            if fo12 is None: break
            dsel, dtyp, dimp = struct.unpack(b.E+'iii', b.raw[fo12:fo12+12])
            slot = evm + j*12 + dsel
            sel = b.cstr(deref_ptr(b, slot)) or b.cstr(slot) or f'?{dsel}'
            typ = b.cstr(evm + j*12 + 4 + dtyp) or ''
            imp = evm + j*12 + 8 + dimp
            out.append((sel, typ, imp))
    else:  # 传统指针列表
        p = lm + 8
        for j in range(count):
            rr = b.u('3Q', p)
            if rr is None: break
            sel_vm, typ_vm, imp = rr
            sel = deref_ptr(b, sel_vm) or b.cstr(sel_vm) or '?'
            typ = b.cstr(typ_vm) or '' if typ_vm else ''
            out.append((sel, typ, imp))
            p += 24
    return out

def deref_ptr(b, slot_vm):
    fo = b.v2f(slot_vm)
    if fo is None: return None
    tgt = struct.unpack(b.E+'Q', b.raw[fo:fo+8])[0] & MASK
    return tgt if b.v2f(tgt) is not None else None

def read_props(b, list_vm):
    lm = list_vm & MASK
    if lm == 0: return []
    hdr = b.u('II', lm)
    if hdr is None: return []
    _, count = hdr
    out = []
    p = lm + 8
    for _ in range(count):
        r = b.u('2Q', p)
        if r is None: break
        nv, tv = r
        nm = b.cstr(nv) or '?'; at = b.cstr(tv) or ''
        out.append((nm, at)); p += 16
    return out

def parse_method_block(b, mv):
    """返回 [(sel, enc, imp)]，enc 为空则占位"""
    return read_methods(b, mv) if mv else []

# ---------- 模型构建 ----------
def parse_class(b, cls_vm, kind='class'):
    cfo = b.v2f(cls_vm)
    if cfo is None: return None
    isa, supervm, _, _vt, ro_vm = b.fu('5Q', cfo)
    rfo = b.v2f(ro_vm & ~7)
    if rfo is None: return None
    name_vm, meth_vm, prot_vm, ivar_vm, prop_vm = b.fu('5Q', rfo+24)
    name = b.cstr(name_vm) or '?'
    d = {'kind':kind, 'name':name, 'super':None, 'ivars':[], 'inst':[], 'cls':[],
         'props':[], 'cprops':[], 'protos':[]}
    if supervm:
        sfo = b.v2f(supervm)
        if sfo:
            sro = b.fu('Q', sfo+32)[0] & ~7 & MASK
            srfo = b.v2f(sro)
            d['super'] = b.fcstr(b.fu('Q', srfo+24)[0]) if srfo else hex(supervm & MASK)[2:]
        else:
            d['super'] = None
    if meth_vm: d['inst'] = read_methods(b, meth_vm)
    # 类方法在元类（isa 指向的类结构）里
    mfo = b.v2f(isa)
    if mfo:
        mro = b.fu('Q', mfo+32)[0] & ~7 & MASK
        mrfo = b.v2f(mro)
        if mrfo:
            mmeth = b.fu('Q', mrfo+32)[0] & MASK
            if mmeth: d['cls'] = read_methods(b, mmeth)
    pfo2 = b.v2f(prot_vm)
    if pfo2:
        cnt64 = b.fu('Q', pfo2)[0]; cnt = cnt64 if cnt64 < 10000 else b.fu('I', pfo2)[0]
        for i in range(min(cnt, 200)):
            pn_vm = b.fu('Q', pfo2+8+i*8)[0] & MASK
            pn = b.cstr(pn_vm) if pn_vm else None
            if pn: d['protos'].append(pn)
    if ivar_vm:
        ifo = b.v2f(ivar_vm)
        cnt = b.fu('I', ifo+4)[0]
        for i in range(cnt):
            optr, nm, ty, al, sz = b.fu('QQQII', ifo+8+i*32)
            ofo = b.v2f(optr)
            boff = b.fu('i', ofo)[0] if ofo is not None else -1
            d['ivars'].append((b.cstr(ty) or '?', b.cstr(nm) or '?', boff))
    if prop_vm:
        d['props'] = read_props(b, prop_vm)
    return d

def parse_protocol_full(b, pvm):
    pfo = b.v2f(pvm)
    if pfo is None: return None
    nm_vm, prots_vm, im, cm, oim, ocm, iprops, cprops = b.fu('8Q', pfo+8)
    d = {'name': b.cstr(nm_vm) or '?', 'protos': [], 'inst': [], 'cls': [],
         'opt_inst': [], 'opt_cls': [], 'props': [], 'cprops': []}
    if prots_vm:
        p2 = b.v2f(prots_vm)
        if p2:
            cnt64 = b.fu('Q', p2)[0]; cnt = cnt64 if cnt64 < 10000 else b.fu('I', p2)[0]
            for i in range(min(cnt,100)):
                sub = b.fu('Q', p2+8+i*8)[0] & MASK
                subfo = b.v2f(sub)
                sn = b.fcstr(subfo+8) if subfo else None   # protocol_t.mangledName @ +8
                if sn: d['protos'].append(sn)
    for src, dst in ((im,'inst'),(cm,'cls'),(oim,'opt_inst'),(ocm,'opt_cls')):
        if src: d[dst] = read_methods(b, src)
    for src, dst in ((iprops,'props'),(cprops,'cprops')):
        if src: d[dst] = read_props(b, src)
    return d

def scan(path):
    b = Bin(path)
    model = {'classes': [], 'cats': [], 'protocols': {}}
    secs = b.sections
    def find(suffix):
        return [(k,v) for k,v in secs.items() if k.endswith(suffix)]

    def sec_entries(suffix):
        """产出 (masked_ptr, i)：直接按文件偏移读 section 槽位"""
        for k,(addr,size,fo) in find(suffix):
            for i in range(size//8):
                off = b.BASE + fo + i*8
                if off+8 > len(b.raw): break
                pv = struct.unpack(b.E+'Q', b.raw[off:off+8])[0]
                yield pv & MASK

    for cvm in list(sec_entries('__objc_classlist')):
        if not cvm: continue
        d = parse_class(b, cvm)
        if d and d['name'] != '?': model['classes'].append(d)

    def class_name_of(vm):
        cfo = b.v2f(vm)
        if cfo is None: return None
        ro = b.fu('Q', cfo+32)[0]
        rfo = b.v2f(ro & ~7 & MASK)
        if rfo is None: return None
        return b.cstr(b.fu('Q', rfo+24)[0])

    for cvm in list(sec_entries('__objc_catlist')):
        if not cvm: continue
        cfo = b.v2f(cvm)
        if cfo is None: continue
        v = b.fu('6Q', cfo)
        if not v: continue
        nm, hostptr, im, cm, _pr, ip = v
        d = {'name': b.cstr(nm) or '?', 'host': '?', 'inst': [], 'cls': [], 'props': []}
        hn = class_name_of(hostptr & MASK) if hostptr else None
        d['host'] = hn or '?'
        if im: d['inst'] = read_methods(b, im)
        if cm: d['cls'] = read_methods(b, cm)
        if ip: d['props'] = read_props(b, ip)
        model['cats'].append(d)

    seen = set()
    for pvm in list(sec_entries('__objc_protolist')):
        if not pvm: continue
        full = parse_protocol_full(b, pvm)
        if full and full['name'] != '?' and full['name'] not in seen:
            seen.add(full['name'])
            model['protocols'][full['name']] = full

    # 类上挂的协议补全声明（按名从已收集协议表取，缺失的标记）
    for d in model['classes']:
        d['protos_missing'] = [p for p in d['protos'] if p not in model['protocols']]
    model['_bin'] = b
    return model
# ---------- 编码解码 ----------
def decode_enc(enc):
    """类型编码串 → [C 类型, ...]（方法签名第一个是返回值）"""
    out, i = [], 0
    def one(i):
        c = enc[i]
        if c == '@':
            if enc[i:i+2] == '@"':
                j = enc.index('"', i+2); return enc[i+2:j]+' *', j+1
            if enc[i+1:i+2] == '?': return 'void (^)()', i+2
            return 'id', i+1
        if c == '^':
            t, j = one(i+1); return t.rstrip(' *')+' *' if not t.endswith('*') else t+' *', j
        if c == '{':
            j = enc.index('=', i) if '=' in enc[i:i+60] else enc.index('}', i)
            nm = enc[i+1:j]; end = enc.index('}', j)
            return 'struct '+nm, end+1
        if c == '[':
            j = i+1
            while enc[j].isdigit(): j += 1
            t, j2 = one(j); return t+'[]', j2+1
        if c in SCALARS: return SCALARS[c], i+1
        return '?', i+1
    while i < len(enc):
        if enc[i].isdigit(): i += 1; continue
        t, i = one(i); out.append(t)
    return out or ['void']

def render_method(sel, enc, is_cls):
    sig = decode_enc(enc) if enc else ['void']
    ret = sig[0]; args = sig[3:] if len(sig) >= 3 else []
    parts = sel.split(':')
    prefix = '+' if is_cls else '-'
    if len(parts) == 1:
        return f'{prefix} ({ret}){parts[0]};'
    s = prefix + f' ({ret}){parts[0]}'
    for idx, argt in enumerate(args):
        s += f':({argt})a{idx+1}'
        if idx+1 < len(parts)-1: s += ' ' + parts[idx+1]
    return s + ';'

def render_props(attrs, ivar_map=None):
    # attrs 例: T@"CDParseType",&,N,V_type
    fields = attrs.split(',')
    tenc = fields[0][1:] if fields and fields[0].startswith('T') else '@'
    t = decode_enc(tenc)[0]
    flags = [f for f in fields[1:] if f and not f.startswith('V')]
    kw = {'R':'readonly','C':'copy','&':'retain','N':'nonatomic','W':'weak','A':'assign'}
    mods = ','.join(kw[f[0]] for f in flags if f[0] in kw) or 'nonatomic'
    vname = next((f[1:] for f in fields if f.startswith('V')), '')
    return t, mods, vname

def render_header(model):
    L = []
    names = {d['name'] for d in model['classes']} | {c['host'] for c in model['cats']}
    fw = sorted({d['super'] for d in model['classes'] if d.get('super')} |
                {c['host'] for c in model['cats']} | {p.split()[0] for d in model['classes'] for p in
                 sum([[iv[0].replace('@','id ').replace('struct ','') ] for iv in d['ivars']], [])} )
    fwd = sorted(n for n in names | {d.get('super') for d in model['classes'] if d.get('super')} if n and n != '?')
    if fwd:
        L.append('// 前向声明'); L.append('@class ' + ', '.join(sorted(set(fwd))) + ';\n')
    for pn, p in model['protocols'].items():
        L.append(f'@protocol {pn}')
        for base, tag in (('inst','-'),('cls','+'),('opt_inst',''),('opt_cls','')):
            ms = p[base]
            if not ms: continue
            if tag == '' : L.append('@optional')
            for sel, enc, _imp in ms:
                L.append(render_method(sel, enc, tag=='+'))
        for nm, at in p['props']:
            t, mods, _v = render_props(at)
            L.append(f'@property({mods}) {t} {nm};')
        L.append('@end\n')
    for d in model['classes']:
        sup = f" : {d['super']}" if d.get('super') else ''
        pr = f" <{', '.join(d['protos'])}>" if d['protos'] else ''
        L.append(f'@interface {d["name"]}{sup}{pr}')
        if d['ivars']:
            L.append('{')
            for tenc, inm, off in d['ivars']:
                t = decode_enc(tenc)[0] if tenc else 'id'
                L.append(f'    {t} {inm};')
            L.append('}')
        for sel, enc, _imp in d['inst']:
            L.append(render_method(sel, enc, False))
        for sel, enc, _imp in d['cls']:
            L.append(render_method(sel, enc, True))
        for nm, at in d['props']:
            t, mods, vname = render_props(at)
            syn = f' // @synthesize {vname.strip("_")}={vname}' if vname else ''
            L.append(f'@property({mods}) {t} {vname.strip("_") if vname else nm};{syn}')
        L.append('@end\n')
    for c in model['cats']:
        L.append(f'@interface {c["host"]} ({c["name"]})')
        for sel, enc, _imp in c['inst']: L.append(render_method(sel, enc, False))
        for sel, enc, _imp in c['cls']: L.append(render_method(sel, enc, True))
        L.append('@end\n')
    return '\n'.join(L)

def render_text(model):
    L = [f"== {len(model['classes'])} classes, {len(model['cats'])} categories, {len(model['protocols'])} protocols =="]
    for d in model['classes']:
        L.append(f"\n=== {d['name']} super={d.get('super')} protos={d['protos']} instSize")
        for sel, enc, imp in d['inst']: L.append(f'  -[{d["name"]} {sel}] {enc} @ {imp:#x}')
        for sel, enc, imp in d['cls']: L.append(f'  +[{d["name"]} {sel}] {enc} @ {imp:#x}')
        for t, nm, off in d['ivars']: L.append(f'  ivar {nm} : {t} @ {off}')
    for c in model['cats']:
        L.append(f"\n=== {c['host']} ({c['name']})")
        for sel, enc, imp in c['inst']: L.append(f'  -[{c["host"]}({c["name"]}) {sel}] {enc} @ {imp:#x}')
    for pn, p in model['protocols'].items():
        L.append(f"\n@protocol {pn}")
        for sel, enc, imp in p['inst']: L.append(f'  -{sel} {enc}')
        for sel, enc, imp in p['opt_inst']: L.append(f'  @opt -{sel} {enc}')
    return '\n'.join(L)

if __name__ == '__main__':
    args = sys.argv[1:]
    if not args: sys.exit(__doc__)
    path = args[0]
    outfile = args[args.index('-o')+1] if '-o' in args else None
    text = '--text' in args
    model = scan(path)
    out = render_text(model) if text else render_header(model)
    if outfile:
        open(outfile, 'w', encoding='utf-8').write(out + '\n')
        print(f'OK {outfile} ({len(out)} chars)')
    else:
        print(out)
