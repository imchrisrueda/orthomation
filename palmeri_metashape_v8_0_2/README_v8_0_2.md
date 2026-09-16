# Palmeri Metashape automation — v8.0.2

## Qué cambia respecto a v8.0.1

v8.0.2 elimina las configuraciones verticales que estaban como desconocidas/provisionales para el vuelo 2025-04-29 y las sustituye por la información del JobXML/JXL Trimble.

Datos confirmados del JobXML:

- sistema horizontal del trabajo: ETRS89 / UTM 30 North;
- ajuste vertical: `GeoidModel`;
- geoide: `EGM08IGN`;
- `Grid/Elevation`: altura ortométrica H;
- `WGS84/Height`: altura elipsoidal h;
- separación `N = h - H`: aproximadamente 51.212 m;
- los seis puntos son `NetworkFix`;
- la precisión horizontal y vertical se toma por punto desde `PointRecord/Precision`.

## Decisión para Metashape

Para evitar introducir una Z ortométrica en un CRS horizontal EPSG:25830 que Metashape interpretaría por defecto como altura sobre el elipsoide, v8.0.2 utiliza en la referencia de los marcadores:

- X/Y: ETRS89 / UTM 30N — `EPSG::25830`;
- Z: **altura elipsoidal h** del JobXML (`WGS84/Height`);
- altura ortométrica H (`Grid/Elevation`, EGM08IGN): se conserva para auditoría y para transformación/reporte vertical posterior.

Configuración explícita:

- `chunk.crs = EPSG::25830`;
- `marker_crs = EPSG::25830`;
- `camera_crs = EPSG::4326`;
- `marker_projection_accuracy = 0.5 px`;
- precisión de cada marcador: X=Y=`Horizontal`, Z=`Vertical` del JobXML;
- precisión de cámara: conservar los valores P1/XMP por foto ya cargados;
- orientación de cámara: **NO se utiliza como restricción** en ninguna rama.

## Diseño experimental preservado

No es “GCP vs RTK”.

Ambas ramas usan E1, E3, E4 y E6 como GCP y C2/C5 como Check Points.

- `GCP_ONLY`: GCP ON; P1 XYZ OFF; P1 yaw/pitch/roll OFF.
- `GCP_P1`: GCP ON; P1 XYZ ON; P1 yaw/pitch/roll OFF.

La única variable experimental es el uso de la **posición P1**.

## Prueba inmediata

1. Abrir el `MASTER` alineado y marcado, antes de `Optimize Cameras`.
2. Guardar el proyecto.
3. Ejecutar `scripts/01_apply_jobxml_vertical_to_master.py` desde `Tools → Run Script`.
4. Seleccionar el JXL/JobXML del vuelo.
5. El script:
   - valida EGM08IGN y ETRS89/UTM30;
   - reemplaza la Z de E1/C2/E3/E4/C5/E6 por h elipsoidal;
   - carga las precisiones GNSS reales por punto;
   - fija los CRS;
   - deja TODAS las referencias de marcadores y cámaras OFF en MASTER;
   - desactiva las restricciones angulares;
   - guarda `vertical_audit_MASTER_v8_0_2.json`.
6. Revisar en `Reference` que las Z sean aproximadamente 586.26–586.37 m.
7. Revisar las proyecciones problemáticas C2, E1 y E4.
8. No optimizar todavía.

## Después del QA de marcado

1. Ejecutar `scripts/02_prepare_branches.py`.
2. Se crean dos copias del MASTER:
   - `*_GCP_ONLY`;
   - `*_GCP_P1`.
3. Ejecutar `scripts/03_validate_before_optimize.py` en cada rama.
4. Solo si ambas dan `PASS`, ejecutar `Optimize Cameras` con exactamente la misma configuración.

## Importante

La altura ortométrica H no se ha descartado. Se conserva en el CSV de control y en el informe de auditoría. Lo que cambia es qué valor se introduce como Z de referencia en el ajuste de Metashape bajo EPSG:25830 sin geoide compuesto: se utiliza h elipsoidal para mantener coherencia con la interpretación documentada de Metashape.

No ejecutar automáticamente `Update Transform` ni `Optimize Cameras` desde estos scripts. La revisión de marcado sigue siendo una puerta QA obligatoria.
