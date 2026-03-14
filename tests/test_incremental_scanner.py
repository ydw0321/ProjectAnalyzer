"""Unit tests for incremental scanner helpers (no Neo4j required)."""
import json
import os
import tempfile

from _bootstrap import bootstrap_project_root

bootstrap_project_root()

from src.scanner.scanner import (
    compute_delta,
    load_hash_cache,
    save_hash_cache,
)


def _write_java(directory, filename, content="public class X {}"):
    path = os.path.join(directory, filename)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return path


def test_initial_run_all_changed():
    """With an empty cache, every file is 'changed'."""
    with tempfile.TemporaryDirectory() as tmpdir:
        _write_java(tmpdir, "A.java")
        _write_java(tmpdir, "B.java")

        all_files, changed, removed, new_cache = compute_delta(tmpdir, {})

        assert len(all_files) == 2
        assert len(changed) == 2
        assert removed == []
        assert len(new_cache) == 2


def test_unchanged_files_not_in_changed():
    """After saving the cache, an unchanged file must NOT appear in changed."""
    with tempfile.TemporaryDirectory() as tmpdir:
        _write_java(tmpdir, "A.java", "class A {}")

        _, _, _, cache1 = compute_delta(tmpdir, {})
        save_hash_cache(tmpdir, cache1)

        old = load_hash_cache(tmpdir)
        _, changed, removed, _ = compute_delta(tmpdir, old)

        assert changed == []
        assert removed == []


def test_modified_file_detected():
    """A file that is written again with different content must appear in changed."""
    with tempfile.TemporaryDirectory() as tmpdir:
        path = _write_java(tmpdir, "A.java", "class A {}")

        _, _, _, cache1 = compute_delta(tmpdir, {})
        save_hash_cache(tmpdir, cache1)

        # Modify the file
        with open(path, "w", encoding="utf-8") as f:
            f.write("class A { void foo() {} }")

        old = load_hash_cache(tmpdir)
        _, changed, removed, _ = compute_delta(tmpdir, old)

        assert os.path.normpath(path) in [os.path.normpath(c) for c in changed]
        assert removed == []


def test_removed_file_detected():
    """A file that is deleted must appear in removed_files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        path = _write_java(tmpdir, "A.java")
        _write_java(tmpdir, "B.java")

        _, _, _, cache1 = compute_delta(tmpdir, {})
        save_hash_cache(tmpdir, cache1)

        os.remove(path)

        old = load_hash_cache(tmpdir)
        _, changed, removed, new_cache = compute_delta(tmpdir, old)

        assert changed == []
        assert os.path.normpath(path) in [os.path.normpath(r) for r in removed]
        assert len(new_cache) == 1  # only B.java remains


def test_new_file_detected():
    """A brand-new file added after cache snapshot must appear in changed."""
    with tempfile.TemporaryDirectory() as tmpdir:
        _write_java(tmpdir, "A.java")

        _, _, _, cache1 = compute_delta(tmpdir, {})
        save_hash_cache(tmpdir, cache1)

        new_path = _write_java(tmpdir, "B.java")

        old = load_hash_cache(tmpdir)
        _, changed, removed, _ = compute_delta(tmpdir, old)

        assert os.path.normpath(new_path) in [os.path.normpath(c) for c in changed]
        assert removed == []
