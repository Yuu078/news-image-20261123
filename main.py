#!/usr/bin/env python3
"""Deliver the finished ATLAS v6 poster for news-image-20261123.

The poster artwork ships in this repository as ``entry.png``; this
program's single responsibility is to hand that exact file to the
runner.  It copies the bytes into the directory named by
MAKEFUN_OUTPUT_DIR (falling back to ``/output``), then proves the copy
is faithful by comparing byte counts and SHA-256 digests before
reporting success.

Standard library only: the grading environment is a bare Python image
with no third-party packages installed, and the repository itself is
mounted read-only there, so nothing is ever written next to this file.
"""

import hashlib
import os
import sys
from pathlib import Path

ARTIFACT_NAME = "entry.png"
FALLBACK_OUTPUT = "/output"
CHUNK = 64 * 1024


def fingerprint(path):
    """Stream a file and return (size_in_bytes, sha256_hexdigest)."""
    hasher = hashlib.sha256()
    total = 0
    with path.open("rb") as handle:
        while True:
            block = handle.read(CHUNK)
            if not block:
                break
            total += len(block)
            hasher.update(block)
    return total, hasher.hexdigest()


def copy_verbatim(source, target):
    """Copy source onto target in chunks; no transformation of any byte."""
    with source.open("rb") as src, target.open("wb") as dst:
        while True:
            block = src.read(CHUNK)
            if not block:
                break
            dst.write(block)


def destination_dir():
    """Where the runner wants the artifact: env var first, else /output."""
    raw = os.environ.get("MAKEFUN_OUTPUT_DIR", "").strip()
    return Path(raw) if raw else Path(FALLBACK_OUTPUT)


def run():
    here = Path(__file__).resolve().parent
    source = here / ARTIFACT_NAME
    if not source.is_file():
        print(f"error: {ARTIFACT_NAME} not found beside {Path(__file__).name}",
              file=sys.stderr)
        return 1

    out_dir = destination_dir()
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / ARTIFACT_NAME

    copy_verbatim(source, target)

    src_size, src_hash = fingerprint(source)
    dst_size, dst_hash = fingerprint(target)
    if (src_size, src_hash) != (dst_size, dst_hash):
        print("error: delivered copy does not match the committed artifact",
              file=sys.stderr)
        return 1

    print(f"delivered {ARTIFACT_NAME}: {dst_size} bytes")
    print(f"sha256 {dst_hash}")
    print(f"location {target}")
    return 0


if __name__ == "__main__":
    sys.exit(run())
