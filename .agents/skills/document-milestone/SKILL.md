---
name: document-milestone
description: Documentar un hito o dictamen aceptado de Orthomation y actualizar su trazabilidad, estado y tareas pendientes.
---

# Document milestone

Resuelve las rutas de documentación y del paquete activo desde la raíz del repositorio, incluso si la sesión se inició en una subcarpeta.

Usar sólo después de aceptar un hito, dictamen o cambio técnico. Actualiza únicamente los artefactos afectados: `ESTADO_ACTUAL.md` (estado, bloqueo y punto seguro), `FACTS.md` (hechos/evidencia/decisiones), `TASKS.md` (progreso y siguiente acción), README aplicable, `CHANGELOG.md`, manifiestos y versión cuando corresponda.

Mantén separados hechos confirmados, decisiones, limitaciones, riesgos y preguntas abiertas. Las afirmaciones técnicas deben identificar fuente, versión y sección/ruta. No conviertas un PASS automático en aceptación geomática ni declares disponibilidad de una función bloqueada. Revisa Git, exclusiones y hashes; no incluyas JobXML, imágenes, datos de vuelo, secretos o resultados pesados. Registra qué se actualizó y qué sigue pendiente.
