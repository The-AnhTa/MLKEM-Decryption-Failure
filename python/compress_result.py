#!/usr/bin/env python3
"""Losslessly gzip a large result table using bounded memory."""

import argparse
import gzip
import shutil
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("--remove-source", action="store_true")
    args = parser.parse_args()
    target = args.source.with_suffix(args.source.suffix + ".gz")
    # Suppress the source filename and wall-clock timestamp so committed result
    # archives are byte-for-byte reproducible.
    with args.source.open("rb") as source, target.open("wb") as raw_output:
        with gzip.GzipFile(filename="", mode="wb", compresslevel=9,
                           fileobj=raw_output, mtime=0) as output:
            shutil.copyfileobj(source, output, length=1024 * 1024)
    if args.remove_source:
        args.source.unlink()
    print(target)


if __name__ == "__main__":
    main()
