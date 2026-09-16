# Facts del proyecto Orthomation

Fecha de corte: 2026-09-16.

Este documento distingue hechos confirmados, decisiones metodológicas adoptadas y cuestiones todavía abiertas. No convierte una hipótesis en hecho.

## 1. Propósito y alcance

- El objetivo es producir ortomosaicos y reconstrucciones geométricas RGB comparables, con máxima conservación posible de formas y dimensiones, que sirvan después como entrada para clasificación automática o modelado 3D.
- Habrá dos adaptadores independientes: Agisoft Metashape y Pix4Dmapper. Deben poder utilizarse indistintamente sobre una definición común de campaña, pero no compartirán llamadas internas ni proyectos.
- La primera implementación y validación se realiza en Agisoft Metashape Professional 2.3.x. Pix4Dmapper 4.1 se abordará después.
- El software no decidirá automáticamente qué fotografías de una diana son correctas. El marcado de GCP/CP y su revisión son una puerta manual obligatoria.

## 2. Datos confirmados del levantamiento 2025

- Sensor: DJI Zenmuse P1, 45 MP, imágenes de 8192 x 5460 píxeles.
- El piloto del 29/04/2025 contiene 43 JPG y todos incluyen XMP DJI legible.
- Los 43 XMP declaran `GpsStatus=Normal`, `AltitudeType=RtkAlt`, `RtkFlag=50` y `SurveyingMode=1`.
- Rango de desviaciones estándar XMP observado:
  - longitud: 0,02842-0,03002 m;
  - latitud: 0,03127-0,03259 m;
  - altura: 0,05964-0,06384 m.
- El fichero `Timestamp.MRK` etiqueta la Z como `Ellh` y contiene coordenadas posteriores a compensación y desviaciones estándar norte/este/elevación.
- DJI documenta que `AbsoluteAltitude` es altura geodésica, que `RtkStdLon/Lat/Hgt` son desviaciones estándar y que `RtkFlag=50` es solución fija centimétrica. DJI también indica que las fotografías P1 registran la posición de la pupila de salida del objetivo y que las coordenadas MRK son posteriores a la compensación. Fuentes: [manual oficial Zenmuse P1](https://dl.djicdn.com/downloads/Zenmuse_P1/20210510/Zenmuse_P1%20_User%20Manual_EN_v1.2_1.pdf), [soporte oficial P1](https://www.dji.com/support/product/zenmuse-p1) y [descripción oficial del MRK](https://repair.dji.com/help/content?customId=01700003680&lang=en&paperDocType=ARTICLE&re=US&spaceId=17).
- Por lo anterior, no se aplica un segundo lever arm inventado en el adaptador.

## 3. Control terrestre y referencia vertical 2025

- JobXML: `2025-GPS-ensayopalmeri-poveda.jxl`, Trimble JobXML 5.72.
- Sistema horizontal: ETRS89 / UTM 30 North.
- Ajuste vertical de campo: `GeoidModel` con `EGM08IGN`.
- Los seis puntos configurados son `NetworkFix`, sin `PoorPrecisionsWarning`.
- El JobXML conserva simultáneamente:
  - `WGS84/Height`: altura elipsoidal `h`;
  - `Grid/Elevation`: altura ortométrica `H` referida a EGM08IGN.
- La separación `N = h - H` es aproximadamente 51,2116 m y su dispersión entre puntos es inferior a 0,2 mm.
- Roles actuales:
  - GCP: E1, E3, E4 y E6;
  - Check Points: C2 y C5.
- Solo existen dos CP. Sirven para diagnóstico externo, pero no permiten una caracterización estadística robusta de la exactitud espacial completa. Esta limitación debe figurar en los resultados.

## 4. Decisión geodésica adoptada

- El bundle adjustment se realiza con altura elipsoidal para cámaras y marcadores.
- Cámara: EPSG:4326, con Z elipsoidal procedente del XMP P1.
- Marcadores: X/Y ETRS89 / UTM 30N (EPSG:25830) y Z elipsoidal procedente del JobXML.
- Chunk/salida horizontal de trabajo: EPSG:25830.
- La salida ortométrica EGM08IGN se generará mediante una transformación vertical explícita después de cerrar la solución geométrica. No se mezclan `h` y `H` dentro del ajuste.
- El manual Metashape 2.3, sección Coordinate System, indica que una altitud debe ser altura sobre el elipsoide salvo que se seleccione un sistema compuesto con geoide. También admite CRS diferentes para cámaras, marcadores y chunk (manual, páginas impresas 99-110).

## 5. Precisión y ponderación

- Cada marcador recibe precisión individual `X=Y=Horizontal`, `Z=Vertical` desde `PointRecord/Precision`.
- La interpretación `X=Y=Horizontal` es una decisión operativa pendiente de confirmar con la definición estadística exacta de Trimble; no se presenta como hecho metrológico definitivo.
- Cada cámara conserva `RtkStdLon`, `RtkStdLat` y `RtkStdHgt` por fotografía. Se rechazan valores ausentes, no positivos, superiores a 0,5 m o estados no fijos.
- El manual Metashape señala que las precisiones RTK/PPK deben cargarse individualmente; en caso contrario se asume por defecto 10 m. También permite precisiones diferentes por coordenada y por elemento (manual, páginas impresas 101 y 112).
- Las orientaciones yaw/pitch/roll se cargan para auditoría, pero permanecen desactivadas en ambas ramas. La única variable de `GCP_ONLY` frente a `GCP_P1` es la posición XYZ P1.

## 6. Alineación seleccionada

Preset principal `MORPHOLOGY_MAX`:

- Accuracy High (`downscale=1`): imágenes a resolución original.
- Generic Preselection: ON.
- Reference Preselection: OFF.
- Exclude stationary tie points: OFF.
- Key point limit: 40 000.
- Tie point limit: 10 000.
- Guided Matching: ON.
- Adaptive Camera Model Fitting: ON.

Fundamento en el manual Metashape 2.3:

- `Exclude stationary tie points` está descrito para fondo estático/turntable y artefactos fijos, no como opción normal de un vuelo nadiral.
- Guided Matching puede mejorar imágenes de vegetación y cámaras de alta resolución.
- Adaptive Camera Model Fitting ayuda a evitar divergencia de parámetros en geometría aérea débil.
- El valor recomendado de tie point limit es 10 000 (manual, páginas impresas 38-40).

Reference Preselection permanece fuera del preset principal porque el piloto ya alineó 43/43 imágenes con conectividad suficiente. Activarla sería una variante separada, no una mejora demostrada del bundle.

## 7. Calidad de imagen y adquisición

- Metashape estima calidad antes de alinear y genera un informe. El umbral 0,5 produce una advertencia, no una exclusión automática.
- Pix4Dmapper 4.1 advierte que la calidad del dataset y el solape condicionan el resultado; para terreno agrícola homogéneo recomienda una malla de vuelo y al menos 85 % de solape frontal y 70 % lateral. Esta recomendación sirve para evaluar la adquisición, no puede corregir vuelos ya capturados.
- La comparación entre motores debe utilizar exactamente el mismo conjunto de fotografías aceptadas y documentar cualquier exclusión.

## 8. Diseño experimental

- MASTER: alineado, con coordenadas y precisiones cargadas pero todas las restricciones externas OFF.
- Puerta manual: revisión de calidad y marcado de GCP/CP.
- `GCP_ONLY`: cuatro GCP ON, dos CP OFF, cámaras XYZ OFF, orientación OFF.
- `GCP_P1`: cuatro GCP ON, dos CP OFF, cámaras XYZ ON, orientación OFF.
- Las ramas parten de una copia idéntica y deben optimizarse con exactamente los mismos parámetros.
- Los CP nunca intervienen en el ajuste.
- Metashape exige como mínimo tres proyecciones para control/check; el protocolo prefiere cinco imágenes adecuadas. Si solo existen tres o cuatro imágenes útiles, se requiere confirmación manual documentada.

## 9. Productos y métricas necesarias

Para seleccionar la mejor solución morfológica se necesitan, como mínimo:

- RMSE y sesgo X, Y, Z, XY y 3D de los CP;
- errores de GCP separados de CP;
- error de reproyección de marcadores y tie points;
- cambios de calibración interior y evidencia de sobreajuste;
- densidad, completitud y ruido de nube;
- GSD y resolución efectiva;
- resolución y referencia vertical del DSM/DTM;
- resolución, NoData, seamlines y consistencia radiométrica del ortomosaico;
- área cubierta, huecos y artefactos;
- tiempo, versión, hardware y parámetros exactos;
- para clasificación: mismas bandas, profundidad radiométrica, resolución, alineación, NoData y esquema de compresión;
- para 3D: precisión métrica, geometría de superficies, completitud y textura, no solo apariencia visual.

La métrica principal de exactitud externa son los CP. Los residuos de GCP describen ajuste interno y no deben presentarse como validación independiente.

## 10. Estado 2026

- El fichero llamado `2026-GPS-ensayopalmeri-poveda.jxl` añadido al workspace tiene la misma huella SHA-256 y el mismo contenido que el de 2025.
- Contiene observaciones del 29/04/2025, no un levantamiento 2026.
- La campaña 2026 permanece bloqueada hasta sustituirlo por el JobXML correcto.

## 11. Fuentes locales contrastadas

- `manuales/metashape-pro_2_3_en.pdf`: alineación, CRS, alturas, GCP/CP, precisiones y optimización.
- `manuales/pix4D_manual_4_1.pdf`: adquisición, solape y flujo Pix4Dmapper 4.1. La implementación Pix4D queda fuera de v0.9.0.

