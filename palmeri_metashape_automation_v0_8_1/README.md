# Palmeri Metashape Automation v0.8.1

Versión robusta multi-campaña para Agisoft Metashape Professional 2.3.x.

## Cambio crítico respecto a v0.6

Los GCP y Check Points se cargan **antes de Match Photos / Align Cameras**.

La secuencia es ahora:

```text
crear *_INCOMPLETE.psx
        ↓
configurar CRS y accuracies
        ↓
cargar imágenes + GPS/XMP
        ↓
Camera Reference OFF
        ↓
cargar GCP/CP Source XYZ
        ↓
todos los marcadores OFF
        ↓
VALIDACIÓN PRE-ALIGN
        ↓
guardar INCOMPLETE
        ↓
Match Photos
        ↓
guardar INCOMPLETE
        ↓
Align Cameras
        ↓
VALIDACIÓN POST-ALIGN
        ↓
crear *_MASTER.psx
```

Por tanto, un archivo terminado en `_MASTER.psx` solo aparece si el flujo completo
ha superado la validación automática.

Si el proceso falla, queda únicamente un proyecto claramente identificado como:

```text
*_INCOMPLETE.psx
```

en:

```text
D:\datos_palmeri\_geomatics_automation\<CAMPAÑA>\work\
```

Esto permite inspeccionar el punto exacto de fallo sin confundirlo con un MASTER válido.

## CRS 2025

```text
Chunk / Output       EPSG:25830
Camera Reference     EPSG:4326
Marker Reference     EPSG:25830
Marker accuracy      0.02 / 0.02 / 0.02 m
Marker projection    0.5 px
```

## GCP 2025

`control/gcp_2025.csv`

E1, E3, E4 y E6 son GCP.

C2 y C5 son CHECK_POINT.

## 2026

`control/gcp_2026.csv` permanece vacío hasta introducir las coordenadas reales de 2026.

## Prueba recomendada

Elimina únicamente:

```text
D:\datos_palmeri\_geomatics_automation\2025
```

Después ejecuta:

```text
launchers\2025_02_pilot.bat
```

Si el proceso termina correctamente debe existir:

```text
D:\datos_palmeri\_geomatics_automation\2025\projects\metashape\
2025-04-29\RGB_P1\2025-04-29_RGB_P1_A0_MASTER.psx
```

Antes de marcar, verifica:

- cámaras Source en WGS84;
- Camera Reference OFF;
- E1/E3/E4/E6/C2/C5 ya presentes;
- Marker Source XYZ en EPSG:25830;
- marcadores OFF;
- Marker accuracy = 0.02 m;
- Marker projection accuracy = 0.5 px;
- bloque A0 correctamente alineado.

Después marca las seis dianas y ejecuta:

```text
launchers\2025_03_validate_pilot.bat
```

## Nueva campaña

No modifiques Python.

1. Copia `campaigns/_template_campaign.json`.
2. Crea `campaigns/<ID>.json`.
3. Define CRS, accuracies, rutas y fechas.
4. Copia `control/_template_gcp.csv`.
5. Crea `control/gcp_<ID>.csv`.
6. Ejecuta `launchers/run_campaign.bat`.


## Gestión del proyecto temporal en v0.8

Por defecto `keep_incomplete_on_success=false`.

Durante el procesamiento existe un proyecto `*_INCOMPLETE.psx` dentro de `work/`.
Si el vuelo termina correctamente, ese proyecto se mueve/renombra a `*_MASTER.psx`
y se verifica abriéndolo de nuevo. No se conserva una copia duplicada.

Si falla una fase, `INCOMPLETE` permanece disponible para diagnóstico.


## Rutas de fotografías en v0.8.1

Las rutas de las imágenes se guardan de forma absoluta. Esto permite promover el
proyecto desde `work/` a `projects/` sin cambiar el significado de las referencias
a los JPG originales.

El pipeline y el validador comprueban además que todas las rutas existan.
