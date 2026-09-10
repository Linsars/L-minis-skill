#!/usr/bin/env python3
import hashlib
import subprocess
import sys
import tempfile
from pathlib import Path

from codesign_check import code_signature_range, parse_superblob, inspect

PAIRS = (
    ("original/TrollStore.app/TrollStore", "fixed/TrollStore"),
    ("original/TrollStore.app/PersistenceHelper", "fixed/PersistenceHelper"),
    ("original/TrollStore.app/trollstorehelper", "fixed/trollstorehelper"),
)


def validate(original_path: Path, fixed_path: Path) -> None:
    original = original_path.read_bytes()
    fixed = fixed_path.read_bytes()
    original_offset, _ = code_signature_range(original)
    fixed_offset, fixed_size = code_signature_range(fixed)
    if len(original) != len(fixed) or original_offset != fixed_offset:
        raise ValueError(f"layout changed for {fixed_path}")
    if original[:fixed_offset] != fixed[:fixed_offset]:
        raise ValueError(f"signed content changed for {fixed_path}")
    entries = {slot: blob for slot, _, _, blob in parse_superblob(fixed[fixed_offset:fixed_offset + fixed_size])}
    primary, alternate, cms = entries[0], entries[0x1000], entries[0x10000]
    if hashlib.sha1(primary).digest() not in cms:
        raise ValueError(f"primary CodeDirectory digest missing from CMS for {fixed_path}")
    if hashlib.sha256(alternate).digest() not in cms:
        raise ValueError(f"alternate CodeDirectory digest missing from CMS for {fixed_path}")
    with tempfile.TemporaryDirectory(prefix="ctverify-") as directory:
        directory = Path(directory)
        (directory / "primary.cd").write_bytes(primary)
        (directory / "signature.cms").write_bytes(cms[8:])
        result = subprocess.run([
            "openssl", "cms", "-verify", "-binary", "-inform", "DER",
            "-in", str(directory / "signature.cms"), "-content", str(directory / "primary.cd"),
            "-noverify", "-out", str(directory / "content"),
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if result.returncode:
            raise ValueError(f"CMS verification failed for {fixed_path}: {result.stderr.decode().strip()}")
    if not inspect(fixed_path):
        raise ValueError(f"page verification failed for {fixed_path}")


def main() -> int:
    root = Path(__file__).resolve().parent
    for original, fixed in PAIRS:
        validate(root / original, root / fixed)
    print("all_checks=passed")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        sys.stderr.write(f"validation failed: {error}\n")
        raise SystemExit(1)
