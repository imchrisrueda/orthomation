# Orthomation — contrato de trabajo para Codex

## Propósito y alcance

Orthomation prepara, procesa y compara reconstrucciones RGB, multiespectrales y térmicas de vuelos con dron mediante Agisoft Metashape y, posteriormente, Pix4D. Debe conservar la trazabilidad, la geometría y las limitaciones de cada resultado. No cambies algoritmos, configuraciones geomáticas, datos de campaña ni resultados científicos salvo especificación explícita y revisión aplicable.

## Fuentes de verdad

Resuelve según esta prioridad: (1) instrucciones explícitas del usuario; (2) evidencia primaria y manuales locales; (3) `FACTS.md`; (4) `ESTADO_ACTUAL.md`; (5) configuración y código activos; (6) `TASKS.md`. No resuelvas contradicciones silenciosamente: regístralas y pide o encarga la evidencia necesaria.

El paquete activo y único mantenido es `palmeri_metashape_adapter_v0_9_0/`. Las versiones anteriores se conservan en el historial Git, no en el árbol de trabajo.

## Invariantes científicos y geomáticos

- Mantén separadas altura elipsoidal `h` y ortométrica `H`: el bundle adjustment usa `h`; EGM08IGN sólo se aplica mediante transformación explícita posterior y validada.
- Mantén cámaras P1 en EPSG:4326 con altura elipsoidal y marcadores en EPSG:25830 con altura elipsoidal; el chunk/salida horizontal es EPSG:25830, salvo una decisión geomática aprobada.
- E1, E3, E4 y E6 son GCP; C2 y C5 son Check Points y permanecen fuera del ajuste. Dos CP sólo dan evidencia exploratoria, no una caracterización robusta.
- No añadas un lever arm P1, ni cambies las restricciones de cámara, CRS, datum, geoide, precisión, calibración, alineación u optimización sin una especificación aprobada.
- No generes nube, DSM/DTM ni ortomosaico antes de validar la solución geométrica, comparar ramas y registrar la selección humana.
- Distingue siempre hechos documentados, decisiones de diseño, hipótesis, limitaciones y riesgos.

La calidad de imagen, el marcado de dianas, la aprobación geomática y la elección final de solución son gates humanos: Codex no puede sustituirlos ni saltárselos.

## Orquestación

El agente principal actúa como orquestador; no existe un subagente `orchestrator`. Paraleliza investigación documental y revisión geomática sólo cuando sean independientes; serializa síntesis, implementación y verificación. Formula una especificación concreta antes de encargar cambios a un único `code_worker`; después encarga revisión independiente a `verifier`. Solicita `geomatics_reviewer` si un cambio puede afectar resultados científicos y usa la Skill `document-milestone` tras aceptar un hito.

- `knowledge_researcher`: evidencia primaria, manuales y API; no modifica archivos ni toma decisiones científicas.
- `geomatics_reviewer`: dictamen independiente sobre validez geomática; puede bloquear cambios, no escribe código.
- `code_worker`: único implementador de código/configuración técnica bajo una especificación aprobada.
- `verifier`: QA independiente posterior; no corrige hallazgos salvo instrucción expresa.

Cada delegación indica objetivo, alcance/archivos autorizados, entradas, criterios de aceptación, pruebas, riesgo geomático y gate humano requerido.

## Git y datos

Mantén cambios atómicos, trazables y revisables. No uses `reset --hard`, `push --force` ni reescritura destructiva de historial. No publiques JobXML, imágenes originales, proyectos, resultados pesados, datos de vuelo, secretos ni archivos ignorados. Revisa estado y diff antes de proponer un commit o publicación.
