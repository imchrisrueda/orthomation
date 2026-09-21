# Palmeri Metashape Adapter v0.9.0

Adaptador activo para inventariar vuelos RGB, crear un MASTER y preparar una comparación controlada en Agisoft Metashape Professional 2.3.1. La definición científica y el estado global están en [`../FACTS.md`](../FACTS.md), [`../ESTADO_ACTUAL.md`](../ESTADO_ACTUAL.md) y [`../TASKS.md`](../TASKS.md).

## Estado operativo

- Piloto 2025-04-29: la siguiente acción autorizada es preparar, de forma no destructiva, las ramas `GCP_ONLY_fixed_model_v1` y `GCP_P1_fixed_model_v1` desde el MASTER autorizado. Después debe revisarse el informe generado y solicitarse dictamen geomático antes de preflight, optimización, métricas o productos.
- Campaña 2026: el candidato supera las reglas estructurales, pero queda `REVIEW_REQUIRED` por identidad/roles y metadatos CRS aún no aceptados; la copia local que resuelve `default_jobxml` sigue siendo la antigua.
- No se generan nube, DSM/DTM ni ortomosaico hasta validar la solución geométrica, comparar ramas y registrar una selección humana.

## Preparación

1. Configura una ruta local de salida en `config/global.json` (`generated_root`).
2. Comprueba `campaigns/<id>.json`: estado, rutas, CRS, geoide, puntos y roles aprobados.
3. Coloca el JobXML aprobado bajo `control/jobxml/`; los `*.jxl` no se añaden a Git.
4. Confirma que Metashape Professional 2.3.1 está disponible para los lanzadores en `launchers/`.

Para registrar una campaña, usa [`NEW_CAMPAIGN.md`](NEW_CAMPAIGN.md).

## Flujo seguro

Los lanzadores ejecutan `scripts/palmeri_pipeline.py` dentro de Metashape. Revisa los informes de inventario y calidad; el marcado manual de GCP/CP es obligatorio. Los scripts `prepare_branches.py`, `validate_before_optimize.py` y `optimize_branch.py` se ejecutan desde Metashape con el proyecto y chunk correctos abiertos, nunca con el Python de sistema.

- `overwrite_policy=forbid`: no se sobrescriben proyectos, ramas ni informes.
- Los Check Points permanecen fuera del ajuste.
- El bundle adjustment usa alturas elipsoidales; la conversión EGM08IGN es una etapa posterior explícita y validada.
- La rama sólo puede optimizarse después de un preflight `PASS` y autorización geomática vigente.

## Pruebas

Audita un candidato local sin publicar coordenadas, alturas individuales, XML ni rutas absolutas:

```powershell
python scripts/validate_jobxml_candidate.py <candidato.jxl> campaigns/2026.json
```

La salida JSON por `stdout` usa `PASS_AUTOMATIC` (código 0), `FAIL` (1) o `REVIEW_REQUIRED` (2). Cada campaña debe declarar un `expected_sha256` completo: su ausencia, formato inválido o discrepancia producen `FAIL`. `PASS_AUTOMATIC` sólo es alcanzable cuando todas las aceptaciones semánticas y los campos `crs_acceptance` están explícitamente aprobados con `source=campaign_config`; no concede aceptación geomática y `campaign_unlock` siempre permanece en `false`. Las unidades 1-sigma de precisión se aceptan separadamente de las unidades de coordenadas. Para una comparación espacial exclusivamente diagnóstica se pueden añadir `--reference <referencia.jxl> --reference-campaign <campaña.json>`; no existe umbral, clasificación ni autoasignación.

Compara dos informes de métricas ya exportados, sin abrir Metashape:

```powershell
python scripts/compare_branch_metrics.py <metrics_GCP_ONLY.json> <metrics_GCP_P1.json>
```

El orden de entrada es indiferente. La salida `OBJECTIVE_COMPARISON_READY` sólo confirma que los informes son estructuralmente equivalentes y presenta valores y deltas `GCP_P1 - GCP_ONLY`; no selecciona una rama, no concede aceptación geomática y no autoriza productos. Con sólo C2 y C5, la evidencia sigue siendo exploratoria y requiere decisión humana.

Desde este directorio:

```powershell
python -m unittest discover -s tests -v
```

`tests/test_orthomation_core.py` y `tests/test_validate_jobxml_candidate.py` contienen pruebas puras. Los smoke de `tests/` requieren Metashape 2.3.1 y las entradas locales autorizadas; sus resultados se generan fuera de Git para cada ejecución.
