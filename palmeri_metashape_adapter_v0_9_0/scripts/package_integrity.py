"""Byte-exact source manifest; never reads survey or generated data."""

import hashlib
from pathlib import Path, PurePosixPath
import re

SOURCE_SUFFIXES = {".py", ".json", ".md", ".txt", ".bat"}
EXCLUDED_DIRS = {"__pycache__", ".pytest_cache", "tmp", "generated", "generated_outputs", "control", ".git", ".venv", "venv", "env", "node_modules"}
MANIFEST = "SHA256SUMS.txt"


class IntegrityError(ValueError):
    def __init__(self, code, members=(), line=None):
        super().__init__(code)
        self.code = code
        self.members = list(members)
        self.line = line


def source_files(root):
    root = Path(root)
    if root.is_symlink() or getattr(root, "is_junction", lambda: False)():
        raise IntegrityError("symlink_package")
    resolved_root = root.resolve()
    result = {}

    def visit(directory):
        for path in sorted(directory.iterdir()):
            # Reject links before traversal, including links pretending to be source dirs.
            if path.is_symlink() or getattr(path, "is_junction", lambda: False)() or not path.resolve().is_relative_to(resolved_root):
                raise IntegrityError("symlink_entry")
            if path.is_dir():
                if path.name not in EXCLUDED_DIRS and not path.name.endswith(".files"):
                    visit(path)
            elif (path.suffix.lower() in SOURCE_SUFFIXES and path.name != MANIFEST
                  and not path.name.startswith(".test_")):
                result[path.relative_to(root).as_posix()] = path
    visit(root)
    return result


def manifest_entries(root):
    path = Path(root) / MANIFEST
    if path.is_symlink():
        raise IntegrityError("symlink_manifest")
    entries = {}
    try:
        lines = path.read_text(encoding="ascii").splitlines()
    except (OSError, UnicodeError) as exc:
        raise IntegrityError("manifest_unreadable") from exc
    for number, line in enumerate(lines, 1):
        match = re.fullmatch(r"([0-9a-f]{64})  (.+)", line)
        if not match:
            raise IntegrityError("manifest_line_invalid", line=number)
        digest, name = match.groups()
        parts = PurePosixPath(name)
        if (parts.is_absolute() or "\\" in name or ":" in name or
                any(p in {"", ".", ".."} for p in name.split("/"))):
            raise IntegrityError("manifest_path_invalid", line=number)
        if name in entries:
            raise IntegrityError("manifest_duplicate", (name,), number)
        entries[name] = digest
    if not entries:
        raise IntegrityError("manifest_empty")
    return entries


def verify_package(root):
    files = source_files(root)
    entries = manifest_entries(root)
    if set(files) != set(entries):
        raise IntegrityError("manifest_source_set_mismatch", sorted(set(files) ^ set(entries)))
    for name, path in files.items():
        if hashlib.sha256(path.read_bytes()).hexdigest() != entries[name]:
            raise IntegrityError("manifest_hash_mismatch", (name,))
    return {"status": "PASS", "source_file_count": len(files), "byte_exact": True}


def write_manifest(root):
    root = Path(root)
    files = source_files(root)
    target = root / MANIFEST
    if target.is_symlink():
        raise IntegrityError("symlink_manifest")
    content = "".join(
        f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {name}\n"
        for name, path in sorted(files.items())
    )
    target.write_bytes(content.encode("ascii"))
    return verify_package(root)
