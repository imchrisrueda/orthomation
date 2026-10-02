# Palmeri Metashape Adapter v0.9.0

Adaptador activo para inventariar vuelos RGB, crear un MASTER y preparar una comparación controlada en Agisoft Metashape Professional 2.3.1. La definición científica y el estado global están en [`../FACTS.md`](../FACTS.md), [`../ESTADO_ACTUAL.md`](../ESTADO_ACTUAL.md) y [`../TASKS.md`](../TASKS.md).

## Estado operativo

- Los controles offline descritos abajo están implementados y aceptados técnicamente tras revisión QA y de controles geomáticos independientes; no amplían la autorización geomática vigente.
- Piloto 2025-04-29: la siguiente acción autorizada es preparar, de forma no destructiva, las ramas `GCP_ONLY_fixed_model_v1` y `GCP_P1_fixed_model_v1` desde el MASTER autorizado. Después debe revisarse el informe generado y solicitarse dictamen geomático antes de preflight, optimización, métricas o productos.
- Campaña 2026: la evidencia histórica del 19/09 registra que el candidato supera las reglas estructurales, pero queda `REVIEW_REQUIRED` por identidad/roles y metadatos CRS aún no aceptados; la copia local entonces resuelta por `default_jobxml` era la antigua. Su presencia y huella no se han revalidado hoy.
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

Cada entrada de ramas exige ahora una autorización explícita por fase en `optimization_experiments.fixed_model_v1.phase_authorizations`: `prepare_branches`, `preflight`, `optimization` y `metrics_export`. Sólo preparación conserva `APPROVED`, con referencia al dictamen histórico; las otras fases permanecen `REVIEW_REQUIRED`. La aprobación global no basta; un registro ausente, incompleto o sin evidencia para `APPROVED` bloquea la ejecución. La preparación verifica primero el manifiesto byte a byte y, después de crear ramas, indica detenerse a revisar el informe. Los estados técnicos no conceden permiso humano.

## Controles offline

Desde la raíz del repositorio, con Python 3.12 y sólo biblioteca estándar:

```powershell
python tools/check_repository.py
python palmeri_metashape_adapter_v0_9_0/scripts/validate_configuration.py
python tools/verify_package.py
```

El checker valida sintaxis AST sin importar Metashape, JSON estricto, TOML y perfiles, el subconjunto escalar `name`/`description` de las cuatro skills (no es un validador YAML universal), enlaces Markdown locales y anchors, configuración, integridad y la suite `test_*.py`. Excluye los smoke de Metashape. El mismo comando está configurado en CI para Windows con Python 3.12, plataforma objetivo confirmada por el usuario; su ejecución remota sigue pendiente hasta publicar y ejecutar.

Resultado local del 02/10/2026: checker PASS, 71 pruebas con una omitida por permisos Windows para symlinks y 41 fuentes verificadas byte a byte. Se probaron tipos JSON estrictos y números no representables sin crash de la CLI. Las dos revisiones independientes fueron estáticas; no se ejecutó Metashape ni se revalidaron datos reales. El descubrimiento de las skills está confirmado, pero la aplicación técnica de perfiles de agentes en el runtime sigue sin verificar.

El validador de configuración no abre imágenes, JobXML ni proyectos. Código `0` significa estructura válida, `1` error y `2` uso CLI incorrecto. Su JSON por stdout distingue estructura de operación: 2026 sigue `REVIEW_REQUIRED` y la plantilla es `DRAFT`/`NOT_EXECUTABLE`; ningún resultado concede aceptación geomática. Las rutas Windows se validan sintácticamente incluso en Linux, sin exigir que existan los discos. `expected_sha256` sigue siendo opcional para el parser de 2025, aunque el auditor de candidatos exige esa huella.

El manifiesto incluye sólo fuentes `.py`, `.json`, `.md`, `.txt` y `.bat`, excluyendo el propio manifiesto, datos de control, temporales, cachés y productos generados. Rechaza entradas duplicadas, traversal, rutas absolutas, links/junctions, fuentes omitidas y diferencias de bytes. `.gitattributes` fija LF para fuentes de texto y CRLF para `.bat`. Tras una edición autorizada del paquete, revisa el diff y regenera explícitamente:

```powershell
python tools/verify_package.py --write
python tools/verify_package.py
```

Regenerar registra los bytes actuales; no demuestra por sí mismo su autenticidad ni autoriza cambios científicos. No normalices JobXML ni informes de métricas para hacer coincidir hashes.

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

Para obtener HTML independiente, añade `--html <ruta_nueva_fuera_del_repo.html>`; también se permite la carpeta ignorada `tmp/` de la raíz. No se sobrescriben archivos. El HTML usa la misma comparación validada y sus huellas de entrada, muestra valores y deltas sin ranking, escapa texto y no usa JavaScript ni red. Un error no genera HTML. Añade `--demo` únicamente para identificar entradas sintéticas como demostración, sin resultados reales. La salida JSON por stdout y los códigos `0`/`1` del comparador se conservan; argparse usa `2` para errores de uso.

Desde este directorio:

```powershell
python -m unittest discover -s tests -v
```

La suite pura utiliza fixtures sintéticas, incluidos los controles XML temporales del parser; no necesita JobXML ignorados ni datos de campaña. Los smoke de `tests/` requieren Metashape 2.3.1 y las entradas locales autorizadas; no forman parte del checker offline.

La [preparación offline de contratos por vuelo y protocolo de evaluación](planning/README.md) dispone de borradores JSON estrictos y una CLI de validación. Es independiente de las configuraciones operativas y conserva todos los gates humanos.
