# Validate JobXML

Usar antes de aceptar un JobXML o desbloquear una campaña. Localiza el fichero realmente resuelto por campaña/vuelo/override; no copies ni publiques su contenido.

1. Registra campaña, año esperado, ruta, nombre y hash.
2. Extrae y compara CRS, datum, geoide, época/unidades y método GNSS con la configuración aprobada.
3. Comprueba `WGS84/Height` (`h`) y `Grid/Elevation` (`H`) sin mezclarlos; registra explícitamente el tratamiento del geoide.
4. Comprueba puntos completos, identificadores, roles GCP/CP, `NetworkFix`, precisiones individuales, avisos y consistencia con la campaña.
5. Ejecuta el validador existente si corresponde y conserva el informe fuera de Git según la configuración.
6. Separa validación automática de aceptación geomática. Cualquier discrepancia de CRS, geoide, año, método, punto, rol, precisión, warning o hash esperado es `FAIL` o `REVIEW_REQUIRED`.

Informe: `STATUS`, `CAMPAIGN`, `SOURCE_HASH`, `CRS_DATUM_GEOID`, `GNSS_METHOD`, `POINTS_AND_ROLES`, `PRECISIONS`, `WARNINGS`, `CONSISTENCY`, `EVIDENCE`, `NEXT_SAFE_ACTION`. No cambies criterios existentes sin dictamen geomático.
