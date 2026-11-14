"""Immutable, content-addressed inputs; no source checkout is ever written."""

from __future__ import annotations

import gzip
import hashlib
import json
import os
import subprocess
import tempfile
import zlib
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


def now():
    return datetime.now(timezone.utc).isoformat()


def digest(value):
    return hashlib.sha256(value).hexdigest()


def json_bytes(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True).encode()


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_bytes(json_bytes(value) + b"\n")
    tmp.replace(path)


def capture(path, store):
    """Copy exactly the size observed at open; detect concurrent rewrites."""
    store.mkdir(parents=True, exist_ok=True)
    for _ in range(3):
        with path.open("rb") as source:
            before = os.fstat(source.fileno())
            h = hashlib.sha256()
            with tempfile.NamedTemporaryFile(dir=store, delete=False) as target:
                temporary = Path(target.name)
                left = before.st_size
                while left:
                    block = source.read(min(left, 1024 * 1024))
                    if not block:
                        break
                    h.update(block)
                    target.write(block)
                    left -= len(block)
            after = os.fstat(source.fileno())
            current = path.stat()
            source.seek(0)
            verified = hashlib.sha256()
            remaining = before.st_size
            while remaining:
                block = source.read(min(remaining, 1024 * 1024))
                if not block:
                    break
                verified.update(block)
                remaining -= len(block)
        if (
            left
            or remaining
            or verified.digest() != h.digest()
            or current.st_ino != before.st_ino
            or after.st_size < before.st_size
            or (
                after.st_size == before.st_size
                and after.st_mtime_ns != before.st_mtime_ns
            )
        ):
            temporary.unlink()
            continue
        sha = h.hexdigest()
        destination = store / sha
        if destination.exists():
            temporary.unlink()
        else:
            temporary.replace(destination)
        return {"sha256": sha, "bytes": before.st_size, "mtime_ns": before.st_mtime_ns}
    raise RuntimeError(f"Input changed during snapshot: {path}")


def open_files():
    try:
        result = subprocess.run(
            ["lsof", "-nP", "-Fn"],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        return {
            line[1:] for line in result.stdout.splitlines() if line.startswith("n/")
        }
    except (OSError, subprocess.TimeoutExpired):
        return set()


def snapshot(root, state, store, code):
    started = now()
    opened = open_files()
    pattern = (
        "raw/ror/district_*/tahsil_*/village_*.jsonl.gz"
        if state == "odisha"
        else "raw/plots/*.jsonl.gz"
    )
    paths = sorted(root.glob(pattern))
    if not paths:
        raise FileNotFoundError(f"No checkpoints under {root}")
    files = {}
    for path in paths:
        relative = str(path.relative_to(root))
        item = capture(path, store)
        item["open_at_capture"] = str(path) in opened
        status = path.with_suffix(".status.json")
        if status.exists():
            item["status"] = capture(status, store)
        files[relative] = item
    dependencies = {
        "raw/villages.parquet": capture(root / "raw/villages.parquet", store)
    }
    aliases = root / "raw/pdf-village-aliases.json"
    if aliases.exists():
        dependencies[str(aliases.relative_to(root))] = capture(aliases, store)
    parser_paths = (
        [root / "parse_ror.py", root / "pdf_ror.py"]
        if state == "odisha"
        else sorted((root / "src/rajasthan_ror").glob("*.py"))
    )
    for path in parser_paths:
        dependencies[str(path.relative_to(root))] = capture(path, store)
    health = root / "logs/crawl-health.json"
    if health.exists():
        dependencies["logs/crawl-health.json"] = capture(health, store)
    return {
        "state": state,
        "source": str(root),
        "capture_started": started,
        "capture_finished": now(),
        "files": files,
        "dependencies": dependencies,
        "pipeline_code": code,
        "audit_mode": "census",
        "sampling_limit": 0,
    }


def records(path, counts):
    """Visit every complete JSON line, including those before an active tail."""
    try:
        with gzip.open(path, "rt", encoding="utf8") as stream:
            for line in stream:
                if not line.endswith("\n"):
                    counts["incomplete_json_tail"] += 1
                    continue
                try:
                    row = json.loads(line)
                    if not isinstance(row, dict):
                        raise ValueError("not an object")
                except (ValueError, UnicodeError):
                    counts["malformed_json"] += 1
                    continue
                counts["saved_attempt_rows"] += 1
                yield row
    except (EOFError, OSError, zlib.error, UnicodeError):
        counts["gzip_tail_or_decode_error"] += 1


def scan(path):
    counts = Counter()
    return list(records(path, counts)), counts
