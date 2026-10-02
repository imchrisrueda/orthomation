---
name: review-metashape-run
description: Revisar una ejecución o informe de Metashape en Orthomation, extraer evidencia y emitir un dictamen técnico sin alterar proyectos ni conceder aprobación humana.
---

# Review Metashape run

Resuelve las rutas del paquete activo desde la raíz del repositorio, incluso si la sesión se inició en una subcarpeta.

Usar para revisar una ejecución o informe de Metashape sin alterar el proyecto.

Primero extrae objetivamente versión, rama/run_id, estado, configuración, cámaras, marcadores, calibración y parámetros antes/después, residuos, RMSE, reproyección, errores, warnings y artefactos generados. Después separa el juicio geomático: verifica CRS/h-H/geoide, roles GCP/CP, restricciones de cámara, comparabilidad de imágenes y parámetros, y limitaciones de inferencia. Dos CP sólo sustentan evidencia exploratoria.

Informe: `RUN_ID`, `OBJECTIVE_EXTRACTION`, `CONFIGURATION`, `CAMERAS_AND_MARKERS`, `METRICS`, `WARNINGS`, `COMPARABILITY`, `GEOMATIC_JUDGMENT`, `STATUS`, `BLOCKERS`, `NEXT_SAFE_ACTION`. Encarga el dictamen técnico independiente a `geomatics_reviewer`; su resultado automatizado nunca concede aprobación científica ni supera un gate humano. Si se requiere autorización geomática o selección de solución, remite la evidencia a la persona responsable y conserva el bloqueo hasta registrar su decisión.
