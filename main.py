#!/usr/bin/env python3
"""Ship the ATLAS v6 poster for news-image-20261123.

The artwork lives in this repository as entry.png. This program copies
those exact bytes to the runner's output directory (MAKEFUN_OUTPUT_DIR,
or /output when that variable is unset) and proves the delivered copy
is identical by comparing byte counts and SHA-256 digests.

Pure standard library: the grading sandbox is a bare Python image, and
the repository is mounted read-only there, so this program writes
nothing beside itself and needs no third-party package.
"""

import hashlib
import os
import sys
from pathlib import Path

ARTIFACT = "entry.png"
DEFAULT_DIR = "/output"
BLOCK = 128 * 1024


def digest_of(path):
    """Return (size_in_bytes, sha256_hexdigest) for a file, streamed."""
    h = hashlib.sha256()
    total = 0
    with open(path, "rb") as handle:
        while True:
            chunk = handle.read(BLOCK)
            if not chunk:
                break
            total += len(chunk)
            h.update(chunk)
    return total, h.hexdigest()


def ship():
    # No network, no clock, no randomness: the bytes out are the bytes in.
    root = Path(__file__).resolve().parent
    src = root / ARTIFACT
    if not src.is_file():
        print("error: %s is missing next to %s"
              % (ARTIFACT, Path(__file__).name), file=sys.stderr)
        return 1
    wanted = os.environ.get("MAKEFUN_OUTPUT_DIR", "").strip() or DEFAULT_DIR
    out_dir = Path(wanted)
    out_dir.mkdir(parents=True, exist_ok=True)
    dst = out_dir / ARTIFACT
    with open(src, "rb") as fin, open(dst, "wb") as fout:
        while True:
            chunk = fin.read(BLOCK)
            if not chunk:
                break
            fout.write(chunk)
    before = digest_of(src)
    after = digest_of(dst)
    if before != after:
        print("error: the delivered copy differs from the committed "
              "artifact", file=sys.stderr)
        return 1
    print("delivered %s: %d bytes" % (ARTIFACT, after[0]))
    print("sha256 %s" % after[1])
    print("location %s" % dst)
    return 0


if __name__ == "__main__":
    raise SystemExit(ship())
