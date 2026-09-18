# Tareas del proyecto Orthomation

Fecha de corte: 2026-09-18.

## Actualización documental 2026-09-18

- [x] Consolidar instrucciones de trabajo en `AGENTS.md`, perfiles vigentes en `.codex/agents/` y procedimientos en `.agents/skills/`.
- [x] Retirar del árbol de trabajo los paquetes históricos v0.8.1 y v8.0.2; su trazabilidad permanece en Git.
- [x] Actualizar documentación de estado e índice README, y verificar el manifiesto SHA-256 del paquete activo.
- [ ] Reanudar sólo desde el punto seguro descrito en `ESTADO_ACTUAL.md`; los gates geomáticos y de campaña siguen vigentes.

## Completado

- [x] Revisar las conversaciones previas, manual Metashape 2.3 y manual Pix4Dmapper 4.1.
- [x] Identificar la mezcla entre altura ortométrica y elipsoidal del paquete antiguo.
- [x] Confirmar EGM08IGN y `h/H` en el JobXML 2025.
- [x] Verificar los 43 XMP P1 reales del piloto 2025.
- [x] Confirmar mediante documentación DJI que la foto registra la posición compensada de la pupila de salida.
- [x] Crear adaptador Metashape v0.9.0 sin modificar las versiones previas.
- [x] Integrar JobXML como fuente de coordenadas, alturas, roles, precisiones y QA.
- [x] Añadir selección JobXML por campaña, vuelo o variable `PALMERI_JOBXML`.
- [x] Añadir modo de vuelo individual.
- [x] Añadir bloqueo por año, geoide, CRS, método, warning y precisión.
- [x] Añadir validación XMP RTK P1 y coherencia aproximada cámara-terreno.
- [x] Añadir QA de imagen sin exclusión automática.
- [x] Definir `MORPHOLOGY_MAX` y corregir stationary points/configuración ignorada.
- [x] Añadir puerta de marcado y ramas `GCP_ONLY/GCP_P1` no repetibles.
- [x] Añadir huellas de transformación para detectar cambios antes de optimizar.
- [x] Añadir pruebas unitarias del parser JobXML, año y XMP.
- [x] Bloquear campaña 2026 mientras el JobXML está pendiente de verificación.
- [x] Implementar `fixed_model_v1` con modelo de calibración fijo, `run_id`, preflight y optimización fail-closed.
- [x] Implementar exportación objetiva y de sólo lectura de métricas posoptimización.
- [x] Obtener dictamen geomático sobre contrato, tolerancia `1e-12` y equivalencia dual de huella del MASTER.
- [x] Ejecutar 22 pruebas unitarias y smoke de sólo lectura en Metashape 2.3.1.

## Siguiente validación inmediata

- [x] Recibir JobXML 2026 distinto del de 2025 y pasar las reglas automáticas del parser (seis puntos; año, CRS y geoide conformes).
- [ ] Obtener dictamen geomático independiente para el JobXML 2026 y, si se acepta, sustituir la copia antigua local de `control/jobxml/` (mantener el JobXML ignorado por Git).
- [ ] Ejecutar únicamente `prepare_branches.py` sobre el MASTER 2025-04-29 autorizado.
- [ ] Verificar la creación no destructiva de `GCP_ONLY_fixed_model_v1` y `GCP_P1_fixed_model_v1`.
- [ ] Revisar `branch_setup_fixed_model_v1_v0_9_0.json` y someterlo a un nuevo dictamen geomático.
- [x] Fijar y automatizar el conjunto exacto de parámetros de Optimize Cameras tras comprobar la API 2.3.1.
- [ ] Mantener bloqueados preflight, optimización, exportación, productos y otros vuelos hasta ese dictamen.

## Desarrollo Metashape pendiente

- [x] Añadir prueba de integración ejecutada por Metashape 2.3 sobre una imagen P1 real.
- [x] Añadir `optimize_branch.py` con parámetros bloqueados e informe antes/después.
- [x] Añadir extracción objetiva de RMSE, sesgos, reproyección y calibración.
- [ ] Ejecutar preflight de ambas ramas sólo tras autorización geomática expresa.
- [ ] Ejecutar las dos optimizaciones y exportar métricas sólo tras autorización geomática expresa.
- [ ] Definir el criterio de selección entre `GCP_ONLY` y `GCP_P1`, reconociendo la limitación de dos CP.
- [ ] Implementar nube, DSM/DTM y ortomosaico solamente después de elegir la solución geométrica.
- [ ] Implementar conversión vertical final EGM08IGN con validación independiente.
- [ ] Añadir perfiles de producto para clasificación y para reconstrucción 3D.
- [x] Crear manifiesto SHA-256 verificable para v0.9.0.
- [ ] Procesar campañas restantes solo después de aprobar el piloto.

## Adaptador Pix4D pendiente

- [ ] Confirmar instalación, licencia y posibilidades de automatización de Pix4Dmapper 4.1.
- [ ] Diseñar esquema común de campaña sin reutilizar llamadas Metashape.
- [ ] Mapear JobXML/XMP, GCP/CP y referencia vertical a Pix4D.
- [ ] Reproducir el mismo conjunto de imágenes y roles.
- [ ] Extraer métricas y productos comparables con Metashape.

## Investigación pendiente

- [ ] Confirmar en documentación Trimble si `Precision/Horizontal` es sigma por componente, precisión radial o estadístico a otro nivel de confianza.
- [ ] Documentar solapes reales de todos los vuelos y contrastarlos con los mínimos recomendados para agricultura.
- [ ] Definir cómo comunicar incertidumbre con solo dos Check Points.
