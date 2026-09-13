#!/usr/bin/env python3
"""Split a large generated archive into deterministic Git-compatible chunks."""

import argparse
import hashlib
from pathlib import Path


def digest(path):
    value = hashlib.sha256()
    with path.open("rb") as handle:
        while block := handle.read(1024 * 1024):
            value.update(block)
    return value.hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("--chunk-mib", type=int, default=90)
    parser.add_argument("--remove-source", action="store_true")
    args = parser.parse_args()
    if args.chunk_mib <= 0:
        raise ValueError("chunk size must be positive")
    chunk_size = args.chunk_mib * 1024 * 1024
    expected = digest(args.source)
    outputs = []
    with args.source.open("rb") as source:
        index = 0
        while block := source.read(chunk_size):
            target = args.source.with_name(f"{args.source.name}.part{index:03d}")
            target.write_bytes(block)
            outputs.append(target)
            index += 1
    actual = hashlib.sha256()
    for output in outputs:
        actual.update(output.read_bytes())
    if actual.hexdigest() != expected:
        raise RuntimeError("chunk concatenation hash mismatch")
    if args.remove_source:
        args.source.unlink()
    print(f"{len(outputs)} chunks; sha256={expected}")


if __name__ == "__main__":
    main()
