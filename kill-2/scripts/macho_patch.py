#!/usr/bin/env python3
"""
Mach-O load command patcher for iOS version compatibility.
Replaces a system framework path with @rpath/stub, adjusts binary structure,
and updates all file offsets (segments, chained fixups, exports trie, code sig).

Usage: python3 macho_patch.py <binary> <old_path> <new_path> [--dry-run]
"""

import struct
import sys
import os

MH_MAGIC_64 = 0xfeedfacf
LC_SEGMENT_64 = 0x19
LC_LOAD_DYLIB = 0xC
LC_LOAD_WEAK_DYLIB = 0x80000018
LC_LAZY_LOAD_DYLIB = 0x20
LC_DYLD_CHAINED_FIXUPS = 0x80000034
LC_DYLD_EXPORTS_TRIE = 0x80000033
LC_CODE_SIGNATURE = 0x1D


def ru32(d, o): return struct.unpack_from('<I', d, o)[0]
def ru64(d, o): return struct.unpack_from('<Q', d, o)[0]
def wu32(d, o, v): struct.pack_into('<I', d, o, v)
def wu64(d, o, v): struct.pack_into('<Q', d, o, v)
def align_up(x, a): return (x + a - 1) & ~(a - 1)


def patch_binary(binary_path, old_path, new_path, dry_run=False):
    with open(binary_path, 'rb') as f:
        data = bytearray(f.read())

    if ru32(data, 0) != MH_MAGIC_64:
        print("Error: Not arm64 Mach-O"); return False

    ncmds = ru32(data, 16)
    sizeofcmds = ru32(data, 20)
    header_end = 32 + sizeofcmds
    new_path_b = new_path.encode('utf-8')

    # Find target load command
    off = 32
    target = None
    for i in range(ncmds):
        if off + 8 > len(data): break
        cmd, cs = ru32(data, off), ru32(data, off + 4)
        if cs == 0: break
        if cmd in (LC_LOAD_DYLIB, LC_LOAD_WEAK_DYLIB, 0x8000001C, LC_LAZY_LOAD_DYLIB):
            name_off = ru32(data, off + 8)
            ns = off + name_off
            ne = data.index(b'\x00', ns)
            name = data[ns:ne].decode('utf-8', errors='replace')
            if name == old_path:
                target = {'offset': off, 'cmd': cmd, 'cmdsize': cs, 'name_off': name_off, 'index': i}
        off += cs

    if not target:
        print(f"Error: '{old_path}' not found"); return False

    old_cs = target['cmdsize']
    name_off = target['name_off']
    new_cs = align_up(name_off + len(new_path_b) + 1, 8)
    size_diff = old_cs - new_cs

    print(f"cmd[{target['index']}] at 0x{target['offset']:x}: cmdsize {old_cs} → {new_cs} (save {size_diff})")

    if size_diff < 0:
        print("Error: new path longer than old"); return False
    if dry_run:
        print("[DRY RUN] OK"); return True
    if size_diff == 0:
        # In-place
        ns = target['offset'] + name_off
        data[ns:ns + len(old_path)] = new_path_b + b'\x00' * (len(old_path) - len(new_path_b))
        with open(binary_path + '.patched', 'wb') as f: f.write(data)
        print(f"✅ In-place done ({len(data)} bytes)")
        return True

    # Build new load command
    new_cmd = bytearray(new_cs)
    struct.pack_into('<II', new_cmd, 0, target['cmd'], new_cs)
    struct.pack_into('<I', new_cmd, 8, name_off)
    new_cmd[name_off:name_off + len(new_path_b)] = new_path_b

    # Split: load commands before target, after target, segment data
    before = data[:target['offset']]
    after = data[target['offset'] + old_cs:header_end]
    seg_data = data[header_end:]

    # Rebuild load commands
    new_cmds = bytearray(before + bytes(new_cmd) + after)

    # Update all file-position-dependent offsets
    o = 32
    for i in range(ncmds):
        if o + 8 > len(new_cmds): break
        cmd = ru32(new_cmds, o)
        cs = ru32(new_cmds, o + 4)
        if cs == 0: break

        if cmd == LC_SEGMENT_64:
            fo = ru64(new_cmds, o + 40)
            fs = ru64(new_cmds, o + 48)
            if fo > 0 and fs > 0:
                wu64(new_cmds, o + 40, fo - size_diff)
                print(f"  seg fileoff: 0x{fo:x} → 0x{fo - size_diff:x}")
        elif cmd in (LC_DYLD_CHAINED_FIXUPS, LC_DYLD_EXPORTS_TRIE, LC_CODE_SIGNATURE):
            do = ru32(new_cmds, o + 8)
            wu32(new_cmds, o + 8, do - size_diff)
            n = {LC_DYLD_CHAINED_FIXUPS:'fixups', LC_DYLD_EXPORTS_TRIE:'trie', LC_CODE_SIGNATURE:'codesig'}.get(cmd,'?')
            print(f"  {n} dataoff: 0x{do:x} → 0x{do - size_diff:x}")
        o += cs

    # Update header
    wu32(new_cmds, 20, sizeofcmds - size_diff)

    # Final binary: shifted load commands + segment data
    data = bytes(new_cmds) + seg_data

    with open(binary_path + '.patched', 'wb') as f:
        f.write(data)
    print(f"✅ Done ({len(data)} bytes)")
    return True


if __name__ == '__main__':
    if len(sys.argv) < 4:
        print(f"Usage: {sys.argv[0]} <binary> <old_path> <new_path> [--dry-run]")
        sys.exit(1)
    patch_binary(sys.argv[1], sys.argv[2], sys.argv[3], '--dry-run' in sys.argv)
