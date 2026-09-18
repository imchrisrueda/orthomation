# Palmeri Metashape Adapter v0.9.0

Adaptador activo para inventariar vuelos RGB, crear un MASTER y preparar una comparación controlada en Agisoft Metashape Professional 2.3.1. La definición científica y el estado global están en [`../FACTS.md`](../FACTS.md), [`../ESTADO_ACTUAL.md`](../ESTADO_ACTUAL.md) y [`../TASKS.md`](../TASKS.md).

## Estado operativo

- Piloto 2025-04-29: la siguiente acción autorizada es preparar, de forma no destructiva, las ramas `GCP_ONLY_fixed_model_v1` y `GCP_P1_fixed_model_v1` desde el MASTER autorizado. Después debe revisarse el informe generado y solicitarse dictamen geomático antes de preflight, optimización, métricas o productos.
- Campaña 2026: bloqueada hasta aceptar geomáticamente el JobXML configurado y corregir la copia local que resuelve `default_jobxml`.
- No se generan nube, DSM/DTM ni ortomosaico hasta validar la solución geométrica, comparar ramas y registrar una selección humana.

## Preparación

1. Configura una ruta local de salida en `config/global.json` (`generated_root`).
2. Comprueba `campaigns/<id>.json`: estado, rutas, CRS, geoide, puntos y roles aprobados.
3. Coloca el JobXML aprobado bajo `control/jobxml/`; los `*.jxl` no se añaden a Git.
4. Confirma que Metashape Professional 2.3.1 está disponible para los lanzadores en `launchers/`.

Para registrar una campaña, usa [`NEW_CAMPAIGN.md`](NEW_CAMPAIGN.md).

## Flujo seguro

Los lanzadores ejecutan `scripts/palmeri_pipeline.py` dentro de Metashape. Revisa los informes de inventario y calidad; el marcado manual de GCP/CP es obligatorio. Los scripts `prepare_branches.py`, `validate_before_optimize.py` y `optimize_branch.py` se ejecutan desde Metashape con el proyecto y chunk correctos abiertos, nunca con el Python de sistema.

- `overwrite_policy=forbid`: no se sobrescriben proyectos, ramas ni informes.
- Los Check Points permanecen fuera del ajuste.
- El bundle adjustment usa alturas elipsoidales; la conversión EGM08IGN es una etapa posterior explícita y validada.
- La rama sólo puede optimizarse después de un preflight `PASS` y autorización geomática vigente.

## Pruebas

Desde este directorio:

```powershell
python -m unittest discover -s tests -v
```

`tests/test_orthomation_core.py` contiene pruebas puras. Los smoke de `tests/` requieren Metashape 2.3.1 y las entradas locales autorizadas; sus resultados se generan fuera de Git para cada ejecución.
