# Estado actual de Orthomation

Fecha: 2026-09-17.

## Resultado alcanzado

Se ha creado `palmeri_metashape_adapter_v0_9_0` como nueva base, manteniendo intactos `palmeri_metashape_automation_v0_8_1` y `palmeri_metashape_v8_0_2` para trazabilidad.

La v0.9.0 ya no depende de CSV con alturas provisionales. Integra directamente el JobXML, usa altura elipsoidal, aplica precisiones individuales, valida XMP P1 y registra QA de imagen.

Para el piloto 2025-04-29 se implementó el experimento no destructivo `fixed_model_v1`. El modelo de optimización fija `adaptive_fitting=false`, mantiene `f, cx, cy, k1, k2, k3, p1, p2` ajustables, fija `b1, b2, k4`, desactiva correcciones y activa `tiepoint_covariance`. Las ramas adaptativas anteriores y sus JSON se conservan sin cambios y quedan excluidos de la selección del experimento nuevo.

El dictamen geomático vigente es `APPROVED_WITH_CONDITIONS`: autoriza sólo `prepare_branches.py` sobre el MASTER 2025-04-29 y obliga a detenerse tras generar y revisar `branch_setup_fixed_model_v1_v0_9_0.json`. No existe evidencia de que esa ejecución haya finalizado.

## Verificaciones ejecutadas

- Sintaxis Python de todos los scripts: correcta.
- JSON de configuración: correcto.
- Pruebas unitarias puras: 22/22 correctas para la implementación actual.
- Parser JobXML 2025: seis puntos, `NetworkFix`, EGM08IGN, año y precisiones correctos.
- XMP reales del piloto: 43/43 válidos, RTK fixed y altura elipsoidal coherente.
- Diferencia cámara-terreno elipsoidal observada: 14,558-14,960 m.
- JobXML denominado 2026: rechazado por ser idéntico al de 2025.
- Prueba directa con Metashape 2.3.1: carga correcta de ubicación, precisión XMP, `AnalyzeImages` y precisión individual de marcador.
- Contrato `OptimizeCameras` fijo, preflight por `run_id`, optimización fail-closed y exportador de métricas de sólo lectura implementados.
- Tolerancia absoluta de calibración `1e-12` aprobada para `b1`, `b2`, `k4`, `p3` y `p4`.
- Smoke no procesante: PASS en Metashape Professional 2.3.1 build 22580.
- Smoke del MASTER en modo `read_only`: PASS. Huella persistida `49925af981c6a0076cb5f43490d8b4b344864ebe71a2d0407cb4ec3b2fe24d10`, huella API-live `e75f994cfff3a0a286ee7e3283b4ae2f202ce7869ee4e42c3b4caf0107831520`, huella común a 12 cifras `53c4790ff878b4b5cc2e132e87f4df5394beba4093bbf928ddfb8ba25b3cc0d1` y diferencia máxima `7.771561172376096e-16` frente al límite `1e-15`.
- Manifiesto `SHA256SUMS.txt`: verificado sin fallos después de la implementación; debe regenerarse tras cualquier edición del paquete.

## Lo que todavía no se ha ejecutado

- No consta que `prepare_branches.py` haya terminado ni que exista `branch_setup_fixed_model_v1_v0_9_0.json` revisado.
- No se ha autorizado ni ejecutado el preflight `fixed_model_v1`.
- No se han optimizado las ramas `fixed_model_v1`.
- No se ha ejecutado el exportador de métricas sobre ramas optimizadas.
- No se han generado nube, DSM/DTM u ortomosaico.
- No se han procesado otros vuelos bajo esta autorización.
- No se ha implementado el adaptador Pix4D.

## Bloqueos

- Campaña 2026: el JobXML recibido en la raíz del repo supera la validación automática cuando se pasa explícitamente al parser (seis puntos; Trimble JobXML 5.72; observaciones de 2026; ETRS89 / UTM 30 North; EGM08IGN). La ruta predeterminada configurada, `palmeri_metashape_adapter_v0_9_0/control/jobxml/2026-GPS-ensayopalmeri-poveda.jxl`, todavía contiene el fichero anterior con SHA-256 de 2025, por lo que el flujo de campaña aún no acepta el nuevo fichero. La campaña sigue bloqueada hasta instalar la versión recibida en esa ruta local, obtener dictamen geomático y registrar su aceptación.
- Precisión horizontal Trimble: la asignación X=Y=Horizontal es provisional hasta confirmar su definición estadística.
- Experimento `fixed_model_v1`: preflight, optimización, exportación, selección de rama, productos y otros vuelos permanecen bloqueados hasta un nuevo dictamen geomático posterior a la revisión del informe de preparación.

El JobXML recibido se conserva localmente en la raíz del repo y está excluido de Git por contener datos de control. Su SHA-256 es `3b8a66c5475505b90c7be77dfb9a42537971af963f0e01d55c307fa64aa7cd5`. El fichero que aún está en la ruta configurada y el de 2025 tienen SHA-256 `877c73e9a409d41c1262adf6921713d009db4a395d977550755b15d8f2b63d18`.

## Punto seguro de reanudación

1. Abrir el MASTER autorizado 2025-04-29 en Metashape Professional 2.3.1 y seleccionarlo como chunk activo.
2. Ejecutar únicamente `palmeri_metashape_adapter_v0_9_0/scripts/prepare_branches.py`.
3. Confirmar que el script crea las ramas con sufijo `fixed_model_v1` sin alterar las ramas adaptativas previas.
4. Revisar `branch_setup_fixed_model_v1_v0_9_0.json`, sus hashes y todas las comprobaciones fail-closed.
5. Detenerse y solicitar un nuevo dictamen geomático antes de preflight.

En paralelo, la campaña 2026 conserva su bloqueo independiente. No debe ejecutarse preflight, optimización, exportación, generación de productos, procesamiento masivo 2025 ni ningún vuelo 2026 con la autorización vigente.
