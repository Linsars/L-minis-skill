#!/usr/bin/env python3
import argparse
import hashlib
import struct
import subprocess
import tempfile
from pathlib import Path

from codesign_check import CSMAGIC_CODEDIRECTORY, code_signature_range, parse_superblob, u32be


def refresh_code_directory(file_data: bytes, directory: bytes) -> tuple[bytes, list[int]]:
    if u32be(directory, 0) != CSMAGIC_CODEDIRECTORY:
        raise ValueError("alternate blob is not a CodeDirectory")
    hash_offset = u32be(directory, 16)
    code_count = u32be(directory, 28)
    code_limit = u32be(directory, 32)
    hash_size, hash_type, _, page_shift = struct.unpack_from("BBBB", directory, 36)
    if hash_type != 2 or hash_size != 32:
        raise ValueError("alternate CodeDirectory is not full SHA-256")
    if u32be(directory, 8) >= 0x20300 and len(directory) >= 64:
        extended_limit = struct.unpack_from(">Q", directory, 56)[0]
        if extended_limit:
            code_limit = extended_limit
    page_size = 1 << page_shift
    if code_limit > len(file_data):
        raise ValueError("CodeDirectory code limit exceeds file")
    if code_count != (code_limit + page_size - 1) // page_size:
        raise ValueError("CodeDirectory slot count is inconsistent")
    if hash_offset + code_count * hash_size > len(directory):
        raise ValueError("CodeDirectory hash table is truncated")
    output = bytearray(directory)
    changed = []
    for index in range(code_count):
        start = index * page_size
        end = min(start + page_size, code_limit)
        actual = hashlib.sha256(file_data[start:end]).digest()
        location = hash_offset + index * hash_size
        if output[location:location + hash_size] != actual:
            output[location:location + hash_size] = actual
            changed.append(index)
    return bytes(output), changed


def repair(input_path: Path, output_path: Path, signer: Path) -> list[int]:
    original = input_path.read_bytes()
    signature_offset, signature_size = code_signature_range(original)
    signature = original[signature_offset:signature_offset + signature_size]
    entries = parse_superblob(signature)
    by_slot = {slot: (magic, offset, blob) for slot, magic, offset, blob in entries}
    for required in (0, 0x1000, 0x10000):
        if required not in by_slot:
            raise ValueError(f"signature slot 0x{required:x} is missing")
    primary = by_slot[0][2]
    alternate_offset, alternate = by_slot[0x1000][1], by_slot[0x1000][2]
    cms_offset, old_cms = by_slot[0x10000][1], by_slot[0x10000][2]
    updated_alternate, changed = refresh_code_directory(original, alternate)
    if not changed:
        raise ValueError("no stale code-page hashes found")

    with tempfile.TemporaryDirectory(prefix="ctrepair-") as directory:
        temp = Path(directory)
        primary_path = temp / "primary.cd"
        alternate_path = temp / "alternate.cd"
        cms_path = temp / "cms.blob"
        primary_path.write_bytes(primary)
        alternate_path.write_bytes(updated_alternate)
        completed = subprocess.run(
            [str(signer), str(primary_path), str(alternate_path), str(cms_path)],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        )
        if completed.returncode:
            raise RuntimeError(f"CMS signer failed: {completed.stderr.strip()}")
        new_cms = cms_path.read_bytes()
    if len(new_cms) != len(old_cms):
        raise ValueError(f"CMS size changed ({len(old_cms)} -> {len(new_cms)})")

    output = bytearray(original)
    alt_start = signature_offset + alternate_offset
    cms_start = signature_offset + cms_offset
    output[alt_start:alt_start + len(updated_alternate)] = updated_alternate
    output[cms_start:cms_start + len(new_cms)] = new_cms
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(output)
    return changed


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--signer", type=Path, default=Path("/tmp/cms_resign"))
    args = parser.parse_args()
    changed = repair(args.input, args.output, args.signer)
    print("updated_pages=" + ",".join(str(index) for index in changed))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
