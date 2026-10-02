# Estado actual de Orthomation

Revisión documental: 2026-10-02. Corte de evidencia científica: 2026-09-19.

## Ámbito del repositorio revisado

La base común publicada de `main` y `feature/validacion-jobxml-y-comparativa-ramas` es `40ca7af`, con controles offline y CI sólo Windows. El primer incremento de preparación se versionó en `a2f9497`; el esquema común se prepara para publicación. Consulta `git log -1 --oneline` y `git branch -vv` para las referencias actuales. CI remoto de `40ca7af`: [main PASS](https://github.com/imchrisrueda/orthomation/actions/runs/36993914467) y [feature PASS](https://github.com/imchrisrueda/orthomation/actions/runs/36993914504), comprobados en esta sesión.

Hito de integración del 02/10/2026: código, agentes, skills y documentación revisados están versionados e integrados, con cierre documental posterior al fast-forward. No modifica el corte científico ni las autorizaciones vigentes.

Verificación posterior a la integración: `python tools/check_repository.py` PASS con 71 pruebas, una omitida por permisos Windows para symlinks e integridad byte a byte de 41 fuentes correcta; `git diff --check` correcto. El paquete y su manifiesto no requieren cambios para este cierre de documentación raíz.

El flujo implementado es RGB P1. Inventario y preparación MASTER admiten varios vuelos, pero la optimización conserva un contrato específico del piloto. Multiespectral, térmico, productos, conversión vertical y Pix4D requieren desarrollo. Las ejecuciones Metashape y auditorías de datos reales siguientes son históricas y no se han repetido hoy; véase [evidencia del código y límites](FACTS.md#14-revisión-del-repositorio-2026-10-02).

## Controles offline 2026-10-02 (hito técnico aceptado)

Incremento técnico posterior: [preparación offline de contratos por vuelo y protocolo](palmeri_metashape_adapter_v0_9_0/planning/README.md) implementada y aceptada tras QA y revisión geomática estáticas independientes. La CLI valida JSON DRAFT y enumera evidencia pendiente; no abre las referencias ni autentica documentos. Separa estructura de completitud declarativa y mantiene siempre `NOT_EXECUTABLE`, `evidence_verified=false`, `geomatic_acceptance=NOT_GRANTED` y autorizaciones falsas. El contrato activo del piloto, las campañas y los algoritmos científicos no cambian; los borradores no se consumen por el runtime.

Verificación del primer incremento: 17 pruebas nuevas, checker PASS con 88 pruebas totales y una omitida por permisos de symlink en Windows; integridad de 47 fuentes correcta. La CLI y el checker desactivan bytecode antes de importar módulos locales; una prueba en proceso nuevo verifica ausencia de escritura. Los contratos reales y el protocolo siguen pendientes de aceptación humana, incluida la cuestión abierta de FACTS §9. Se versionó posteriormente en `a2f9497`; no se ejecutó Metashape ni se auditaron datos reales.

- Cinco desarrollos implementados y aceptados tras dos revisiones estáticas independientes, QA y controles geomáticos: gates por fase, validación estructural de configuración, integridad byte a byte, HTML objetivo y checker/CI. Sólo preparación conserva autorización histórica; preflight, optimización y métricas permanecen `REVIEW_REQUIRED`.
- `python tools/check_repository.py`: PASS local histórico de 71 pruebas puras sintéticas con una omitida por permisos de symlink; cinco TOML, cuatro skills, enlaces locales y manifiesto de 41 fuentes correctos. No se ejecutaron Metashape ni auditorías de datos reales. El CI de la base publicada `40ca7af` se comprobó posteriormente con éxito.
- Normalizados los finales de línea de fuentes del paquete según `.gitattributes` y regenerado el manifiesto sin cambiar criterios científicos. La configuración exige tipos JSON estrictos y rechaza enteros no representables sin traceback. El hito técnico no concede aprobación humana geomática ni amplía el alcance de procesamiento.
- Alcance de CI corregido a Windows por indicación del usuario: `windows-latest`, sin matriz Ubuntu. Conserva el checker, los pasos y permisos; el resultado de la base publicada ya está comprobado. Este ajuste no modifica gates científicos.

## Esquema común documental 2026-10-02

Hito técnico aceptado tras QA y revisión geomática estáticas independientes: `scripts/common_campaign_core.py` y `planning/_template_common_campaign.json` representan una propuesta RGB P1 `common-campaign-1`. Valida IDs únicos, fechas y referencias por motor/vuelo, metadatos separados de cámara/control y evidencia declarada. Los adaptadores al esquema común son `NOT_IMPLEMENTED` en ambos motores; mapeos `UNVERIFIED`, compatibilidad no comprobada y equivalencia no establecida. La comparación de ramas y el requisito de MASTER/parámetros idénticos se limitan explícitamente a Metashape. No cambia configuraciones científicas ni acepta la campaña 2026.

Resultado local: 12 pruebas nuevas; checker completo PASS con 100 pruebas, una omitida por permisos Windows para symlinks; manifiesto de 50 fuentes correcto. CLI/checker validan tres borradores. Los dos incrementos están preparados para publicación; el resultado CI que ya consta corresponde a `40ca7af`, no a este lote. Su publicación y verificación posteriores se registrarán por commit. Se conservan el corte científico, los bloqueos y el punto seguro de reanudación.

## Revisión de agentes y skills 2026-10-02

- Hito técnico aceptado tras revisión independiente `verifier: PASS`: las cuatro skills de `.agents/skills/` incorporan metadatos YAML `name` y `description`, rutas desde la raíz y la CLI real del auditor `palmeri_metashape_adapter_v0_9_0/scripts/validate_jobxml_candidate.py`.
- `AGENTS.md` y `.codex/agents/{geomatics_reviewer,verifier}.toml` separan el dictamen automatizado de los gates humanos, mantienen `verifier` en sólo lectura y documentan el fallback cuando el runtime no permite seleccionar perfiles o delegar.
- Validación de esta revisión: cinco TOML analizados con `tomllib`, cuatro frontmatter comprobados mediante validación básica de sus campos escalares y `git diff --check` correcto. Fuentes de formato: documentación oficial enlazada en `README.md`, sección «Documentación del proyecto».
- El catálogo de esta sesión confirma el descubrimiento de las cuatro skills. Limitaciones: `quick_validate.py` no pudo ejecutarse por ausencia de PyYAML; la aplicación técnica de perfiles de agentes en el runtime no está verificada. Esta revisión no modifica el estado científico ni sus autorizaciones.

## Cambios documentales del corte 2026-09-19

- El árbol mantenido contiene únicamente `palmeri_metashape_adapter_v0_9_0`; las versiones anteriores se conservan en el historial Git.
- Las instrucciones de trabajo están en `AGENTS.md`; los perfiles de agentes en `.codex/agents/` y los procedimientos repetibles en `.agents/skills/`.
- Se actualizó `README.md` para reflejar esta organización y se regeneró/verificó el manifiesto del paquete activo para incluir su `AGENTS.md`.
- Este corte no cambia configuraciones geomáticas, datos de campaña, resultados ni el alcance de la autorización `fixed_model_v1`.
- El paquete activo se depuró para una nueva serie de pruebas: conserva código, configuración y pruebas ejecutables; elimina documentación narrativa y logs de smoke de iteraciones anteriores. El README del paquete describe únicamente el estado operativo vigente.

## Resultado alcanzado

`palmeri_metashape_adapter_v0_9_0` es la única base mantenida. Las versiones previas se retiraron del árbol de trabajo tras confirmar que no eran dependencias de ejecución; su trazabilidad permanece en el historial Git.

La v0.9.0 ya no depende de CSV con alturas provisionales. Integra directamente el JobXML, usa altura elipsoidal, aplica precisiones individuales, valida XMP P1 y registra QA de imagen.

Para el piloto 2025-04-29 se implementó el experimento no destructivo `fixed_model_v1`. El modelo de optimización fija `adaptive_fitting=false`, mantiene `f, cx, cy, k1, k2, k3, p1, p2` ajustables, fija `b1, b2, k4`, desactiva correcciones y activa `tiepoint_covariance`. Las ramas adaptativas anteriores y sus JSON se conservan sin cambios y quedan excluidos de la selección del experimento nuevo.

El dictamen geomático vigente es `APPROVED_WITH_CONDITIONS`: autoriza sólo `prepare_branches.py` sobre el MASTER 2025-04-29 y obliga a detenerse tras generar y revisar `branch_setup_fixed_model_v1_v0_9_0.json`. No existe evidencia de que esa ejecución haya finalizado.

## Verificaciones históricas registradas hasta 2026-09-19

- Sintaxis Python de todos los scripts: correcta.
- JSON de configuración: correcto.
- Conteos históricos de pruebas puras: 22/22 en la base de `main`; 52/52 en la feature con auditor y comparador. La suite ampliada sí se ejecutó hoy con fixtures sintéticas, como consta arriba; no se reconstruyeron ni ejecutaron las ramas científicas históricas.
- Parser JobXML 2025: seis puntos, `NetworkFix`, EGM08IGN, año y precisiones correctos.
- XMP reales del piloto: 43/43 válidos, RTK fixed y altura elipsoidal coherente.
- Diferencia cámara-terreno elipsoidal observada: 14,558-14,960 m.
- Auditor JobXML candidato: salida redactada, huella esperada obligatoria, dianas `NetworkFix` adicionales visibles, registros no-control informativos con identificadores redactados, roles con procedencia de configuración, comparación opcional sin umbral ni autoasignación y códigos CLI verificados.
- Candidato JobXML 2026: reglas estructurales automáticas correctas y estado final `REVIEW_REQUIRED`; la campaña permanece bloqueada.
- Comparador offline de métricas: validación fail-closed de los informes `GCP_ONLY` y `GCP_P1`, procedencia y contratos equivalentes, recálculo de agregados, huellas de las entradas y deltas objetivos `GCP_P1 - GCP_ONLY`. La salida no selecciona rama, no concede aceptación geomática y no autoriza productos.
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
- No se ha ejecutado el comparador sobre métricas reales; sólo se ha verificado con entradas sintéticas.
- No se han generado nube, DSM/DTM u ortomosaico.
- No se han procesado otros vuelos bajo esta autorización.
- No se ha implementado el adaptador Pix4D.

## Bloqueos

- Campaña 2026: el candidato recibido supera las reglas estructurales automáticas (seis puntos; Trimble JobXML 5.72; observaciones de 2026; ETRS89 / UTM 30 North; EGM08IGN), pero el auditor devuelve `REVIEW_REQUIRED` y `campaign_unlock=false`. La identidad y los roles GCP/CP no están aceptados; EPSG y unidades CRS proceden explícitamente de configuración pero tampoco están aceptados, y la época no está fijada. La proximidad frente a 2025 sugiere una permutación diagnóstica que contradice el mapeo configurado, pero no realiza ni autoriza autoasignación. La copia en `control/jobxml/` sigue siendo la de 2025 y falla año y huella esperada.
- Precisión Trimble: `Horizontal` y `Vertical` están documentadas en metros y a 1-sigma. Usar `X=Y=Horizontal` sigue siendo una aproximación isotrópica, no evidencia de sigmas independientes por componente.
- Experimento `fixed_model_v1`: preflight, optimización, exportación, selección de rama, productos y otros vuelos permanecen bloqueados hasta un nuevo dictamen geomático posterior a la revisión del informe de preparación.
- Comparación de ramas: la herramienta está implementada, pero dos CP sólo proporcionan evidencia exploratoria. La selección final exige métricas reales comparables y una decisión geomática humana documentada.

La evidencia histórica registró el candidato en la raíz del repo, excluido de Git, con SHA-256 `3b8a66c5475505b90c7be77dfb9a42537971af963f0e01d55c307fa64aa7cd5d`. La copia entonces localizada en la ruta configurada y el fichero de 2025 tenían SHA-256 `877c73e9a409d41c1262adf6921713d009db4a395d977550755b15d8f2b63d18`. No se han revalidado hoy presencia, contenido ni huellas de esos datos locales; las referencias a la copia antigua en los bloqueos describen ese corte histórico.

## Control de autorizaciones y deuda restante

La configuración global `review_status=APPROVED` y los estados técnicos de preparación no conceden autorización por fase. Los nuevos gates explícitos están implementados y revisados técnicamente: sólo `prepare_branches` está aprobado con evidencia histórica; las otras tres fases bloquean antes de acceder al proyecto. Quedan pendientes nuevos contratos por vuelo y criterios de selección frente a evaluación posterior de productos ([FACTS §14](FACTS.md#14-revisión-del-repositorio-2026-10-02)). Los bloqueos científicos y el punto seguro siguiente conservan su alcance.

## Punto seguro de reanudación

1. Abrir el MASTER autorizado 2025-04-29 en Metashape Professional 2.3.1 y seleccionarlo como chunk activo.
2. Ejecutar únicamente `palmeri_metashape_adapter_v0_9_0/scripts/prepare_branches.py`.
3. Confirmar que el script crea las ramas con sufijo `fixed_model_v1` sin alterar las ramas adaptativas previas.
4. Revisar `branch_setup_fixed_model_v1_v0_9_0.json`, sus hashes y todas las comprobaciones fail-closed.
5. Detenerse y solicitar un nuevo dictamen geomático antes de preflight.

En paralelo, la campaña 2026 conserva su bloqueo independiente. No debe ejecutarse preflight, optimización, exportación, generación de productos, procesamiento masivo 2025 ni ningún vuelo 2026 con la autorización vigente.
