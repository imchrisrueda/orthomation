"""Verify maintained package sources; --write explicitly regenerates the manifest."""

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "palmeri_metashape_adapter_v0_9_0"
sys.path.insert(0, str(PACKAGE / "scripts"))
from package_integrity import IntegrityError, verify_package, write_manifest


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args(argv)
    try:
        result = write_manifest(PACKAGE) if args.write else verify_package(PACKAGE)
        code = 0
    except (IntegrityError, OSError) as exc:
        result = {"status": "FAIL", "error": str(exc) if isinstance(exc, IntegrityError) else "source_unreadable"}
        if isinstance(exc, IntegrityError):
            result.update(members=exc.members, line=exc.line)
        code = 1
    print(json.dumps(result, sort_keys=True))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
