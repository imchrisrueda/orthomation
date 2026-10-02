---
name: validate-jobxml
description: Auditar un candidato JobXML frente a las reglas de campaña de Orthomation, con informe redactado y separación entre comprobación automática y aceptación geomática humana.
---

# Validate JobXML

Resuelve las rutas del paquete activo desde la raíz del repositorio, incluso si la sesión se inició en una subcarpeta.

Usar antes de aceptar un JobXML o desbloquear una campaña. Localiza el fichero realmente resuelto por campaña/vuelo/override; no copies ni publiques su contenido.

1. Registra campaña, año esperado, ruta, nombre y hash.
2. Extrae y compara CRS, datum, geoide, época/unidades y método GNSS con la configuración aprobada.
3. Comprueba `WGS84/Height` (`h`) y `Grid/Elevation` (`H`) sin mezclarlos; registra explícitamente el tratamiento del geoide.
4. Comprueba puntos completos, identificadores, roles GCP/CP, `NetworkFix`, precisiones individuales, avisos y consistencia con la campaña.
5. Ejecuta el auditor existente `palmeri_metashape_adapter_v0_9_0/scripts/validate_jobxml_candidate.py` si corresponde. Desde la raíz del repositorio, su CLI es:

   ```powershell
   python palmeri_metashape_adapter_v0_9_0/scripts/validate_jobxml_candidate.py "RUTA_CANDIDATO" "RUTA_CONFIG_CAMPAÑA"
   ```

   Ambos argumentos posicionales son obligatorios. Para comparar con una referencia, añade conjuntamente `--reference "RUTA_JOBXML_REFERENCIA" --reference-campaign "RUTA_CONFIG_REFERENCIA"`. Devuelve JSON redactado por stdout: conserva el informe fuera de Git según la configuración si necesitas guardarlo; no admite `--output`. Los códigos de salida son `0` para `PASS_AUTOMATIC`, `1` para `FAIL` y `2` para `REVIEW_REQUIRED` (argparse también usa `2` para errores de uso). El auditor no concede aceptación geomática ni desbloquea campañas: `geomatic_acceptance` permanece `NOT_GRANTED` y `campaign_unlock` permanece `false`.
6. Separa validación automática de aceptación geomática. Cualquier discrepancia de CRS, geoide, año, método, punto, rol, precisión, warning o hash esperado es `FAIL` o `REVIEW_REQUIRED`.

Informe: `STATUS`, `CAMPAIGN`, `SOURCE_HASH`, `CRS_DATUM_GEOID`, `GNSS_METHOD`, `POINTS_AND_ROLES`, `PRECISIONS`, `WARNINGS`, `CONSISTENCY`, `EVIDENCE`, `NEXT_SAFE_ACTION`. No cambies criterios existentes sin dictamen geomático.
