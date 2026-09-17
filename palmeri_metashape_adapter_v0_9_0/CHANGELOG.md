# Changelog

## Experimento `fixed_model_v1` — 2026-09-17

- Cambia únicamente `optimization.adaptive_fitting` a `false`; conserva ambos presets de alineación con `adaptive_fitting=true`.
- Registra el dictamen final `APPROVED_WITH_CONDITIONS`: contrato y tolerancias `1e-12` aprobados, con autorización operativa limitada a la preparación no destructiva de ramas.
- Añade la preparación de ramas nuevas con `run_id` desde la huella MASTER autorizada, sin alterar ramas o JSON adaptativos existentes; no consta todavía su ejecución satisfactoria.
- Endurece el preflight a 43 cámaras, seis proyecciones por marcador, C2/C5 OFF, rotaciones OFF y ausencia de derivados.
- Hace la optimización fail-closed: sólo guarda `OPTIMIZED_FIXED_MODEL` si el conjunto solicitado y la calibración posterior cumplen el contrato.
- Añade exportación de residuos, sesgos, RMSE, reproyección, conteos y calibración sin selección automática de rama.
- Registra un smoke no procesante satisfactorio en Metashape Professional 2.3.1 build 22580, sin aplicar la tarea de optimización.
- Añade el contrato dual de huella MASTER aprobado: persistida `49925af…`, API live `e75f994c…` y equivalencia común a 12 cifras `53c4790f…`, con límite `1e-15` y comprobación estructural completa.
- Amplía el smoke para abrir el MASTER con `read_only=True`, verificar las dos representaciones sin guardar el proyecto y registrar `max |delta|=7.771561172376096e-16` frente al límite `1e-15`.
- Registra 22/22 pruebas unitarias puras correctas y mantiene bloqueados preflight, optimización, exportación, productos y otros vuelos hasta revisar el informe de preparación.

## Corrección — 2026-09-17 (huella de transformaciones)

- Adapta la huella SHA-256 de transformaciones a Metashape 2.3, cuya matriz puede iterarse como una secuencia plana de números.
- Centraliza la serialización para que creación de ramas, preflight y optimización calculen exactamente la misma huella.
- Recarga el módulo compartido al ejecutar scripts desde una sesión de Metashape que ya lo tenía en memoria.
- Añade pruebas para matrices planas, matrices iterables por filas y orden estable de cámaras.

## Documentación — 2026-09-17 (guía del repositorio)

- Añade README raíz con propósito, mapa del repositorio, estado, límites y referencias para empezar.
- Amplía la guía del adaptador con preparación local, pasos de operación, informes, seguridad, pruebas y límites de la versión activa.
- Detalla el registro de campañas nuevas y su bloqueo hasta revisión geomática.

## Documentación — 2026-09-17

- Registra la recepción del JobXML 2026, su SHA-256 y resultado PASS de las reglas automáticas del parser.
- Registra que la campaña sigue apuntando a la copia antigua local; requiere dictamen geomático antes de sustituirla.
- Corrige la afirmación previa de que el JobXML 2026 era idéntico al de 2025.

## 0.9.0

- Integra la corrección vertical experimental en el pipeline masivo.
- Sustituye CSV provisionales por JobXML validado.
- Usa `h` elipsoidal en el ajuste y conserva `H` EGM08IGN para salida.
- Aplica precisión individual a cada marcador.
- Valida RTK/XMP P1 y rango de altura cámara-terreno.
- Añade QA de imagen sin exclusión automática.
- Corrige `Exclude stationary tie points` y respeta la configuración de Reference Preselection.
- Añade preset `MORPHOLOGY_MAX` con Guided Matching.
- Añade modo individual y override de JobXML.
- Añade metadatos y huellas SHA-256 dentro del proyecto.
- Añade puertas de marcado, creación segura de ramas y validación pre-optimización.
- Cuenta únicamente proyecciones de marcador confirmadas (`pinned`), no predicciones automáticas.
- Elimina la sobrescritura automática y los CSV verticales provisionales.
