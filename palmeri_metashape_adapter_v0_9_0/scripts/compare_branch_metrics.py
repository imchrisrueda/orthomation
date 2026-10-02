"""Compare exactly two post-optimization metric reports without selecting a branch."""

import argparse
import json
from pathlib import Path
import sys

from comparison_core import (
    ComparisonError,
    compare_reports,
    failure_report,
    load_metrics_json,
    sha256_file,
)


def _parser():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("reports", nargs=2, type=Path)
    parser.add_argument("--html", type=Path, help="New standalone HTML outside repository (or under ignored tmp/)")
    parser.add_argument("--demo", action="store_true", help="Label HTML as synthetic demonstration")
    return parser


def main(argv=None):
    args = _parser().parse_args(argv)
    try:
        input_hashes = [sha256_file(path) for path in args.reports]
        reports = [load_metrics_json(path) for path in args.reports]
        result = compare_reports(*reports, input_hashes=input_hashes)
        if args.html:
            from comparison_html import write_comparison_html
            write_comparison_html(result, args.html, args.reports, args.demo)
        exit_code = 0
    except ComparisonError as exc:
        result = failure_report(exc.code)
        exit_code = 1
    json.dump(result, sys.stdout, ensure_ascii=False, sort_keys=True)
    sys.stdout.write("\n")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
