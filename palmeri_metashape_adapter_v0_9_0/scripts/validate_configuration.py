"""Validate configuration offline; exit 0 means structural validity, never scientific approval."""

import argparse
import json
from pathlib import Path

from configuration_core import ConfigurationError, validate_configuration


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args(argv)
    try:
        result = validate_configuration(args.package)
        code = 0
    except ConfigurationError as exc:
        result = {"structural_status": "FAIL", "error": exc.code, "configuration": exc.configuration, "geomatic_acceptance": "NOT_GRANTED"}
        code = 1
    except (OSError, TypeError, KeyError, ValueError):
        result = {"structural_status": "FAIL", "error": "configuration_invalid", "geomatic_acceptance": "NOT_GRANTED"}
        code = 1
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
