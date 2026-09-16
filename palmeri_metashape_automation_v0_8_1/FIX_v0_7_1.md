# v0.7.1 — corrección de validación CRS

La v0.7 interpretaba como distintos:

- `EPSG::25830` devuelto por Metashape
- `EPSG:25830` usado internamente para comparar

Los CRS del proyecto eran correctos; el fallo estaba únicamente en la comparación del validador.

v0.7.1 normaliza ambos formatos antes de comparar.

No cambia:
- CRS configurados;
- GCP;
- precisión de marcadores;
- orden GCP-before-alignment;
- política Camera Reference OFF;
- A0.
