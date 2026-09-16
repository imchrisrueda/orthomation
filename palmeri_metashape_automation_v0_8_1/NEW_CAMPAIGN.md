# Nueva campaña

Editar únicamente:

- `campaigns/<ID>.json`
- `control/gcp_<ID>.csv`

Parámetros principales por campaña:

```json
"output_crs": "EPSG::25830",
"camera_reference_crs": "EPSG::4326",
"marker_crs": "EPSG::25830",
"marker_accuracy_m": [0.02, 0.02, 0.02],
"marker_projection_accuracy_px": 0.5
```

Los GCP pertenecen al CSV de control de la campaña, nunca al código Python.
