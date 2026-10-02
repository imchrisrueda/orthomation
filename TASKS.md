# Tareas del proyecto Orthomation

Revisión documental: 2026-10-02. Corte de evidencia científica: 2026-09-19; no se han repetido ejecuciones Metashape ni auditorías de datos reales.

Ámbito: `main` y la feature conservan los mismos incrementos publicados `a2f9497` y `ed7a73d`, sobre la base `40ca7af`, y la configuración CI Windows. Consulta `git log -1 --oneline` y `git branch -vv` para las referencias actuales. El CI de `ed7a73d` en ambas ramas está comprobado como PASS, con 100 pruebas sin omisiones y 50 fuentes; véase [FACTS §16](FACTS.md#16-esquema-común-de-campaña-y-comprobación-ci-2026-10-02).

## Integración y controles pendientes

- [x] Revisar e integrar localmente en `main` los commits de la feature con auditor, comparador, controles offline y pruebas mediante fast-forward hasta `42b9666`.
- [x] Revisar y versionar agentes, skills y documentación en `42b9666`, con cierre documental posterior de la integración.
- [x] Sincronizar `main` y `feature/validacion-jobxml-y-comparativa-ramas` para conservar los mismos desarrollos y documentación.
- [x] Aceptar técnicamente tras revisión independiente los gates por fase implementados y probados offline; sólo preparación mantiene autorización histórica, las otras fases siguen bloqueadas.
- [ ] Definir mediante revisión humana criterios por etapa para selección geométrica y evaluación posterior de productos, resolviendo la cuestión abierta de FACTS §9 sin saltar gates.
- [ ] Definir y revisar contratos de optimización por vuelo antes de generalizar las huellas y conteos fijos del piloto.
- [ ] Diseñar e implementar flujos multiespectrales y térmicos según sensores y requisitos aprobados; el pipeline vigente sólo procesa RGB P1.

## Secuencia prevista y dependencias

1. Con el CI de la base publicado comprobado, completar las revisiones humanas de los controles científicos pendientes y verificar CI después de cada publicación nueva.
2. Reanudar sólo la preparación autorizada, revisar su informe y obtener decisiones humanas antes de cada fase posterior.
3. Tras autorización, ejecutar preflight, optimizaciones y exportación; comprobar el comparador con métricas reales y documentar la selección humana.
4. Tras selección y especificación aprobadas, implementar y validar productos y conversión vertical; ampliar vuelos y sensores con sus contratos y abordar Pix4D después. La campaña 2026 conserva su bloqueo independiente.

## Preparación de contratos y protocolo 2026-10-02 (hito técnico aceptado)

- [x] Implementar plantillas DRAFT de contrato por vuelo y protocolo de evaluación, separadas de las configuraciones operativas.
- [x] Implementar CLI offline de validación estricta y diagnóstico redactado de campos pendientes, sin abrir evidencia referenciada ni autorizar ejecución.
- [x] Integrar los borradores en el checker y probar límites de autorización, tipos, metadatos, redacción y ausencia de escritura/bytecode: 17 pruebas nuevas; checker PASS con 88 pruebas, una omitida; manifiesto de 47 fuentes correcto.
- [x] Obtener PASS técnico estático de QA y revisión geomática independientes, corregir sus hallazgos y aceptar exclusivamente el desarrollo offline.
- [ ] Completar contratos reales con evidencia y revisión geomática humana; el runtime conserva el contrato específico del piloto y no consume estos borradores.
- [ ] Aceptar mediante revisión humana los criterios por etapa y la comunicación de incertidumbre; el protocolo es una propuesta y FACTS §9 permanece abierta.

Guía: [preparación offline](palmeri_metashape_adapter_v0_9_0/planning/README.md). Los pendientes de criterios y contratos de la sección de integración no se consideran completados por esta implementación. No se han ejecutado Metashape ni auditorías de datos reales; el incremento se versionó posteriormente en `a2f9497`, con publicación tratada en el hito siguiente.

## Esquema común y comprobación CI 2026-10-02 (hito técnico aceptado)

- [x] Comprobar CI Windows de `40ca7af` en `main` y feature: ambas ejecuciones completadas con éxito y evidencia enlazada en FACTS §16.
- [x] Preparar esquema común documental `common-campaign-1` para RGB P1, con validación de vuelos, referencias a contratos y evidencia declarada por motor; sin importadores ni equivalencia científica.
- [x] Integrar la tercera plantilla en CLI/checker, añadir 12 pruebas sintéticas y obtener PASS técnico estático de QA y revisión geomática independientes. Checker local: 100 pruebas, una omitida; manifiesto de 50 fuentes correcto.
- [x] Publicar los dos incrementos revisados y documentados en ambas ramas mediante fast-forward: `a2f9497` y `ed7a73d`; CI de `ed7a73d` PASS en ambas, 100 pruebas sin omisiones y 50 fuentes verificadas.
- [ ] Diseñar contratos y mapeos operativos Pix4D con evidencia primaria; la plantilla común no implementa ni valida esas capacidades.

## Desarrollos offline 2026-10-02 (hito técnico aceptado)

- [x] Implementar gates por fase y verificación de integridad previa a preparación, conservando los contratos científicos.
- [x] Implementar validación offline de configuración, manifiesto byte a byte con regeneración explícita y HTML de comparación validada sin ranking.
- [x] Implementar checker común local/CI y aislar las pruebas del parser con controles sintéticos temporales.
- [x] Ejecutar checker local: 71 pruebas puras, una omitida por permisos de symlink en Windows, configuración e integridad de 41 fuentes correctas; tipos estrictos y entero extremo cubiertos.
- [x] Obtener PASS técnico estático de QA y controles geomáticos independientes y aceptar el hito sin ampliar autorizaciones científicas.
- [x] Ajustar el alcance de CI a Windows, plataforma objetivo confirmada por el usuario; conservar el comando offline y sus permisos.
- [x] Comprobar el resultado de CI Windows de la base publicada `40ca7af`: PASS en ambas ramas; las nuevas publicaciones se verifican por commit en el hito siguiente.

## Revisión de agentes y skills 2026-10-02

- [x] Corregir metadatos YAML de las cuatro skills y precisar rutas, CLI JobXML, gates humanos, sólo lectura de `verifier` y fallback de delegación.
- [x] Validar cinco TOML, los cuatro frontmatter mediante comprobación básica y `git diff --check`; obtener revisión independiente `verifier: PASS`.
- El descubrimiento de las cuatro skills está confirmado en el catálogo de la sesión. Limitaciones: `quick_validate.py` no pudo ejecutarse por ausencia de PyYAML y la aplicación técnica de perfiles de agentes en el runtime no está verificada. Los gates científicos conservan su alcance.

## Actualización documental 2026-09-18

- [x] Consolidar instrucciones de trabajo en `AGENTS.md`, perfiles vigentes en `.codex/agents/` y procedimientos en `.agents/skills/`.
- [x] Retirar del árbol de trabajo los paquetes históricos v0.8.1 y v8.0.2; su trazabilidad permanece en Git.
- [x] Actualizar documentación de estado e índice README, y verificar el manifiesto SHA-256 del paquete activo.
- [ ] Reanudar sólo desde el punto seguro descrito en `ESTADO_ACTUAL.md`; los gates geomáticos y de campaña siguen vigentes.

## Completado (evidencia histórica)

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
- [x] Implementar auditor redactado y de sólo lectura para candidatos JobXML, con huella esperada, detección de IDs adicionales y comparación diagnóstica sin autoasignación.
- [x] Confirmar en documentación Trimble que `Precision/Horizontal` y `Vertical` están expresadas en metros y son estimaciones 1-sigma.
- [x] Implementar y revisar un comparador offline fail-closed para métricas `GCP_ONLY`/`GCP_P1`, sin ranking, selección automática ni autorización de productos.
- [x] Ejecutar 52 pruebas puras, incluidos casos adversariales de JobXML y comparación de métricas, y verificar el manifiesto del paquete.

## Siguiente validación inmediata

- [x] Recibir JobXML 2026 distinto del de 2025 y pasar las reglas automáticas del parser (seis puntos; año, CRS y geoide conformes).
- [ ] Resolver mediante dictamen geomático independiente la identidad y los roles del JobXML 2026; la permutación por proximidad es sólo inferencia diagnóstica. Si se acepta, sustituir la copia antigua local de `control/jobxml/` (mantener el JobXML ignorado por Git).
- [ ] Ejecutar únicamente `prepare_branches.py` sobre el MASTER 2025-04-29 autorizado.
- [ ] Verificar la creación no destructiva de `GCP_ONLY_fixed_model_v1` y `GCP_P1_fixed_model_v1`.
- [ ] Revisar `branch_setup_fixed_model_v1_v0_9_0.json` y someterlo a un nuevo dictamen geomático.
- [x] Fijar y automatizar el conjunto exacto de parámetros de Optimize Cameras tras comprobar la API 2.3.1.
- [ ] Mantener bloqueados preflight, optimización, exportación, productos y otros vuelos hasta ese dictamen.

## Desarrollo Metashape pendiente

- [x] Añadir prueba de integración ejecutada por Metashape 2.3 sobre una imagen P1 real.
- [x] Añadir `optimize_branch.py` con parámetros bloqueados e informe antes/después.
- [x] Añadir extracción objetiva de RMSE, sesgos, reproyección y calibración.
- [x] Añadir comparación objetiva lado a lado y deltas `GCP_P1 - GCP_ONLY`, con huellas de entrada y evidencia de dos CP declarada exploratoria.
- [ ] Ejecutar preflight de ambas ramas sólo tras autorización geomática expresa.
- [ ] Ejecutar las dos optimizaciones y exportar métricas sólo tras autorización geomática expresa.
- [ ] Ejecutar y verificar el comparador existente con dos informes reales autorizados y comparables; hasta ahora sólo se probó con entradas sintéticas.
- [ ] Definir y documentar la decisión humana de selección entre `GCP_ONLY` y `GCP_P1` cuando existan métricas reales, reconociendo la limitación de dos CP; el comparador no decide ni puntúa.
- [ ] Implementar nube, DSM/DTM y ortomosaico solamente después de elegir la solución geométrica.
- [ ] Implementar conversión vertical final EGM08IGN con validación independiente.
- [ ] Añadir perfiles de producto para clasificación y para reconstrucción 3D.
- [x] Crear manifiesto SHA-256 verificable para v0.9.0.
- [ ] Procesar campañas restantes solo después de aprobar el piloto.

## Adaptador Pix4D pendiente

- [ ] Confirmar instalación, licencia y posibilidades de automatización de Pix4Dmapper 4.1.
- [x] Preparar esquema común documental de campaña RGB P1, sin llamadas de motores; implementación y aceptación operativas permanecen pendientes.
- [ ] Mapear JobXML/XMP, GCP/CP y referencia vertical a Pix4D.
- [ ] Reproducir el mismo conjunto de imágenes y roles.
- [ ] Extraer métricas y productos comparables con Metashape.

## Investigación pendiente

- [ ] Decidir y documentar si se mantiene la aproximación isotrópica `X=Y=Horizontal` o se adopta otra ponderación; Trimble confirma metros y 1-sigma, pero no componentes X/Y independientes.
- [ ] Documentar solapes reales de todos los vuelos y contrastarlos con los mínimos recomendados para agricultura.
- [ ] Definir cómo comunicar incertidumbre con solo dos Check Points.
