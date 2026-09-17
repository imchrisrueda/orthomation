# Changelog

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
