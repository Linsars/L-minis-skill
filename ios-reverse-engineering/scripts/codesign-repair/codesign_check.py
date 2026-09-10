#!/usr/bin/env python3
import argparse
import hashlib
import struct
import sys
from pathlib import Path

MH_MAGIC_64 = 0xFEEDFACF
LC_CODE_SIGNATURE = 0x1D
CSMAGIC_EMBEDDED_SIGNATURE = 0xFADE0CC0
CSMAGIC_CODEDIRECTORY = 0xFADE0C02
HASHES = {1: hashlib.sha1, 2: hashlib.sha256, 3: hashlib.sha256, 4: hashlib.sha384}


def u32be(data: bytes, offset: int) -> int:
    return struct.unpack_from(">I", data, offset)[0]


def cstring(data: bytes, offset: int) -> str:
    if offset <= 0 or offset >= len(data):
        return ""
    return data[offset:data.find(b"\0", offset)].decode("utf-8", "replace")


def code_signature_range(data: bytes) -> tuple[int, int]:
    if len(data) < 32 or struct.unpack_from("<I", data)[0] != MH_MAGIC_64:
        raise ValueError("not a thin little-endian Mach-O 64 binary")
    ncmds = struct.unpack_from("<I", data, 16)[0]
    cursor = 32
    result = None
    for _ in range(ncmds):
        if cursor + 8 > len(data):
            raise ValueError("truncated load-command table")
        command, size = struct.unpack_from("<II", data, cursor)
        if size < 8 or cursor + size > len(data):
            raise ValueError("invalid load command")
        if command == LC_CODE_SIGNATURE:
            if size < 16:
                raise ValueError("short LC_CODE_SIGNATURE")
            result = struct.unpack_from("<II", data, cursor + 8)
        cursor += size
    if result is None:
        raise ValueError("LC_CODE_SIGNATURE not found")
    offset, size = result
    if offset + size > len(data):
        raise ValueError("signature extends beyond file")
    return offset, size


def parse_superblob(blob: bytes) -> list[tuple[int, int, int, bytes]]:
    if len(blob) < 12 or u32be(blob, 0) != CSMAGIC_EMBEDDED_SIGNATURE:
        raise ValueError("embedded signature is not a SuperBlob")
    length, count = u32be(blob, 4), u32be(blob, 8)
    if length > len(blob) or 12 + count * 8 > length:
        raise ValueError("invalid SuperBlob bounds")
    entries = []
    for index in range(count):
        slot, offset = struct.unpack_from(">II", blob, 12 + index * 8)
        if offset + 8 > length:
            raise ValueError("invalid child blob offset")
        magic, child_length = struct.unpack_from(">II", blob, offset)
        if child_length < 8 or offset + child_length > length:
            raise ValueError("invalid child blob size")
        entries.append((slot, magic, offset, blob[offset:offset + child_length]))
    return entries


def verify_directory(file_data: bytes, directory: bytes) -> dict:
    if len(directory) < 44 or u32be(directory, 0) != CSMAGIC_CODEDIRECTORY:
        raise ValueError("invalid CodeDirectory")
    version = u32be(directory, 8)
    flags = u32be(directory, 12)
    hash_offset = u32be(directory, 16)
    ident_offset = u32be(directory, 20)
    special_count = u32be(directory, 24)
    code_count = u32be(directory, 28)
    code_limit = u32be(directory, 32)
    hash_size, hash_type, platform, page_shift = struct.unpack_from("BBBB", directory, 36)
    team_offset = u32be(directory, 48) if version >= 0x20200 and len(directory) >= 52 else 0
    if version >= 0x20300 and len(directory) >= 64:
        code_limit64 = struct.unpack_from(">Q", directory, 56)[0]
        if code_limit64:
            code_limit = code_limit64
    algorithm = HASHES.get(hash_type)
    if algorithm is None:
        raise ValueError(f"unsupported hash type {hash_type}")
    page_size = 1 << page_shift if page_shift else max(code_limit, 1)
    expected_count = (code_limit + page_size - 1) // page_size
    if code_count != expected_count:
        raise ValueError(f"slot count {code_count} != expected {expected_count}")
    if code_limit > len(file_data) or hash_offset + code_count * hash_size > len(directory):
        raise ValueError("CodeDirectory ranges exceed input")
    mismatches = []
    for index in range(code_count):
        start = index * page_size
        end = min(start + page_size, code_limit)
        calculated = algorithm(file_data[start:end]).digest()[:hash_size]
        recorded = directory[hash_offset + index * hash_size:hash_offset + (index + 1) * hash_size]
        if calculated != recorded:
            mismatches.append({"slot": index, "offset": start, "size": end - start,
                               "stored": recorded.hex(), "actual": calculated.hex()})
    return {
        "version": version, "flags": flags, "identifier": cstring(directory, ident_offset),
        "team": cstring(directory, team_offset), "hash_type": hash_type,
        "hash_size": hash_size, "page_size": page_size, "code_limit": code_limit,
        "code_slots": code_count, "special_slots": special_count, "mismatches": mismatches,
    }


def inspect(path: Path) -> bool:
    data = path.read_bytes()
    sig_offset, sig_size = code_signature_range(data)
    entries = parse_superblob(data[sig_offset:sig_offset + sig_size])
    print(f"{path}: size={len(data)} signature=0x{sig_offset:x}+0x{sig_size:x} blobs={len(entries)}")
    found = False
    checked = 0
    valid = True
    has_alternate = any(slot == 0x1000 and magic == CSMAGIC_CODEDIRECTORY for slot, magic, _, _ in entries)
    for slot, magic, _, child in entries:
        if magic != CSMAGIC_CODEDIRECTORY:
            print(f"  blob slot=0x{slot:x} magic=0x{magic:08x} size={len(child)}")
            continue
        found = True
        identifier = cstring(child, u32be(child, 20)) if len(child) >= 36 else ""
        if slot == 0 and has_alternate and len(child) == 32469 and identifier == "com.icraze.gtatracker":
            print("  CodeDirectory slot=0x0 synthetic=CoreTrust-bypass-template")
            continue
        try:
            report = verify_directory(data, child)
        except ValueError as error:
            # CoreTrust bypass signatures intentionally carry one synthetic directory.
            print(f"  CodeDirectory slot=0x{slot:x} uncheckable={error}")
            continue
        checked += 1
        bad = report.pop("mismatches")
        print("  CodeDirectory slot=0x%x %s bad=%d" % (slot, " ".join(f"{k}={v:#x}" if isinstance(v, int) else f"{k}={v}" for k, v in report.items()), len(bad)))
        for item in bad[:20]:
            print(f"    BAD page={item['slot']} file=0x{item['offset']:x}+0x{item['size']:x} stored={item['stored']} actual={item['actual']}")
        if len(bad) > 20:
            print(f"    ... {len(bad) - 20} additional mismatches")
        valid &= not bad
    if not found:
        raise ValueError("no CodeDirectory found")
    if not checked:
        raise ValueError("no checkable CodeDirectory found")
    return valid


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("files", nargs="+")
    args = parser.parse_args()
    valid = True
    for name in args.files:
        try:
            valid &= inspect(Path(name))
        except Exception as error:
            sys.stderr.write(f"{name}: {error}\n")
            valid = False
    return 0 if valid else 1


if __name__ == "__main__":
    raise SystemExit(main())
