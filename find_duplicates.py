#!/usr/bin/env python3
import argparse
import hashlib
import os
from collections import defaultdict
from difflib import SequenceMatcher
from pathlib import Path


def find_python_files(source_root):
    skip_dirs = {"__pycache__", ".venv", "venv", "env", ".env", ".git",
                 "node_modules", ".pytest_cache", "tests", "test", "archive"}
    py_files = []
    for root, dirs, fnames in os.walk(source_root):
        dirs[:] = [d for d in dirs if d not in skip_dirs and not d.startswith(".")]
        for f in fnames:
            if f.endswith(".py"):
                py_files.append(Path(root) / f)
    return sorted(py_files)


def compute_hash(path):
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except Exception:
        return None


def count_lines(path):
    try:
        with open(path, errors="replace") as f:
            return sum(1 for _ in f)
    except Exception:
        return 0


def similarity(a, b):
    try:
        return SequenceMatcher(None,
            a.read_text(errors="replace"),
            b.read_text(errors="replace")).ratio()
    except Exception:
        return 0.0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", default="~/gabagool")
    parser.add_argument("--similarity-threshold", type=float, default=0.85)
    args = parser.parse_args()

    source = Path(args.source).expanduser().resolve()
    print("Source: {}".format(source))

    files = find_python_files(source)
    print("Found {} Python files".format(len(files)))

    print("\nComputing SHA256 hashes...")
    by_hash = defaultdict(list)
    for f in files:
        h = compute_hash(f)
        if h:
            by_hash[h].append(f)

    duplicates_by_hash = {h: paths for h, paths in by_hash.items() if len(paths) > 1}
    total_dups = sum(len(v) for v in duplicates_by_hash.values()) - len(duplicates_by_hash)

    print("\n" + "=" * 60)
    print("IDENTICAL FILES (byte-for-byte)")
    print("=" * 60)
    print("Groups: {}".format(len(duplicates_by_hash)))
    print("Total redundant copies: {}".format(total_dups))
    print()

    for h, paths in sorted(duplicates_by_hash.items(), key=lambda x: -len(x[1])):
        size = paths[0].stat().st_size
        lines = count_lines(paths[0])
        print("Hash {}... ({} copies, {:,} bytes, ~{} lines):".format(
            h[:12], len(paths), size, lines))
        for p in paths:
            rel = p.relative_to(source)
            print("  {}".format(rel))
        print()

    print("=" * 60)
    print("SAME-NAME FILES IN DIFFERENT DIRECTORIES")
    print("=" * 60)
    print("(skipping __init__.py and byte-identical)")
    print("Threshold for yellow: {:.0%}".format(args.similarity_threshold))
    print()

    by_name = defaultdict(list)
    for f in files:
        by_name[f.name].append(f)

    interesting_groups = []
    for name, paths in sorted(by_name.items()):
        if len(paths) < 2 or name == "__init__.py":
            continue
        hashes = set(compute_hash(p) for p in paths)
        if len(hashes) == 1:
            continue
        interesting_groups.append((name, paths))

    print("Filenames with divergent content: {}\n".format(len(interesting_groups)))

    for name, paths in interesting_groups:
        print("### {} ({} versions):".format(name, len(paths)))
        for p in paths:
            rel = p.relative_to(source)
            lines = count_lines(p)
            size = p.stat().st_size
            print("  {} ({:,} lines, {:,} bytes)".format(rel, lines, size))

        if len(paths) == 2:
            sim = similarity(paths[0], paths[1])
            symbol = "[!!]" if sim > 0.95 else "[??]" if sim > args.similarity_threshold else "[ok]"
            print("  Similarity: {} {:.1%}".format(symbol, sim))
        elif len(paths) >= 3:
            print("  Pairwise similarities:")
            for i in range(len(paths)):
                for j in range(i + 1, len(paths)):
                    sim = similarity(paths[i], paths[j])
                    symbol = "[!!]" if sim > 0.95 else "[??]" if sim > args.similarity_threshold else "[ok]"
                    print("    [{}]<>[{}]: {} {:.1%}".format(i, j, symbol, sim))
        print()


if __name__ == "__main__":
    main()
