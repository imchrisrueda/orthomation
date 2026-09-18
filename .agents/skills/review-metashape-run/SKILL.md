# Review Metashape run

Usar para revisar una ejecución o informe de Metashape sin alterar el proyecto.

Primero extrae objetivamente versión, rama/run_id, estado, configuración, cámaras, marcadores, calibración y parámetros antes/después, residuos, RMSE, reproyección, errores, warnings y artefactos generados. Después separa el juicio geomático: verifica CRS/h-H/geoide, roles GCP/CP, restricciones de cámara, comparabilidad de imágenes y parámetros, y limitaciones de inferencia. Dos CP sólo sustentan evidencia exploratoria.

Informe: `RUN_ID`, `OBJECTIVE_EXTRACTION`, `CONFIGURATION`, `CAMERAS_AND_MARKERS`, `METRICS`, `WARNINGS`, `COMPARABILITY`, `GEOMATIC_JUDGMENT`, `STATUS`, `BLOCKERS`, `NEXT_SAFE_ACTION`. El juicio o autorización corresponde a `geomatics_reviewer`; una extracción no implica aprobación.
