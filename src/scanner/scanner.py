import hashlib
import json
import os
from src.config import Config

_CACHE_FILENAME = ".parse_cache.json"


def scan_java_files(project_path):
    java_files = []
    for root, dirs, files in os.walk(project_path):
        dirs[:] = [d for d in dirs if d not in Config.EXCLUDE_DIRS]
        for file in files:
            if file.endswith(Config.JAVA_FILE_EXT):
                java_files.append(os.path.join(root, file))
    return java_files


def _compute_file_hash(file_path: str) -> str:
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _cache_path(project_path: str) -> str:
    return os.path.join(project_path, _CACHE_FILENAME)


def load_hash_cache(project_path: str) -> dict:
    path = _cache_path(project_path)
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def save_hash_cache(project_path: str, cache: dict) -> None:
    path = _cache_path(project_path)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(cache, f, indent=2, ensure_ascii=False)


def compute_delta(project_path: str, old_cache: dict):
    """Return (all_files, changed_files, removed_files, new_cache).

    changed_files: new or modified Java files.
    removed_files: files in old_cache that no longer exist on disk.
    new_cache: updated hash map for all current Java files.
    """
    all_files = scan_java_files(project_path)
    new_cache: dict = {}
    changed_files: list = []

    for fp in all_files:
        norm = os.path.normpath(fp)
        h = _compute_file_hash(fp)
        new_cache[norm] = h
        if old_cache.get(norm) != h:
            changed_files.append(fp)

    current_norm = set(new_cache.keys())
    removed_files = [fp for fp in old_cache if fp not in current_norm]

    return all_files, changed_files, removed_files, new_cache
