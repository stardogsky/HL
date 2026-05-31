#!/usr/bin/env python3
"""
code_map.py — Static analysis of gabagool/ codebase.

Read-only analyzer. Walks Python files, parses with AST, detects:
- Import graph (who imports whom)
- Polymarket-specific keywords/constants (PLATFORM markers)
- Transport boundary (network/IPC/file I/O — TRANSPORT markers)
- Class inventory (all classes + their import-level usage)

Generates markdown reports for human review BEFORE any refactoring.
Pure stdlib. Does not modify any files in source tree.

Usage:
    python3 code_map.py --source ~/gabagool --output ~/HL/code_map
"""
import argparse
import ast
import json
import os
import re
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path


# ============================================================
# CLASSIFICATION CRITERIA
# ============================================================

POLYMARKET_KEYWORDS = [
    r"\byes_bid\b", r"\byes_ask\b", r"\bno_bid\b", r"\bno_ask\b",
    r"\byes_shares\b", r"\bno_shares\b",
    r"\btotal_yes\b", r"\btotal_no\b",
    r"\bpolymarket\b", r"\bCTF\b", r"\bctf\b",
    r"\btoken_id\b", r"\bcondition_id\b",
    r"\bpolygon\b", r"\bGNOSIS\b",
    r"\bpair_state\b", r"\blocked_pairs\b",
    r"\bmint_pair\b", r"\bsplit_pair\b",
    r"\bMIN_MKT_LOT\b",
]

PLATFORM_CONSTANTS_REGEX = [
    (r"TICK_SIZE\s*=\s*0\.01", "TICK_SIZE=0.01 (Polymarket tick)"),
    (r"MIN_MKT_LOT\s*=\s*5", "MIN_MKT_LOT=5 (Polymarket min lot)"),
    (r"market_duration_sec\s*=\s*900", "market_duration=900s (15min)"),
    (r"market_duration_sec\s*=\s*[0-9]+", "market_duration_sec hardcoded"),
]

TRANSPORT_MODULES = {
    "zmq", "websocket", "websockets", "aiohttp", "requests",
    "http.client", "urllib", "socket",
    "subprocess", "asyncio.subprocess",
}

TRANSPORT_KEYWORDS = [
    r"\bws\.send\b", r"\bws\.recv\b",
    r"\bzmq\b", r"\bSUB\b", r"\bPUB\b", r"\bDEALER\b", r"\bROUTER\b",
    r"\bsocket\.bind\b", r"\bsocket\.connect\b",
    r"\.post\(", r"\.get\(",
]


# ============================================================
# AST ANALYSIS
# ============================================================

class FileAnalysis:
    """Per-file static analysis result."""

    def __init__(self, path, source_root):
        self.path = path
        self.rel_path = str(path.relative_to(source_root))
        self.source = ""
        self.lines = 0
        self.imports_stdlib = []
        self.imports_thirdparty = []
        self.imports_local = []
        self.classes = []
        self.functions = []
        self.async_functions = []
        self.platform_hits = []
        self.transport_hits = []
        self.constant_hits = []
        self.has_platform = False
        self.has_transport = False
        self.label = "UNKNOWN"
        self.parse_error = None
        self._module_name = ""

    def to_dict(self):
        return {
            "rel_path": self.rel_path,
            "lines": self.lines,
            "label": self.label,
            "imports_local": self.imports_local,
            "imports_thirdparty": self.imports_thirdparty,
            "classes": self.classes,
            "functions": self.functions,
            "async_functions": self.async_functions,
            "platform_hits": [
                {"line": ln, "snippet": s[:100], "keyword": k}
                for ln, s, k in self.platform_hits
            ],
            "transport_hits": [
                {"line": ln, "snippet": s[:100], "marker": m}
                for ln, s, m in self.transport_hits
            ],
            "constant_hits": [
                {"line": ln, "snippet": s[:100], "label": l}
                for ln, s, l in self.constant_hits
            ],
            "has_platform": self.has_platform,
            "has_transport": self.has_transport,
            "parse_error": self.parse_error,
        }


def is_stdlib(module_name):
    top = module_name.split(".")[0]
    stdlib_set = {
        "os", "sys", "re", "json", "logging", "asyncio", "time", "datetime",
        "typing", "pathlib", "collections", "itertools", "functools",
        "math", "statistics", "decimal", "fractions", "random",
        "ast", "argparse", "subprocess", "threading", "multiprocessing",
        "socket", "urllib", "http", "ssl", "hashlib", "hmac", "secrets",
        "io", "tempfile", "shutil", "csv", "yaml", "configparser",
        "dataclasses", "enum", "abc", "contextlib", "warnings",
        "queue", "concurrent", "weakref", "gc", "platform", "locale",
        "copy", "pickle", "struct", "array", "ctypes",
    }
    return top in stdlib_set


def analyze_file(path, source_root):
    fa = FileAnalysis(path, source_root)

    try:
        source = path.read_text(encoding="utf-8", errors="replace")
        fa.source = source
        fa.lines = source.count("\n") + 1
    except Exception as e:
        fa.parse_error = "read failed: {}".format(e)
        return fa

    try:
        tree = ast.parse(source, filename=str(path))
    except SyntaxError as e:
        fa.parse_error = "syntax error: {}".format(e)
    else:
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    name = alias.name
                    if is_stdlib(name):
                        fa.imports_stdlib.append(name)
                    elif name in TRANSPORT_MODULES or any(name.startswith(t + ".") for t in TRANSPORT_MODULES):
                        fa.imports_thirdparty.append(name)
                        fa.has_transport = True
                    else:
                        fa.imports_thirdparty.append(name)
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                if node.level > 0:
                    fa.imports_local.append("." + module)
                elif is_stdlib(module):
                    fa.imports_stdlib.append(module)
                elif module in TRANSPORT_MODULES or any(module.startswith(t + ".") for t in TRANSPORT_MODULES):
                    fa.imports_thirdparty.append(module)
                    fa.has_transport = True
                else:
                    fa.imports_thirdparty.append(module)

            if isinstance(node, ast.ClassDef):
                fa.classes.append(node.name)
            elif isinstance(node, ast.FunctionDef):
                fa.functions.append(node.name)
            elif isinstance(node, ast.AsyncFunctionDef):
                fa.async_functions.append(node.name)

    for line_idx, line in enumerate(source.splitlines(), start=1):
        stripped = line.strip()
        if stripped.startswith("#"):
            continue

        for pattern in POLYMARKET_KEYWORDS:
            if re.search(pattern, line, re.IGNORECASE):
                fa.platform_hits.append((line_idx, line.strip()[:120], pattern.strip(r"\b")))
                fa.has_platform = True

        for pattern, label in PLATFORM_CONSTANTS_REGEX:
            if re.search(pattern, line):
                fa.constant_hits.append((line_idx, line.strip()[:120], label))

        for pattern in TRANSPORT_KEYWORDS:
            if re.search(pattern, line):
                fa.transport_hits.append((line_idx, line.strip()[:120], pattern.strip(r"\b()")))
                fa.has_transport = True

    fa.label = classify(fa)
    return fa


def classify(fa):
    plat_count = len(fa.platform_hits) + len(fa.constant_hits)

    if plat_count >= 3:
        return "PLATFORM"
    if fa.has_transport:
        return "TRANSPORT"
    if plat_count >= 1:
        return "PLATFORM"
    if (fa.classes or fa.functions or fa.async_functions) and fa.lines > 30:
        return "CORE"
    return "UTIL"


# ============================================================
# REPORT GENERATION
# ============================================================

def build_import_graph(files):
    rev_imports = defaultdict(list)
    fwd_imports = defaultdict(list)

    for fa in files:
        mod_name = fa.rel_path.replace("/", ".").replace(".py", "")
        fa._module_name = mod_name

    for fa in files:
        for imp in fa.imports_local + fa.imports_thirdparty:
            for other in files:
                if other.rel_path == fa.rel_path:
                    continue
                if imp == other._module_name or other._module_name.endswith("." + imp.lstrip(".")):
                    rev_imports[other.rel_path].append(fa.rel_path)
                    fwd_imports[fa.rel_path].append(other.rel_path)
                    break

    return {"forward": dict(fwd_imports), "reverse": dict(rev_imports)}


def write_summary(out_dir, files, graph, run_ts):
    by_label = defaultdict(list)
    for fa in files:
        by_label[fa.label].append(fa)

    total_lines = sum(f.lines for f in files)

    lines = []
    lines.append("# Code Map — Summary")
    lines.append("_Generated: {} UTC_".format(run_ts))
    lines.append("")
    lines.append("## Counts")
    lines.append("- Total files: **{}**".format(len(files)))
    lines.append("- Total lines: **{:,}**".format(total_lines))
    lines.append("")
    lines.append("## Distribution by classification")
    lines.append("")
    lines.append("| Label | Count | Lines | What it means |")
    lines.append("|---|---|---|---|")
    label_meaning = {
        "PLATFORM": "🔴 точно менять для multi-venue (есть Polymarket-specific код)",
        "TRANSPORT": "🟡 границы transport-слоя — обернуть в abstraction",
        "CORE": "🟢 pure logic — оставлять как есть или минимально",
        "UTIL": "⚪ utility — обычно platform-agnostic",
        "UNKNOWN": "❓ не классифицирован (parse error?)",
    }
    for label in ("PLATFORM", "TRANSPORT", "CORE", "UTIL", "UNKNOWN"):
        flist = by_label.get(label, [])
        if flist:
            ln = sum(f.lines for f in flist)
            lines.append("| {} | {} | {:,} | {} |".format(label, len(flist), ln, label_meaning[label]))
    lines.append("")

    rev = graph["reverse"]
    top_hubs = sorted(rev.items(), key=lambda x: -len(x[1]))[:15]
    lines.append("## Top 15 hubs (files imported by many others)")
    lines.append("Critical mass = if you change them, lots of code rebreaks.")
    lines.append("")
    lines.append("| File | Imported by | Label |")
    lines.append("|---|---|---|")
    for path, importers in top_hubs:
        fa = next((f for f in files if f.rel_path == path), None)
        label = fa.label if fa else "?"
        lines.append("| `{}` | {} | {} |".format(path, len(importers), label))
    lines.append("")

    platform_files = sorted(by_label.get("PLATFORM", []),
                            key=lambda f: -len(f.platform_hits) - len(f.constant_hits))
    if platform_files:
        lines.append("## 🔴 PLATFORM files (must refactor for multi-venue)")
        lines.append("Sorted by Polymarket-coupling intensity.")
        lines.append("")
        lines.append("| File | Lines | Platform hits | Constants | Top keywords |")
        lines.append("|---|---|---|---|---|")
        for fa in platform_files[:25]:
            top_kw = sorted(set(k for _, _, k in fa.platform_hits))[:4]
            lines.append("| `{}` | {} | {} | {} | {} |".format(
                fa.rel_path, fa.lines, len(fa.platform_hits),
                len(fa.constant_hits), ", ".join(top_kw)))
        lines.append("")

    transport_files = sorted(by_label.get("TRANSPORT", []),
                             key=lambda f: -len(f.transport_hits))
    if transport_files:
        lines.append("## 🟡 TRANSPORT files (boundaries to abstract)")
        lines.append("")
        lines.append("| File | Lines | Transport hits | Imports |")
        lines.append("|---|---|---|---|")
        for fa in transport_files[:15]:
            transport_imports = [
                i for i in fa.imports_thirdparty
                if i in TRANSPORT_MODULES or any(i.startswith(t + ".") for t in TRANSPORT_MODULES)
            ]
            lines.append("| `{}` | {} | {} | {} |".format(
                fa.rel_path, fa.lines, len(fa.transport_hits),
                ", ".join(transport_imports[:3])))
        lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("## Architectural recommendations")
    lines.append("")
    lines.append("1. **Files marked PLATFORM** — твой список «что точно менять» при multi-venue. Открой `polymarket_specific.md` для конкретных строк.")
    lines.append("2. **Files marked TRANSPORT** — поверхность для abstraction. Создавай `BridgeAdapter` interface, эти файлы общаются через него.")
    lines.append("3. **Top hubs** — менять в последнюю очередь. Чем больше importers, тем больше тестов прогонять.")
    lines.append("4. **CORE files** — большинство можно оставить нетронутым. Но проверить `polymarket_specific.md` — иногда хардкод проникает в CORE через имена методов.")
    lines.append("")
    lines.append("См. также:")
    lines.append("- `import_graph.md` — полный граф зависимостей")
    lines.append("- `polymarket_specific.md` — все строки с platform-coupling")
    lines.append("- `transport_boundary.md` — все I/O границы")
    lines.append("- `class_inventory.md` — все классы")

    (out_dir / "SUMMARY.md").write_text("\n".join(lines))


def write_import_graph(out_dir, files, graph):
    rev = graph["reverse"]
    fwd = graph["forward"]

    lines = ["# Import Graph", ""]

    lines.append("## Mermaid diagram (top hubs only)")
    lines.append("")
    lines.append("```mermaid")
    lines.append("graph LR")
    top_hubs = sorted(rev.items(), key=lambda x: -len(x[1]))[:10]
    for path, importers in top_hubs:
        for imp in importers[:5]:
            short_path = path.split("/")[-1].replace(".py", "")
            short_imp = imp.split("/")[-1].replace(".py", "")
            lines.append("    {} --> {}".format(
                short_imp.replace('-', '_'),
                short_path.replace('-', '_')))
    lines.append("```")
    lines.append("")

    lines.append("## Forward dependencies (X imports → Y)")
    lines.append("")
    for fa in sorted(files, key=lambda f: f.rel_path):
        deps = fwd.get(fa.rel_path, [])
        if deps:
            lines.append("### `{}` [{}]".format(fa.rel_path, fa.label))
            for dep in sorted(set(deps)):
                lines.append("- → `{}`".format(dep))
            lines.append("")

    lines.append("## Reverse dependencies (X is imported by → Y)")
    lines.append("")
    for path, importers in sorted(rev.items(), key=lambda x: -len(x[1])):
        if importers:
            fa = next((f for f in files if f.rel_path == path), None)
            label = fa.label if fa else "?"
            lines.append("### `{}` [{}] — imported by {} files".format(path, label, len(importers)))
            for imp in sorted(set(importers)):
                lines.append("- ← `{}`".format(imp))
            lines.append("")

    (out_dir / "import_graph.md").write_text("\n".join(lines))


def write_polymarket_specific(out_dir, files):
    lines = ["# Polymarket-Specific Code", ""]
    lines.append("Все места где код хардкодит Polymarket-специфику.")
    lines.append("Это **точно** то что менять при переходе на multi-venue.")
    lines.append("")
    lines.append("## Hardcoded constants")
    lines.append("")
    found_constants = False
    for fa in sorted(files, key=lambda f: f.rel_path):
        if fa.constant_hits:
            found_constants = True
            lines.append("### `{}`".format(fa.rel_path))
            for ln, snippet, label in fa.constant_hits:
                lines.append("- L{} **{}**".format(ln, label))
                lines.append("  ```python")
                lines.append("  {}".format(snippet))
                lines.append("  ```")
            lines.append("")
    if not found_constants:
        lines.append("_(no hardcoded constants matched)_")
        lines.append("")

    lines.append("## Polymarket keywords usage")
    lines.append("")
    files_with_hits = [f for f in files if f.platform_hits]
    files_with_hits.sort(key=lambda f: -len(f.platform_hits))
    for fa in files_with_hits:
        lines.append("### `{}` [{}] — {} hits".format(fa.rel_path, fa.label, len(fa.platform_hits)))
        by_kw = defaultdict(list)
        for ln, snippet, kw in fa.platform_hits:
            by_kw[kw].append((ln, snippet))
        for kw in sorted(by_kw.keys()):
            occurrences = by_kw[kw]
            lines.append("- `{}` ({} times) — example L{}: `{}`".format(
                kw, len(occurrences), occurrences[0][0], occurrences[0][1]))
        lines.append("")

    (out_dir / "polymarket_specific.md").write_text("\n".join(lines))


def write_transport_boundary(out_dir, files):
    lines = ["# Transport Boundary", ""]
    lines.append("Файлы которые общаются с внешним миром: WebSocket, HTTP, ZMQ, etc.")
    lines.append("Это границы для transport abstraction.")
    lines.append("")

    transport_files = [f for f in files if f.has_transport]
    transport_files.sort(key=lambda f: -len(f.transport_hits))

    for fa in transport_files:
        lines.append("## `{}` [{}]".format(fa.rel_path, fa.label))
        ext_imports = [
            i for i in fa.imports_thirdparty
            if i in TRANSPORT_MODULES or any(i.startswith(t + ".") for t in TRANSPORT_MODULES)
        ]
        if ext_imports:
            lines.append("**External imports:** {}".format(", ".join(ext_imports)))
            lines.append("")
        if fa.transport_hits:
            lines.append("**Transport calls in code:**")
            for ln, snippet, marker in fa.transport_hits[:30]:
                lines.append("- L{} (`{}`): `{}`".format(ln, marker, snippet))
            lines.append("")

    (out_dir / "transport_boundary.md").write_text("\n".join(lines))


def write_class_inventory(out_dir, files):
    lines = ["# Class Inventory", ""]
    lines.append("Все классы кодовой базы — где определены и где используются.")
    lines.append("")

    class_to_file = {}
    for fa in files:
        for cls in fa.classes:
            class_to_file[cls] = fa

    lines.append("| Class | Defined in | File label |")
    lines.append("|---|---|---|")
    for cls in sorted(class_to_file.keys()):
        fa = class_to_file[cls]
        lines.append("| `{}` | `{}` | {} |".format(cls, fa.rel_path, fa.label))
    lines.append("")

    lines.append("## Functions (top-level + async) per file")
    lines.append("")
    for fa in sorted(files, key=lambda f: f.rel_path):
        all_fn = list(fa.functions or []) + ["async {}".format(n) for n in (fa.async_functions or [])]
        if all_fn:
            lines.append("### `{}` [{}]".format(fa.rel_path, fa.label))
            for fn in all_fn:
                lines.append("- `{}`".format(fn))
            lines.append("")

    (out_dir / "class_inventory.md").write_text("\n".join(lines))


# ============================================================
# MAIN
# ============================================================

def find_python_files(source_root):
    skip_dirs = {"__pycache__", ".venv", "venv", "env", ".env", ".git",
                 "node_modules", ".pytest_cache", "tests", "test"}
    py_files = []
    for root, dirs, fnames in os.walk(source_root):
        dirs[:] = [d for d in dirs if d not in skip_dirs and not d.startswith(".")]
        for f in fnames:
            if f.endswith(".py"):
                py_files.append(Path(root) / f)
    return sorted(py_files)


def main():
    parser = argparse.ArgumentParser(description="Static analysis of gabagool codebase")
    parser.add_argument("--source", default="~/gabagool", help="Source code directory")
    parser.add_argument("--output", default="~/HL/code_map", help="Output directory for reports")
    args = parser.parse_args()

    source_root = Path(args.source).expanduser().resolve()
    output_root = Path(args.output).expanduser().resolve()

    if not source_root.exists():
        print("ERROR: source dir not found: {}".format(source_root), file=sys.stderr)
        sys.exit(1)

    run_ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    out_dir = output_root / run_ts
    out_dir.mkdir(parents=True, exist_ok=True)

    print("Source: {}".format(source_root))
    print("Output: {}".format(out_dir))

    py_files = find_python_files(source_root)
    print("Found {} Python files".format(len(py_files)))

    files = []
    for path in py_files:
        fa = analyze_file(path, source_root)
        files.append(fa)
        if fa.parse_error:
            print("  WARN: {}: {}".format(fa.rel_path, fa.parse_error))

    print("Building import graph...")
    graph = build_import_graph(files)

    print("Writing reports...")
    write_summary(out_dir, files, graph, run_ts)
    write_import_graph(out_dir, files, graph)
    write_polymarket_specific(out_dir, files)
    write_transport_boundary(out_dir, files)
    write_class_inventory(out_dir, files)

    (out_dir / "data.json").write_text(json.dumps(
        {"run_ts": run_ts, "files": [f.to_dict() for f in files], "graph": graph},
        indent=2, default=str
    ))

    by_label = defaultdict(int)
    for fa in files:
        by_label[fa.label] += 1
    print()
    print("=== SUMMARY ===")
    print("Total files: {}".format(len(files)))
    for label in ("PLATFORM", "TRANSPORT", "CORE", "UTIL", "UNKNOWN"):
        if by_label[label]:
            print("  {}: {}".format(label, by_label[label]))
    print()
    print("Reports in: {}".format(out_dir))
    print("Read first: {}/SUMMARY.md".format(out_dir))


if __name__ == "__main__":
    main()