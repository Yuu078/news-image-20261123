#!/usr/bin/env python3
"""Deliver the finished poster for the 23 November 2026 news-image bounty.

The poster already exists in this repository as entry.png. All this
program does is place an exact copy of it where the grader looks
(MAKEFUN_OUTPUT_DIR, falling back to /output) and then check the copy
byte for byte against the original, so a silent truncation or a stale
file can never pass as a submission.

Nothing here touches the network or the clock, and nothing is random:
given the same committed entry.png, the output bytes are always the
same. Only the standard library is used, because the grading sandbox
is a bare Python image and this repository is mounted read-only there.
"""

import hashlib
import os
import shutil
import sys
from pathlib import Path

POSTER = Path(__file__).resolve().parent / "entry.png"
FALLBACK = Path("/output")


def fingerprint(path):
    """SHA-256 hex digest of a file, computed in one call."""
    with open(path, "rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def place_poster():
    if not POSTER.exists():
        print("entry.png is not beside main.py; nothing to deliver",
              file=sys.stderr)
        return 2
    target_dir = Path(os.getenv("MAKEFUN_OUTPUT_DIR") or FALLBACK)
    target_dir.mkdir(parents=True, exist_ok=True)
    delivered = target_dir / "entry.png"
    shutil.copyfile(POSTER, delivered)
    original = fingerprint(POSTER)
    copy = fingerprint(delivered)
    if original != copy:
        print("the copy in %s does not match entry.png" % target_dir,
              file=sys.stderr)
        return 1
    size = delivered.stat().st_size
    print("entry.png -> %s (%d bytes, sha256 %s)"
          % (delivered, size, copy))
    return 0


if __name__ == "__main__":
    sys.exit(place_poster())
