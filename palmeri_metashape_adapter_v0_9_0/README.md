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

Los lanzadores `.bat` establecen las variables de campaña y modo, y ejecutan `scripts/palmeri_pipeline.py` dentro de Metashape.

1. Ejecutar `launchers/2025_01_inventory.bat`. Revisa `inventory.csv`, el log y las advertencias; el inventario crea esos informes y carpetas de salida.
2. Ejecutar `launchers/2025_02_pilot.bat` sólo con entradas válidas. Crea un MASTER sin restricciones externas para el vuelo piloto configurado. No sobrescribe un MASTER existente.
3. Revisar el informe `*_image_quality.json` y las fotos señaladas. La advertencia de calidad no excluye fotos automáticamente.
4. Abrir el MASTER en Metashape y marcar manualmente los GCP y CP configurados. Objetivo: cinco proyecciones confirmadas adecuadas por punto; tres es el mínimo que requiere justificación humana.
5. Ejecutar `launchers/2025_03_validate_pilot.bat`. Aceptar sólo `PASS` o `PASS_WITH_MANUAL_CONFIRMATION` tras revisar todas las advertencias y completar la confirmación manual correspondiente.
6. Con el MASTER validado abierto en Metashape, ejecutar `scripts/prepare_branches.py` desde el ejecutor de scripts de la aplicación. Crea `GCP_ONLY` y `GCP_P1` y no es repetible sobre un documento que ya contiene esas ramas.
7. Seleccionar cada rama como chunk activo y ejecutar `scripts/validate_before_optimize.py`. Continuar sólo si el informe queda en `PASS`.
8. Con cada rama validada como chunk activo, ejecutar `scripts/optimize_branch.py`. El script exige un informe pre-optimización `PASS` reciente y aplica los mismos parámetros bloqueados a ambas ramas.
9. Revisar ambos informes de optimización. La extracción automatizada de métricas GCP/CP y el criterio de selección siguen pendientes; no se debe dar por elegida una rama ni generar productos finales. Los dos CP disponibles sólo sustentan una evaluación exploratoria.

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
- Creación de ramas, preflight y optimización: informes JSON junto al proyecto Metashape correspondiente.

No guardes fotos, proyectos `.psx`, informes generados, archivos temporales ni JobXML en Git. Los resultados se guardan fuera del repositorio mediante `generated_root`.

## Puertas de seguridad

- `overwrite_policy` es `forbid`; el adaptador rechaza sobrescrituras automáticas. Versiona o archiva salidas anteriores explícitamente.
- El MASTER empieza sin restricciones externas. La revisión de calidad y el marcado humano de GCP/CP son obligatorios antes de crear ramas.
- Los CP permanecen fuera del ajuste.
- No optimices sin preflight `PASS` reciente para la rama activa.
- No generes productos derivados antes de comparar ramas y registrar una selección humana.
- El ajuste utiliza alturas elipsoidales para cámaras y marcadores. La altura ortométrica EGM08IGN se aplica mediante una transformación explícita posterior, pendiente de validación independiente.

## Pruebas

Desde esta carpeta, ejecutar las pruebas puras con Python disponible en el sistema:

```powershell
python -m unittest discover -s tests -v
```

Las pruebas puras verifican el parser JobXML y lectura XMP de ejemplo; no ejecutan Metashape ni procesan fotografías. Los scripts `tests/metashape_smoke.py` y `tests/metashape_preflight_smoke.py` requieren Metashape y datos locales.

## Parámetros geomáticos resumidos

- Cámaras: EPSG:4326 con altura elipsoidal P1; marcadores: EPSG:25830 con altura elipsoidal JobXML; salida horizontal de trabajo: EPSG:25830.
- GCP: E1, E3, E4 y E6. Check Points: C2 y C5. Los Check Points no participan en el ajuste.
- `MORPHOLOGY_MAX`: resolución original, 40 000 key points, 10 000 tie points, Generic Preselection, Guided Matching y Adaptive Camera Model Fitting. Reference Preselection y `Exclude stationary tie points` quedan desactivados.
- En la comparación, `GCP_ONLY` usa sólo GCP como restricciones; `GCP_P1` añade las posiciones XYZ de cámara P1. Orientaciones de cámara desactivadas en ambas.
- La interpretación de precisión horizontal Trimble como X=Y continúa pendiente de confirmación estadística.

Para evidencia y estado global, consulta [`ESTADO_ACTUAL.md`](../ESTADO_ACTUAL.md), [`FACTS.md`](../FACTS.md) y [`TASKS.md`](../TASKS.md). Las decisiones completas y fuentes técnicas están registradas en `FACTS.md`.
