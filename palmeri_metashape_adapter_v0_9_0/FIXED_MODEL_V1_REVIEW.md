# Dictamen geomático condicionado — `fixed_model_v1`

## Estado

`APPROVED_WITH_CONDITIONS`. El dictamen geomático final autoriza únicamente preparar las ramas nuevas, una vez verificada la integridad completa del paquete. No autoriza todavía preflight, optimización, exportación, selección de rama ni productos.

El primer dictamen geomático fue `FAIL` y sus seis bloqueos se corrigieron. El segundo dictamen aceptó estáticamente el contrato y autorizó exclusivamente el smoke no procesante. Ese smoke terminó correctamente en Metashape Professional 2.3.1 build 22580; la salida completa se conserva en `tests/metashape_fixed_model_smoke_2026-09-17.txt`. El dictamen final autorizó cambiar únicamente `review_status` a `APPROVED` y ejecutar después sólo `prepare_branches.py` sobre el MASTER autorizado.

El experimento está limitado al piloto 2025-04-29. No autoriza otros vuelos ni la generación de nube, modelo, DSM/DTM, ortomosaico u otros productos.

No consta una ejecución satisfactoria de `prepare_branches.py`. La autorización no implica que las ramas nuevas o el informe de preparación ya existan.

## Contrato implementado

- MASTER requerido: huella persistida `49925af981c6a0076cb5f43490d8b4b344864ebe71a2d0407cb4ec3b2fe24d10` y huella API live Metashape 2.3.1 `e75f994cfff3a0a286ee7e3283b4ae2f202ce7869ee4e42c3b4caf0107831520`.
- La equivalencia exige simultáneamente 43 cámaras, 688 componentes, etiquetas idénticas, diferencias sólo en los índices de rotación `0,1,2,4,5,6,8,9,10`, igualdad exacta en traslaciones/fila homogénea y `max |delta| <= 1e-15`.
- Ambas representaciones deben producir `53c4790ff878b4b5cc2e132e87f4df5394beba4093bbf928ddfb8ba25b3cc0d1` al serializar únicamente para esta comparación a 12 cifras significativas. Esta canonicalización no sustituye las dos huellas exactas.
- JobXML requerido: SHA-256 `877c73e9a409d41c1262adf6921713d009db4a395d977550755b15d8f2b63d18`.
- `run_id`: `fixed_model_v1`.
- Ramas nuevas: `<MASTER>_GCP_ONLY_fixed_model_v1` y `<MASTER>_GCP_P1_fixed_model_v1`.
- Ajustables: `f`, `cx`, `cy`, `k1`, `k2`, `k3`, `p1`, `p2`.
- Fijos: `b1`, `b2`, `k4`; `fit_corrections=false`; `adaptive_fitting=false`; `tiepoint_covariance=true`.
- `p3` y `p4` se auditan como parámetros expuestos por `Calibration` pero no ajustables por la firma de `optimizeCameras` 2.3.1.
- Se exigen 43 cámaras, seis proyecciones confirmadas por marcador, C2/C5 OFF, rotaciones OFF y ausencia de derivados.

Las ramas adaptativas previas y sus JSON no se modifican. El nuevo informe de preparación registrará sus hashes y los estados `REJECTED_ADAPTIVE_FITTING` y `NOT_COMPARABLE_FOR_SELECTION`.

## Tolerancia aprobada

El `geomatic_agent` aprobó una tolerancia absoluta `1e-12`, en las unidades nativas de cada parámetro de calibración, para `b1`, `b2`, `k4`, `p3` y `p4`.

Justificación: al no solicitar su ajuste, estos valores deberían ser invariantes. El margen admite únicamente ruido de representación de doble precisión y detecta cualquier cambio sustantivo. El código valida además que las tolerancias sean completas, finitas, no negativas y exactamente iguales a los valores revisados.

La tolerancia y el contrato están aceptados. Toda ampliación del alcance de ejecución requiere un nuevo dictamen geomático.

## Huella dual del MASTER

El dictamen adicional aprobó el parche técnico tras dos aperturas independientes y de solo lectura. Metashape 2.3.1 re-ortonormaliza la submatriz de rotación al cargar: 258 de 688 componentes difieren, exclusivamente en rotación, con diferencia máxima `7.771561172376096e-16`. No se observó cambio de etiquetas, traslaciones ni fila homogénea.

El smoke integrado repitió esta comprobación con `Document.open(..., read_only=True)` y quedó registrado, sin sobrescribir evidencia anterior, en `tests/metashape_fixed_model_dual_fingerprint_smoke_2026-09-17.txt`.

La implementación completó además 22/22 pruebas unitarias puras. El smoke integrado terminó con `METASHAPE_FIXED_MODEL_SMOKE_OK`; ninguna de estas pruebas creó ramas, ejecutó preflight, optimizó o generó productos.

`prepare_branches.py` debe leer directamente el chunk activo guardado y comparar a la vez la representación persistida y la API live. No acepta una huella mediante una lista alternativa (`OR`) y falla ante cualquier incumplimiento. Las ramas, metadatos e informes conservan separadas las huellas persistida, live y común de comparación. Preflight y optimización exigen continuidad exacta de la huella live.

## Limitación verificable de la API

Metashape 2.3.1 permite configurar y serializar los booleanos de `OptimizeCameras`, pero no ofrece una propiedad documentada que devuelva después el conjunto efectivo de parámetros ajustados ni las correcciones adicionales. Los informes distinguen:

- conjunto solicitado y retenido por la tarea;
- serialización de la tarea;
- cambios observados en calibración antes/después;
- `effective_parameter_set.api_available=false`;
- `additional_corrections.posthoc_api_available=false`.

No se interpreta ausencia de variación como prueba de que un parámetro no fue efectivo, ni una variación como lista efectiva completa.

El smoke confirmó todas las propiedades de la tarea mediante lectura directa. `encodeJSON()` serializó únicamente `tiepoint_covariance=true` porque el resto coincide con los valores predeterminados documentados de la tarea; por ello la evidencia principal del contrato es el diccionario completo leído de las propiedades de `OptimizeCameras`, conservado en el log.

Fuentes: manual local `manuales/metashape-pro_2_3_en.pdf`, páginas PDF 116–119; [Python API 2.3.1](https://www.agisoft.com/pdf/metashape_python_api_2_3_1.pdf), `Chunk.optimizeCameras`, `Tasks.OptimizeCameras`, `Calibration`, `Marker`, `TiePoints` y `Camera.error`; script oficial de Agisoft `save_estimated_reference.py`.

## Secuencia y autorización vigente

1. Autorizado: abrir el MASTER 2025-04-29 y ejecutar `scripts/prepare_branches.py`.
2. Revisar `branch_setup_fixed_model_v1_v0_9_0.json` y sus hashes.
3. Bloqueado hasta nuevo dictamen: `scripts/validate_before_optimize.py`.
4. Bloqueado hasta nuevo dictamen: `scripts/optimize_branch.py`.
5. Bloqueado hasta nuevo dictamen: `scripts/export_postoptimization_metrics.py`.

Todos los informes usan nombres con `fixed_model_v1` y apertura exclusiva; un archivo existente provoca fallo en lugar de sobrescritura.
