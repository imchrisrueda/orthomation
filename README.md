# Orthomation

Orthomation desarrolla flujos reproducibles para preparar y comparar reconstrucciones de vuelos con drones. La implementación activa trabaja con RGB DJI P1 en Metashape; multiespectral, térmico y Pix4D son alcance futuro. El objetivo es conservar la geometría y las dimensiones de los objetos y documentar las decisiones, evidencias y límites de cada resultado.

## Estado del proyecto

Revisión documental: **2026-10-02**. Evidencia científica conservada: **2026-09-19**; no se han repetido ejecuciones Metashape ni auditorías de datos reales. Los controles offline nuevos usan entradas sintéticas.

`main` y `feature/validacion-jobxml-y-comparativa-ramas` conservan los mismos incrementos publicados desde la base `40ca7af`, mediante fast-forward. Los desarrollos de preparación documental están descritos en [FACTS §15–16](FACTS.md#15-preparación-offline-de-contratos-y-evaluación-2026-10-02). Consulta `git log -1 --oneline` y `git branch -vv` para las referencias actuales. CI Windows del commit de implementación `ed7a73d`: [main PASS](https://github.com/imchrisrueda/orthomation/actions/runs/37066927620) y [feature PASS](https://github.com/imchrisrueda/orthomation/actions/runs/37066927301), 100 pruebas sin omisiones y 50 fuentes verificadas en ambas ejecuciones.

El adaptador activo es **Palmeri Metashape Adapter v0.9.0**, dirigido al entorno revisado Agisoft Metashape Professional 2.3.1. El piloto 2025-04-29 dispone de MASTER y marcado validados; el dictamen geomático del experimento `fixed_model_v1` autoriza ahora únicamente crear de forma no destructiva dos ramas nuevas y detenerse a revisar su informe. No consta que esa preparación haya terminado y no se han generado productos finales comparables.

La campaña 2026 está bloqueada para revisión geomática. La evidencia del 19/09 registra que el candidato pasa las reglas estructurales pero queda `REVIEW_REQUIRED`: identidad, roles GCP/CP, EPSG y unidades sin aceptación, época sin fijar y diagnóstico de proximidad contradictorio con el mapeo. La copia predeterminada local era de 2025; su presencia y huella no se han revalidado hoy. No ejecutar vuelos 2026 ni copiar datos de control a GitHub.

## Paquetes

- [`palmeri_metashape_adapter_v0_9_0/`](palmeri_metashape_adapter_v0_9_0/README.md): adaptador activo, instrucciones de instalación, operación, validación y pruebas.

Los controles offline están implementados y aceptados técnicamente tras revisión QA y de controles geomáticos independientes: autorización por fase, configuración, integridad byte a byte, HTML de comparación y checker/CI. Desde la raíz, `python tools/check_repository.py` comprueba el repositorio y ejecuta la suite pura sin imágenes ni JobXML reales. Resultado local actual: 100 pruebas, una omitida por permisos de symlink en Windows; manifiesto de 50 fuentes correcto. Esta aceptación técnica no concede nuevas autorizaciones científicas. Véanse [comandos y límites del adaptador](palmeri_metashape_adapter_v0_9_0/README.md#controles-offline).

La [preparación offline](palmeri_metashape_adapter_v0_9_0/planning/README.md) incluye contrato por vuelo, protocolo de evaluación y esquema común de campaña RGB P1 en borrador. QA y revisión geomática independientes emitieron PASS técnico para ambos incrementos. Los tres artefactos no autentican evidencia ni se consumen por el runtime; los mapeos a motores y la aceptación humana siguen pendientes. Los incrementos `a2f9497` y `ed7a73d` están publicados, con evidencia y límites en [FACTS §16](FACTS.md#16-esquema-común-de-campaña-y-comprobación-ci-2026-10-02).

## Documentación del proyecto

- [Estado actual](ESTADO_ACTUAL.md): revisión documental 2026-10-02, evidencia científica al 2026-09-19, bloqueos y punto seguro de reanudación.
- [Facts](FACTS.md): hechos, decisiones, evidencia y limitaciones metodológicas.
- [Tareas](TASKS.md): validaciones y desarrollo pendientes.
- [Manuales locales](manuales/): referencias de Metashape 2.3 y Pix4Dmapper 4.1.
- [`AGENTS.md`](AGENTS.md): contrato vigente de coordinación, límites científicos, delegación y Git para Codex.
- Los roles ejecutables vigentes están en `.codex/agents/` y los procedimientos repetibles en `.agents/skills/`.

Codex descubre las skills del proyecto en `.agents/skills/<nombre>/SKILL.md`; cada archivo incluye metadatos YAML `name` y `description`. Invócalas como `$validate-jobxml`, `$review-metashape-run`, `$document-milestone` o `$release-package`. Los perfiles de agentes usan archivos TOML independientes con `name`, `description` y `developer_instructions`; la delegación depende de las capacidades del runtime y sigue los límites de `AGENTS.md`. Resuelve las rutas desde la raíz del repositorio aunque trabajes en una subcarpeta. Formatos según la documentación oficial de [agentes](https://learn.chatgpt.com/docs/agent-configuration/subagents) y [skills](https://learn.chatgpt.com/docs/build-skills).

## Inicio rápido

El catálogo de esta sesión confirma el descubrimiento de las cuatro skills. La aplicación técnica de perfiles de agentes en el runtime no está verificada; `quick_validate.py` no pudo ejecutarse por ausencia de PyYAML.

Para instalar y operar el adaptador activo, sigue primero su [guía de uso](palmeri_metashape_adapter_v0_9_0/README.md). En resumen, necesitarás Windows, Agisoft Metashape Professional 2.3.x, imágenes originales y los JobXML de control entregados por separado. Los JobXML y otros datos de vuelo se excluyen del repositorio.

La única acción geomática autorizada actualmente es abrir el MASTER 2025-04-29 en Metashape 2.3.1 y ejecutar `scripts/prepare_branches.py`. Después hay que revisar `branch_setup_fixed_model_v1_v0_9_0.json` y detenerse. Preflight, optimización, exportación de métricas, productos y otros vuelos permanecen bloqueados; consulta la [fuente histórica del dictamen `fixed_model_v1`](FACTS.md#12-experimento-de-optimización-fixed_model_v1), accesible mediante `git show`.

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
