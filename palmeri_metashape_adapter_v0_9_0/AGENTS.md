# Palmeri Metashape Adapter v0.9.0

Estas instrucciones complementan el `AGENTS.md` raíz y se aplican sólo a este paquete activo.

## Arquitectura y operación

- Entradas: `campaigns/<id>.json`, `config/global.json`, JobXML local autorizado y rutas de imágenes. `scripts/palmeri_pipeline.py` coordina inventario y MASTER; los scripts de ramas se ejecutan desde Metashape con el proyecto correcto abierto.
- Núcleo: `scripts/orthomation_core.py`; optimización: `scripts/optimization_core.py`, `prepare_branches.py`, `validate_before_optimize.py`, `optimize_branch.py` y `export_postoptimization_metrics.py`.
- Lanzadores: `launchers/*.bat`. Pruebas puras: `tests/test_orthomation_core.py`; los smoke requieren Metashape 2.3.1 y datos locales.
- Metashape objetivo: Professional 2.3.1. No ejecutes los scripts que importan `Metashape` con el Python de sistema.

## Convenciones y seguridad

- Python: cambios pequeños, configuración versionada, validaciones explícitas e informes JSON/CSV accionables. Conserva rutas absolutas de imágenes tras promover un proyecto.
- El comportamiento es fail-closed y `overwrite_policy=forbid`: no sobrescribas MASTER, ramas, informes o derivados sin política aprobada.
- Los archivos generados se guardan bajo `generated_root`, fuera de Git. No añadas JobXML, imágenes, `.psx` ni resultados al repositorio.
- Respeta los gates: QA de imagen y marcado manual; preflight `PASS` de la rama; comparación y selección humana antes de productos. La autorización vigente de `fixed_model_v1` sólo permite preparar ramas y detenerse para revisión.

## Pruebas y Definition of Done

Desde este directorio ejecuta `python -m unittest discover -s tests -v` para pruebas puras. Declara los smoke de Metashape que no se hayan ejecutado y por qué. Un cambio técnico está terminado cuando cumple su especificación, conserva los invariantes raíz, pasa las pruebas aplicables, no produce archivos no deseados y documenta todo cambio de comportamiento o limitación.
