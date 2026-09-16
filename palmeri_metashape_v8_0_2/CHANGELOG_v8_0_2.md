# CHANGELOG — v8.0.2

- Resuelto el datum vertical del levantamiento 2025-04-29 mediante JobXML.
- Confirmado `EGM08IGN` como modelo geoidal del trabajo Trimble.
- Añadidas simultáneamente H ortométrica y h elipsoidal para los seis puntos.
- Metashape pasa a usar h elipsoidal como Z de referencia con `EPSG::25830`.
- Reemplazado `marker_accuracy = 0.020 m` global/provisional por precisiones GNSS por punto.
- X/Y reciben el valor `Horizontal`; Z recibe `Vertical` del JobXML.
- `camera_crs` fijado explícitamente a WGS84 / EPSG:4326.
- `marker_crs` y `chunk.crs` fijados explícitamente a EPSG:25830.
- El MASTER queda sin restricciones externas.
- `GCP_P1` utiliza solo XYZ de cámara; yaw/pitch/roll quedan OFF para no introducir una segunda variable experimental.
- Añadido QA de posible mezcla H/h y validación previa a Optimize Cameras.
- Optimize Cameras sigue siendo manual y posterior al QA de proyecciones.
