# Palmeri Metashape Adapter v0.9.0

Adaptador para inventariar vuelos y preparar proyectos MASTER RGB en Agisoft Metashape Professional 2.3.x. El flujo posterior permite revisar el marcado terrestre, crear dos ramas de comparación y optimizarlas con parámetros controlados. No genera productos finales en esta versión del flujo.

## Estado y alcance

- **2025:** listo para repetir el piloto del 29/04/2025; ese reprocesamiento todavía no se ha ejecutado con v0.9.0.
- **2026:** bloqueado para revisión geomática. El candidato JobXML recibido pasa las reglas automáticas si se proporciona explícitamente, pero `campaigns/2026.json` apunta por defecto a una copia anterior de 2025 bajo `control/jobxml/`. No habilitar la campaña hasta aceptar el JobXML y actualizar la copia local.
- **Productos:** no generar nube, DSM/DTM ni ortomosaico hasta validar y comparar las dos ramas y aprobar una solución.

## Requisitos

- Windows y Agisoft Metashape Professional 2.3.x. Los scripts de procesamiento importan el módulo `Metashape` y se ejecutan dentro de la aplicación.
- Imágenes originales del vuelo en una carpeta local. La selección configurada procesa JPG/JPEG; la presencia conjunta de JPG y DNG provoca una advertencia bloqueante.
- JobXML de control local y aprobado para la campaña. Los archivos `*.jxl` están excluidos de Git; deben recibirse por un canal de datos autorizado y colocarse bajo `control/jobxml/`.
- Rutas locales válidas en `campaigns/<id>.json` y una carpeta de salida con espacio suficiente en `config/global.json` (`generated_root`). Las rutas actuales son específicas de la estación de trabajo y deben ajustarse antes de ejecutar en otro equipo.

## Preparar una estación de trabajo

1. Clonar o copiar el repositorio y conservar la estructura del paquete.
2. Editar `config/global.json`: ajustar `generated_root` a una carpeta local disponible. No cambies los parámetros geomáticos aprobados sin dictamen de `geomatic_agent`.
3. Editar `campaigns/<id>.json`: comprobar el año, estado, `default_jobxml`, CRS, geoide, puntos/roles y rutas de imágenes.
4. Colocar el JobXML aprobado en `control/jobxml/` y confirmar que el nombre y la ruta coinciden con la campaña. El JobXML no se añade a Git.
5. Comprobar que Metashape está en una de las rutas que buscan los lanzadores de `launchers/`. Si no, ajustar `METASHAPE_EXE` en el lanzador correspondiente.

Para registrar otra campaña o asignar un JobXML a un vuelo concreto, sigue [`NEW_CAMPAIGN.md`](NEW_CAMPAIGN.md).

## Flujo de trabajo 2025

> **Puerta vigente:** `fixed_model_v1` está `APPROVED_WITH_CONDITIONS`. Sólo está autorizada la preparación no destructiva de ramas desde el MASTER 2025-04-29. Preflight, optimización, exportación y productos continúan bloqueados. Consulta [`FIXED_MODEL_V1_REVIEW.md`](FIXED_MODEL_V1_REVIEW.md).

Los lanzadores `.bat` establecen las variables de campaña y modo, y ejecutan `scripts/palmeri_pipeline.py` dentro de Metashape.

1. Ejecutar `launchers/2025_01_inventory.bat`. Revisa `inventory.csv`, el log y las advertencias; el inventario crea esos informes y carpetas de salida.
2. Ejecutar `launchers/2025_02_pilot.bat` sólo con entradas válidas. Crea un MASTER sin restricciones externas para el vuelo piloto configurado. No sobrescribe un MASTER existente.
3. Revisar el informe `*_image_quality.json` y las fotos señaladas. La advertencia de calidad no excluye fotos automáticamente.
4. Abrir el MASTER en Metashape y marcar manualmente los GCP y CP configurados. Objetivo: cinco proyecciones confirmadas adecuadas por punto; tres es el mínimo que requiere justificación humana.
5. Ejecutar `launchers/2025_03_validate_pilot.bat`. Aceptar sólo `PASS` o `PASS_WITH_MANUAL_CONFIRMATION` tras revisar todas las advertencias y completar la confirmación manual correspondiente.
6. Tras la aprobación geomática de `fixed_model_v1`, abrir el MASTER y ejecutar `scripts/prepare_branches.py`. Crea ramas nuevas con `run_id` sin modificar `GCP_ONLY`, `GCP_P1` ni sus JSON anteriores.
7. **Detenerse.** Revisar `branch_setup_fixed_model_v1_v0_9_0.json` y solicitar un nuevo dictamen geomático. No consta todavía una preparación satisfactoria.
8. **Bloqueado:** seleccionar cada rama `*_fixed_model_v1` y ejecutar `scripts/validate_before_optimize.py`. Cuando se autorice, sólo podrá continuar si el informe específico de `run_id` queda en `PASS`.
9. **Bloqueado:** ejecutar `scripts/optimize_branch.py`. El código sólo guarda el estado `OPTIMIZED_FIXED_MODEL` si pasan todas las comprobaciones posteriores; ante fallo recarga el proyecto guardado para descartar la geometría calculada.
10. **Bloqueado:** ejecutar `scripts/export_postoptimization_metrics.py`. El exportador es de sólo lectura y no elige rama. Los dos CP disponibles sólo sustentan una evaluación exploratoria.

Los scripts que actúan sobre un proyecto abierto (`prepare_branches.py`, `validate_before_optimize.py` y `optimize_branch.py`) se ejecutan desde el ejecutor de scripts de Metashape, con el proyecto correcto abierto y el MASTER o la rama pertinente como chunk activo. No los ejecutes con Python de sistema.

`launchers/2025_04_remaining.bat` procesa los vuelos restantes y sólo debe usarse después de aceptar el piloto. `launchers/2025_05_validate_all.bat` valida el marcado para todos los MASTER disponibles; no reemplaza la validación de ramas previa a optimizar.

`launchers/run_campaign.bat` ofrece inventario, piloto, validación del piloto, vuelos restantes, validación completa y vuelo individual. El modo individual pide fecha y permite un override de JobXML. La acción del lanzador no omite las puertas manuales del flujo.

## Entradas, rutas y salidas

- Definición de campaña: `campaigns/<id>.json`; configuración compartida: `config/global.json`.
- Control terrestre: JobXML indicado por `PALMERI_JOBXML`, luego por el campo `jobxml` del vuelo y finalmente por `default_jobxml` de la campaña.
- Fotos: `input_dir` de cada vuelo. Revisa que la carpeta corresponda al vuelo y contenga el conjunto autorizado antes de procesar.
- Salida base: `<generated_root>/<campaign_id>/`.
- Inventario y resumen: `<generated_root>/<campaign_id>/inventory.csv`, `phase2_projects.csv` y `logs/`.
- MASTER: `projects/metashape/<fecha>/RGB_P1/<fecha>_RGB_P1_<preset>_MASTER.psx`.
- Calidad de imagen: informe `*_image_quality.json` junto al proyecto MASTER.
- Validación de marcado: `<generated_root>/<campaign_id>/validation_marking.json`.
- Creación de ramas, preflight, optimización y métricas: informes JSON con `run_id` junto al proyecto Metashape correspondiente.

No guardes fotos, proyectos `.psx`, informes generados, archivos temporales ni JobXML en Git. Los resultados se guardan fuera del repositorio mediante `generated_root`.

## Puertas de seguridad

- `overwrite_policy` es `forbid`; el adaptador rechaza sobrescrituras automáticas. Versiona o archiva salidas anteriores explícitamente.
- El MASTER empieza sin restricciones externas. La revisión de calidad y el marcado humano de GCP/CP son obligatorios antes de crear ramas.
- Los CP permanecen fuera del ajuste.
- No optimices sin preflight `PASS` reciente para la rama activa.
- `review_status=APPROVED` acredita el contrato revisado; la autorización operativa vigente sigue limitada a `prepare_branches.py` hasta revisar su informe.
- No generes productos derivados antes de comparar ramas y registrar una selección humana.
- El ajuste utiliza alturas elipsoidales para cámaras y marcadores. La altura ortométrica EGM08IGN se aplica mediante una transformación explícita posterior, pendiente de validación independiente.

## Pruebas

Desde esta carpeta, ejecutar las pruebas puras con Python disponible en el sistema:

```powershell
python -m unittest discover -s tests -v
```

Las pruebas puras verifican el parser JobXML, la lectura XMP de ejemplo y el contrato `fixed_model_v1`; no ejecutan Metashape ni procesan fotografías. La implementación actual registra 22/22 pruebas correctas. Los scripts `tests/metashape_smoke.py` y `tests/metashape_preflight_smoke.py` requieren Metashape y datos locales.

Las pruebas unitarias incluyen la huella de transformaciones con matrices planas y anidadas, además de verificar que el resultado no depende del orden de las cámaras.

El smoke `tests/metashape_fixed_model_smoke.py` se ejecutó en Metashape Professional 2.3.1 build 22580. Su comprobación integrada del MASTER lo abre con `read_only=True`, verifica simultáneamente la huella persistida exacta, la huella API-live exacta y el contrato de equivalencia aprobado, y no guarda el proyecto ni ejecuta preparación, preflight u optimización. Las salidas conservadas son `tests/metashape_fixed_model_smoke_2026-09-17.txt` y `tests/metashape_fixed_model_dual_fingerprint_smoke_2026-09-17.txt`.

## Solución de problemas

Si aparece `cannot import name 'transform_fingerprint' from 'orthomation_core'`, verifica que `scripts/orthomation_core.py`, `scripts/prepare_branches.py`, `scripts/validate_before_optimize.py` y `scripts/optimize_branch.py` sean de la misma versión actualizada. La huella ahora se define en el módulo compartido, y esos scripts recargan el módulo al iniciar para evitar reutilizar una copia anterior en la sesión de Metashape. Ese error de importación ocurre antes de entrar en `main()`; tras actualizar los archivos, vuelve a ejecutar el script con el MASTER validado activo. Si el mensaje persiste, cierra cualquier sesión de Metashape que esté ejecutando una copia antigua del paquete y abre el paquete actualizado.

Si la huella persistida es `49925af…` pero Metashape muestra `e75f994c…`, no regeneres el MASTER. Es la pareja exacta revisada para Metashape 2.3.1. `prepare_branches.py` comprobará ambas, junto con etiquetas, 688 componentes, posiciones permitidas, delta máximo y hash común; cualquier otra combinación falla de forma cerrada.

## Parámetros geomáticos resumidos

- Cámaras: EPSG:4326 con altura elipsoidal P1; marcadores: EPSG:25830 con altura elipsoidal JobXML; salida horizontal de trabajo: EPSG:25830.
- GCP: E1, E3, E4 y E6. Check Points: C2 y C5. Los Check Points no participan en el ajuste.
- `MORPHOLOGY_MAX`: resolución original, 40 000 key points, 10 000 tie points, Generic Preselection, Guided Matching y Adaptive Camera Model Fitting. Reference Preselection y `Exclude stationary tie points` quedan desactivados.
- En la comparación, `GCP_ONLY` usa sólo GCP como restricciones; `GCP_P1` añade las posiciones XYZ de cámara P1. Orientaciones de cámara desactivadas en ambas.
- La interpretación de precisión horizontal Trimble como X=Y continúa pendiente de confirmación estadística.

Para evidencia y estado global, consulta [`ESTADO_ACTUAL.md`](../ESTADO_ACTUAL.md), [`FACTS.md`](../FACTS.md) y [`TASKS.md`](../TASKS.md). Las decisiones completas y fuentes técnicas están registradas en `FACTS.md`.
