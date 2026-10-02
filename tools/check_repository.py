"""Offline repository checks using Python stdlib only; no Metashape imports or data reads."""

import ast
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tomllib
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "palmeri_metashape_adapter_v0_9_0"
sys.path.insert(0, str(PACKAGE / "scripts"))
from configuration_core import load_configuration, validate_configuration
from package_integrity import source_files, verify_package


def frontmatter(path):
    """Project's scalar name/description subset, not a general YAML validator."""
    text = Path(path).read_text(encoding="utf-8")
    match = re.match(r"^---\n(.*?)\n---(?:\n|$)", text, re.S)
    if not match:
        raise ValueError("skill_frontmatter_missing")
    fields = {}
    for line in match[1].splitlines():
        key, separator, value = line.partition(": ")
        if not separator or key in fields or not value or ": " in value or any(c in value for c in "#{}[]\"'<>"):
            raise ValueError("skill_scalar_subset_invalid")
        fields[key] = value
    if set(fields) != {"name", "description"} or fields["name"] != Path(path).parent.name or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", fields["name"]) or len(fields["name"]) > 64 or len(fields["description"]) > 1024:
        raise ValueError("skill_metadata_invalid")


def heading_anchors(text):
    """GitHub-style Unicode slugs, removing punctuation, preserving underscores; duplicate suffixes."""
    anchors, counts = set(), {}
    fence = None
    for line in text.splitlines():
        marker = re.match(r"^\s*(`{3,}|~{3,})", line)
        if marker:
            if fence is None:
                fence = marker[1][0]
            elif marker[1][0] == fence:
                fence = None
            continue
        match = re.match(r"^#{1,6}\s+(.+?)(?:\s+#+)?$", line) if fence is None else None
        if match:
            slug = re.sub(r"[^\w\- ]", "", match[1].strip().lower()).replace(" ", "-")
            count = counts.get(slug, 0)
            counts[slug] = count + 1
            anchors.add(slug if count == 0 else f"{slug}-{count}")
    return anchors


def markdown_links(path, repository=ROOT):
    """Validate inline Markdown links; external schemes are skipped, no network access."""
    path = Path(path)
    text = path.read_text(encoding="utf-8")
    checked = 0
    for target in re.findall(r"\[[^\]]*\]\(([^)]+)\)", text):
        target = target.strip().removeprefix("<").removesuffix(">")
        if re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*:", target):
            continue
        raw, separator, anchor = target.partition("#")
        destination = (path.parent / unquote(raw)).resolve() if raw else path.resolve()
        if not destination.is_relative_to(Path(repository).resolve()) or not destination.exists():
            raise ValueError("markdown_local_target_missing")
        if separator and unquote(anchor) not in heading_anchors(destination.read_text(encoding="utf-8")):
            raise ValueError("markdown_anchor_missing")
        checked += 1
    return checked


def validate_agents(directory):
    names = set()
    for path in sorted((Path(directory) / "agents").glob("*.toml")):
        profile = tomllib.loads(path.read_text(encoding="utf-8"))
        if any(type(profile.get(key)) is not str or not profile[key].strip() for key in ("name", "description", "developer_instructions")) or profile["name"] != path.stem or profile["name"] in names:
            raise ValueError("agent_profile_metadata_invalid")
        if path.stem in {"knowledge_researcher", "geomatics_reviewer", "verifier"} and profile.get("sandbox_mode") != "read-only":
            raise ValueError("review_agent_sandbox_invalid")
        names.add(profile["name"])
    if names != {"knowledge_researcher", "geomatics_reviewer", "code_worker", "verifier"}:
        raise ValueError("agent_profiles_missing")
    config = tomllib.loads((Path(directory) / "config.toml").read_text(encoding="utf-8"))
    limit = config.get("agents", {}).get("max_concurrent_threads_per_session")
    if type(limit) is not int or limit <= 0:
        raise ValueError("agent_concurrency_invalid")


def main():
    result = {"status": "FAIL", "processing_performed": False}
    try:
        sources = source_files(ROOT)
        counts = {"python": 0, "json": 0, "toml": 0, "skills": 0, "markdown_links": 0}
        for name, path in sources.items():
            if path.suffix == ".py":
                ast.parse(path.read_text(encoding="utf-8"), filename=name)
                counts["python"] += 1
            elif path.suffix == ".json":
                load_configuration(path)
                counts["json"] += 1
            elif path.suffix == ".md":
                counts["markdown_links"] += markdown_links(path)
        for path in sorted((ROOT / ".codex").rglob("*.toml")):
            tomllib.loads(path.read_text(encoding="utf-8"))
            counts["toml"] += 1
        validate_agents(ROOT / ".codex")
        for path in sorted((ROOT / ".agents" / "skills").glob("*/SKILL.md")):
            frontmatter(path)
            counts["skills"] += 1
        configuration = validate_configuration(PACKAGE)
        integrity = verify_package(PACKAGE)
        environment = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PYTHONUTF8="1")
        tests = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", str(PACKAGE / "tests"), "-p", "test_*.py", "-v"], cwd=ROOT, env=environment, capture_output=True, text=True)
        if tests.returncode:
            sys.stderr.write(tests.stdout + tests.stderr)
            raise ValueError("offline_tests_failed")
        # Recheck after fixture cleanup. No smoke or processing entry point is imported.
        verify_package(PACKAGE)
        summary = re.search(r"Ran (\d+) tests?", tests.stderr)
        skipped = re.search(r"skipped=(\d+)", tests.stderr)
        result.update(status="PASS", checks=counts, configuration=configuration, integrity=integrity,
                      pure_test_count=int(summary[1]) if summary else None,
                      skipped_test_count=int(skipped[1]) if skipped else 0, tests="PASS")
    except (ValueError, OSError, SyntaxError, TypeError, KeyError) as exc:
        result["error"] = str(exc) if isinstance(exc, ValueError) else "repository_check_failed"
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
