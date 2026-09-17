# Orthomation

Orthomation desarrolla flujos reproducibles para preparar y comparar reconstrucciones RGB de vuelos con drones. El objetivo es conservar la geometría y las dimensiones de los objetos y documentar las decisiones, evidencias y límites de cada resultado.

## Estado del proyecto

El adaptador activo es **Palmeri Metashape Adapter v0.9.0**, dirigido a Agisoft Metashape Professional 2.3.x. El flujo experimental actual está preparado para el piloto 2025; todavía no se ha repetido ese procesamiento con v0.9.0 ni se han generado productos finales comparables.

La campaña 2026 está bloqueada para revisión geomática. El candidato JobXML recibido pasa las reglas del parser si se proporciona explícitamente, pero la ruta local predeterminada de la campaña conserva la copia antigua de 2025. No ejecutar vuelos 2026 ni copiar datos de control a GitHub.

## Paquetes

- [`palmeri_metashape_adapter_v0_9_0/`](palmeri_metashape_adapter_v0_9_0/README.md): adaptador activo, instrucciones de instalación, operación, validación y pruebas.
- [`palmeri_metashape_automation_v0_8_1/`](palmeri_metashape_automation_v0_8_1/README.md): versión histórica de referencia; no es el flujo activo.
- [`palmeri_metashape_v8_0_2/`](palmeri_metashape_v8_0_2/README_v8_0_2.md): prototipo histórico de corrección vertical; no es el flujo activo.

## Documentación del proyecto

- [Estado actual](ESTADO_ACTUAL.md): resultado alcanzado, bloqueos y punto seguro de reanudación.
- [Facts](FACTS.md): hechos, decisiones, evidencia y limitaciones metodológicas.
- [Tareas](TASKS.md): validaciones y desarrollo pendientes.
- [Manuales locales](manuales/): referencias de Metashape 2.3 y Pix4Dmapper 4.1.
- [Agentes del proyecto](agents/orchestrator.md): responsabilidades y flujo de revisión documental, técnica y geomática.

## Inicio rápido

Para instalar y operar el adaptador activo, sigue primero su [guía de uso](palmeri_metashape_adapter_v0_9_0/README.md). En resumen, necesitarás Windows, Agisoft Metashape Professional 2.3.x, imágenes originales y los JobXML de control entregados por separado. Los JobXML y otros datos de vuelo se excluyen del repositorio.

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
