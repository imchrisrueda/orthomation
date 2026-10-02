"""Standalone HTML from the comparator's allowlisted output, without scripts or assets."""

from html import escape
import json
from pathlib import Path

from comparison_core import ComparisonError


def _text(value):
    return escape(json.dumps(value, ensure_ascii=False, sort_keys=True) if isinstance(value, (dict, list)) else str(value), quote=True)


def _leaves(value, prefix=()):
    if isinstance(value, dict):
        for key, item in value.items():
            yield from _leaves(item, (*prefix, str(key)))
    else:
        yield prefix, value


def _at(value, keys):
    for key in keys:
        value = value[key]
    return value


def _metric_rows(value, prefix=()):
    if isinstance(value, dict) and set(value) == {"GCP_ONLY", "GCP_P1", "delta_GCP_P1_minus_GCP_ONLY"}:
        for keys, left in _leaves(value["GCP_ONLY"]):
            yield (*prefix, *keys), left, _at(value["GCP_P1"], keys), _at(value["delta_GCP_P1_minus_GCP_ONLY"], keys)
    elif isinstance(value, dict):
        for key, child in value.items():
            yield from _metric_rows(child, (*prefix, str(key)))


def render_comparison(result, demo=False):
    if result.get("status") != "OBJECTIVE_COMPARISON_READY" or result.get("selection_performed") is not False or result.get("geomatic_acceptance") != "NOT_GRANTED" or result.get("products_authorized") is not False or result.get("human_decision_required") is not True:
        raise ComparisonError("html_requires_valid_comparison")
    title = "Comparativa objetiva de ramas" + (" — DEMO SINTÉTICA, sin resultados reales" if demo else "")
    rows = "".join(
        "<tr>" + "".join(f"<td>{_text(cell)}</td>" for cell in (" / ".join(keys), left, right, delta)) + "</tr>"
        for keys, left, right, delta in _metric_rows(result["metrics"])
    )
    provenance = "".join(f"<dt>{_text(key)}</dt><dd>{_text(value)}</dd>" for key, value in result["provenance"].items())
    limits = "".join(f"<li>{_text(value)}</li>" for value in result["limitations"])
    return f'''<!doctype html><html lang="es"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'">
<title>{escape(title)}</title><style>
body{{font-family:system-ui,sans-serif;max-width:1200px;margin:2rem auto;padding:0 1rem;color:#17263a;background:#f6f8fb}}
h1,h2{{color:#253e62}}.notice{{padding:1rem;background:#e7edf6;border-left:4px solid #506482}}
table{{border-collapse:collapse;width:100%;background:white}}th,td{{padding:.6rem;border-bottom:1px solid #d6dfea;text-align:left;vertical-align:top}}
th{{background:#dce5f1;position:sticky;top:0}}td:first-child{{max-width:480px}}dd{{overflow-wrap:anywhere;margin-bottom:.7rem}}dt{{font-weight:600}}.scroll{{overflow-x:auto}}
</style><body><h1>{escape(title)}</h1>
<p class="notice">Dos Check Points: evidencia exploratoria. Altura elipsoidal h; sin conversión a H.
Sin ranking ni selección. Decisión humana requerida; aceptación geomática NOT_GRANTED; productos autorizados: false.</p>
<h2>Métricas</h2><p>Delta = GCP_P1 − GCP_ONLY. El signo no expresa preferencia.</p>
<div class="scroll"><table><thead><tr><th>Métrica</th><th>GCP_ONLY</th><th>GCP_P1</th><th>Delta</th></tr></thead><tbody>{rows}</tbody></table></div>
<h2>Procedencia</h2><dl>{provenance}</dl><h2>Limitaciones</h2><ul>{limits}</ul></body></html>'''


def write_comparison_html(result, destination, inputs, demo=False):
    destination = Path(destination)
    if destination.suffix.lower() != ".html" or destination.exists() or destination.is_symlink():
        raise ComparisonError("html_destination_invalid_or_exists")
    resolved = destination.resolve()
    if resolved in {Path(p).resolve() for p in inputs}:
        raise ComparisonError("html_destination_is_input")
    repository = Path(__file__).resolve().parents[2]
    if resolved.is_relative_to(repository) and not resolved.is_relative_to(repository / "tmp"):
        raise ComparisonError("html_destination_inside_repository")
    # Render completely before opening a new file. Exclusive creation preserves no-overwrite.
    content = render_comparison(result, demo)
    try:
        with destination.open("x", encoding="utf-8", newline="\n") as stream:
            stream.write(content)
    except OSError as exc:
        raise ComparisonError("html_destination_unwritable") from exc
