# Orthomation

Orthomation desarrolla flujos reproducibles para preparar y comparar reconstrucciones RGB de vuelos con drones. El objetivo es conservar la geometría y las dimensiones de los objetos y documentar las decisiones, evidencias y límites de cada resultado.

## Estado del proyecto

El adaptador activo es **Palmeri Metashape Adapter v0.9.0**, dirigido al entorno revisado Agisoft Metashape Professional 2.3.1. El piloto 2025-04-29 dispone de MASTER y marcado validados; el dictamen geomático del experimento `fixed_model_v1` autoriza ahora únicamente crear de forma no destructiva dos ramas nuevas y detenerse a revisar su informe. No consta que esa preparación haya terminado y no se han generado productos finales comparables.

La campaña 2026 está bloqueada para revisión geomática. El candidato JobXML recibido pasa las reglas del parser si se proporciona explícitamente, pero la ruta local predeterminada de la campaña conserva la copia antigua de 2025. No ejecutar vuelos 2026 ni copiar datos de control a GitHub.

## Paquetes

- [`palmeri_metashape_adapter_v0_9_0/`](palmeri_metashape_adapter_v0_9_0/README.md): adaptador activo, instrucciones de instalación, operación, validación y pruebas.

## Documentación del proyecto

- [Estado actual](ESTADO_ACTUAL.md): corte 2026-09-18, resultado alcanzado, bloqueos y punto seguro de reanudación.
- [Facts](FACTS.md): hechos, decisiones, evidencia y limitaciones metodológicas.
- [Tareas](TASKS.md): validaciones y desarrollo pendientes.
- [Manuales locales](manuales/): referencias de Metashape 2.3 y Pix4Dmapper 4.1.
- [`AGENTS.md`](AGENTS.md): contrato vigente de coordinación, límites científicos, delegación y Git para Codex.
- Los roles ejecutables vigentes están en `.codex/agents/` y los procedimientos repetibles en `.agents/skills/`.

## Inicio rápido

Para instalar y operar el adaptador activo, sigue primero su [guía de uso](palmeri_metashape_adapter_v0_9_0/README.md). En resumen, necesitarás Windows, Agisoft Metashape Professional 2.3.x, imágenes originales y los JobXML de control entregados por separado. Los JobXML y otros datos de vuelo se excluyen del repositorio.

La única acción geomática autorizada actualmente es abrir el MASTER 2025-04-29 en Metashape 2.3.1 y ejecutar `scripts/prepare_branches.py`. Después hay que revisar `branch_setup_fixed_model_v1_v0_9_0.json` y detenerse. Preflight, optimización, exportación de métricas, productos y otros vuelos permanecen bloqueados; consulta el [dictamen `fixed_model_v1`](palmeri_metashape_adapter_v0_9_0/FIXED_MODEL_V1_REVIEW.md).

Las pruebas unitarias puras se ejecutan desde la carpeta del adaptador:

```powershell
cd palmeri_metashape_adapter_v0_9_0
python -m unittest discover -s tests -v
```

Estas pruebas no procesan imágenes. La integración con Metashape necesita la aplicación y los datos de entrada locales.

## Principios operativos

- No sobrescribir proyectos automáticamente; `overwrite_policy` es `forbid`.
- Revisar la calidad de imagen y marcar GCP/CP manualmente antes de crear ramas.
- Mantener Check Points fuera del ajuste. Dos CP sólo permiten evidencia exploratoria.
- Comparar `GCP_ONLY` y `GCP_P1` antes de generar nube, DSM/DTM u ortomosaico.
- Ajustar cámaras y marcadores con alturas elipsoidales; convertir a altura ortométrica sólo como etapa explícita posterior.
- Consultar el README del paquete activo para requisitos, comandos, salidas y puertas de validación completas.
