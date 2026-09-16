# Changelog

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
