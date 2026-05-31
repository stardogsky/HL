"""
JSONL writer with hourly rotation and post-close gzip.

Design:
- Each (network, stream, coin) gets its own file
- Files rotate at the top of each UTC hour
- After rotation, old file is gzipped in background
- Append-only, line-by-line JSON
- Atomic: each write flushes immediately
"""
import asyncio
import gzip
import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path


class JsonlWriter:
    def __init__(self, base_dir: str, gzip_after_close: bool = True):
        self.base_dir = Path(base_dir)
        self.gzip_after_close = gzip_after_close
        self._files = {}  # key -> (file_handle, opened_at_hour, path)
        self._lock = asyncio.Lock()
        self._stats = {}  # key -> {"lines": int, "bytes": int}

    def _get_path(self, network: str, stream: str, coin: str = None) -> Path:
        """Build path: <base>/raw/<network>/<YYYY-MM-DD>/<stream>[_<coin>].jsonl"""
        now = datetime.now(timezone.utc)
        date_str = now.strftime("%Y-%m-%d")
        hour_str = now.strftime("%H")
        coin_safe = coin.replace("#", "h").replace("/", "_") if coin else None

        dir_path = self.base_dir / "raw" / network / date_str
        dir_path.mkdir(parents=True, exist_ok=True)

        if coin_safe:
            fname = f"{stream}_{coin_safe}_{hour_str}.jsonl"
        else:
            fname = f"{stream}_{hour_str}.jsonl"
        return dir_path / fname

    def _key(self, network: str, stream: str, coin: str = None) -> str:
        return f"{network}|{stream}|{coin or '_'}"

    async def write(self, network: str, stream: str, payload: dict, coin: str = None):
        """Write one line. Handles rotation transparently."""
        key = self._key(network, stream, coin)

        async with self._lock:
            current_hour = datetime.now(timezone.utc).strftime("%Y%m%d%H")

            # Rotate if hour changed
            if key in self._files:
                fh, opened_hour, path = self._files[key]
                if opened_hour != current_hour:
                    fh.close()
                    if self.gzip_after_close:
                        asyncio.create_task(self._gzip_file(path))
                    del self._files[key]

            # Open new file if needed
            if key not in self._files:
                path = self._get_path(network, stream, coin)
                fh = open(path, "a", buffering=1)  # line-buffered
                self._files[key] = (fh, current_hour, path)
                self._stats.setdefault(key, {"lines": 0, "bytes": 0})

            fh, _, _ = self._files[key]
            line = json.dumps(payload, separators=(",", ":"), default=str) + "\n"
            fh.write(line)

            self._stats[key]["lines"] += 1
            self._stats[key]["bytes"] += len(line)

    async def _gzip_file(self, path: Path):
        """Gzip a closed file, then delete original."""
        try:
            gz_path = path.with_suffix(path.suffix + ".gz")
            with open(path, "rb") as src, gzip.open(gz_path, "wb", compresslevel=6) as dst:
                shutil.copyfileobj(src, dst)
            path.unlink()
        except Exception as e:
            # Log but don't crash
            print(f"[writer] gzip failed for {path}: {e}")

    def get_stats(self) -> dict:
        """Return stats for healthcheck."""
        return dict(self._stats)

    async def close(self):
        """Close all open files (graceful shutdown)."""
        async with self._lock:
            for key, (fh, _, path) in self._files.items():
                fh.close()
                if self.gzip_after_close:
                    asyncio.create_task(self._gzip_file(path))
            self._files.clear()


# Special writer for one-shot JSON files (settlement events, etc)
class JsonFileWriter:
    """Writes complete JSON objects to standalone files (not append-mode)."""

    def __init__(self, base_dir: str):
        self.base_dir = Path(base_dir)

    def write(self, network: str, subdir: str, name: str, payload: dict) -> Path:
        """Write payload to <base>/raw/<network>/<subdir>/<name>.json"""
        dir_path = self.base_dir / "raw" / network / subdir
        dir_path.mkdir(parents=True, exist_ok=True)
        path = dir_path / f"{name}.json"
        with open(path, "w") as f:
            json.dump(payload, f, indent=2, default=str)
        return path
