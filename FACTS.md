# Facts del proyecto Orthomation

Fecha de corte: 2026-09-19.

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

- La fuente primaria Trimble [`JobXMLSchema-5.72.xsd`](https://www.trimble.com/schema/JobXML/5_7/JobXMLSchema-5.72.xsd), en el elemento `PointRecord/Precision` de tipo `distType`, define `Horizontal` y `Vertical` en metros y como estimaciones 1-sigma.
- Cada marcador recibe precisión individual `X=Y=Horizontal`, `Z=Vertical` desde `PointRecord/Precision`. La asignación del único estadístico horizontal a ambos ejes es una aproximación isotrópica de implementación, no un hecho metrológico sobre componentes X/Y independientes.
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

- El JobXML añadido al workspace el 17/09/2026 es distinto del de 2025. SHA-256 2026: `3b8a66c5475505b90c7be77dfb9a42537971af963f0e01d55c307fa64aa7cd5d`; SHA-256 2025: `877c73e9a409d41c1262adf6921713d009db4a395d977550755b15d8f2b63d18`.
- El parser del adaptador v0.9.0 valida el candidato de la raíz del repo cuando se proporciona esa ruta explícitamente: seis puntos, observaciones de 2026, JobXML 5.72, ETRS89 / UTM 30 North y geoide EGM08IGN.
- `campaigns/2026.json` fija la huella esperada completa del candidato. La ruta `default_jobxml` aún apunta a la copia local antigua en `control/jobxml/`; esta tiene la misma huella que el JobXML 2025 y falla las reglas de año y huella.
- `scripts/validate_jobxml_candidate.py` genera un informe JSON redactado y de sólo lectura: no emite coordenadas, alturas individuales, XML ni rutas absolutas; distingue validación automática de aceptación geomática; detecta dianas `NetworkFix` adicionales; clasifica registros no destinados a control, incluida la base GNSS `FromBase/KeyedIn`, de forma informativa y sin revelar sus identificadores; y nunca reasigna identidades ni desbloquea la campaña.
- Hecho confirmado: el candidato supera las reglas estructurales automáticas, pero queda `REVIEW_REQUIRED`, con `campaign_unlock=false`, porque no están aceptadas su identidad ni sus funciones GCP/CP. El EPSG y las unidades CRS constan con `source=campaign_config` pero siguen sin aceptación geomática; la época continúa sin fijar.
- Inferencia diagnóstica, no autoasignación: la proximidad espacial frente a 2025 sugiere `E1→E6`, `C2→E1`, `E3→C2`, `E4→C5`, `C5→E4`, `E6→E3`. Esta permutación contradice el mapeo configurado y debe ser resuelta por revisión geomática independiente; no modifica etiquetas ni roles.
- El JobXML y los datos de control permanecen excluidos del repositorio remoto. La huella permite verificar localmente qué versión se revisó sin publicar el contenido.

## 11. Fuentes locales contrastadas

- `manuales/metashape-pro_2_3_en.pdf`: alineación, CRS, alturas, GCP/CP, precisiones y optimización.
- `manuales/pix4D_manual_4_1.pdf`: adquisición, solape y flujo Pix4Dmapper 4.1. La implementación Pix4D queda fuera de v0.9.0.

## 12. Experimento de optimización `fixed_model_v1`

### Hechos confirmados

- El experimento está limitado al piloto 2025-04-29 y a Agisoft Metashape Professional 2.3.1.
- `config.global.optimization.adaptive_fitting=false`; los presets de alineación `MORPHOLOGY_MAX` y `BASELINE_A0` conservan `adaptive_fitting=true`.
- El contrato solicita ajustar exactamente `f`, `cx`, `cy`, `k1`, `k2`, `k3`, `p1` y `p2`; mantiene fijos `b1`, `b2` y `k4`; usa `fit_corrections=false` y `tiepoint_covariance=true`.
- La tolerancia absoluta aprobada por revisión geomática es `1e-12`, en unidades nativas de cada parámetro, para auditar `b1`, `b2`, `k4`, `p3` y `p4`.
- El MASTER tiene dos representaciones exactas revisadas: huella persistida `49925af981c6a0076cb5f43490d8b4b344864ebe71a2d0407cb4ec3b2fe24d10` y huella API-live `e75f994cfff3a0a286ee7e3283b4ae2f202ce7869ee4e42c3b4caf0107831520`.
- Metashape 2.3.1 re-ortonormaliza la rotación al cargar. Ambas representaciones coinciden a 12 cifras significativas con huella `53c4790ff878b4b5cc2e132e87f4df5394beba4093bbf928ddfb8ba25b3cc0d1`; la diferencia máxima observada es `7.771561172376096e-16`, inferior al límite revisado `1e-15`. Traslaciones, fila homogénea, etiquetas y estructura permanecen idénticas.
- Las 22 pruebas unitarias puras y los smoke no procesantes terminaron en PASS. La evidencia del MASTER se obtuvo con `Document.open(..., read_only=True)` y no ejecutó preparación, preflight ni optimización.

### Decisión operativa vigente

- El dictamen `APPROVED_WITH_CONDITIONS` autoriza exclusivamente ejecutar `prepare_branches.py` sobre el MASTER 2025-04-29 y revisar `branch_setup_fixed_model_v1_v0_9_0.json`.
- Las ramas previas `GCP_ONLY` y `GCP_P1` y sus JSON deben permanecer intactos; se registran externamente como `REJECTED_ADAPTIVE_FITTING` y `NOT_COMPARABLE_FOR_SELECTION`.
- No hay evidencia de una ejecución satisfactoria de `prepare_branches.py`; las ramas `fixed_model_v1` no se consideran creadas hasta verificar el informe de preparación.

### Limitaciones y bloqueos

- Preflight, optimización, exportación de métricas, selección de rama, productos y otros vuelos requieren un nuevo dictamen geomático.

## 13. Comparación objetiva de ramas

### Hechos confirmados

- `scripts/comparison_core.py` y `scripts/compare_branch_metrics.py` implementan una comparación Python pura, sin importar Metashape ni abrir MASTER o imágenes.
- El comparador exige exactamente un informe `GCP_ONLY` y uno `GCP_P1`, ambos `METRICS_EXPORTED`, sin incidencias y con la misma procedencia, configuración, huellas del MASTER y contrato de optimización.
- Revalida roles y activación de E1/E3/E4/E6 como GCP y C2/C5 como CP, las convenciones de coordenadas y altura elipsoidal, los conteos, cámaras, calibración y agregados matemáticamente derivables. Registra la huella SHA-256 de cada informe sin publicar su ruta.
- La salida aceptada sólo contiene valores lado a lado y deltas `GCP_P1 - GCP_ONLY`; declara `selection_performed=false`, `human_decision_required=true`, `geomatic_acceptance=NOT_GRANTED` y `products_authorized=false`.
- La implementación y los casos adversariales han superado revisión geomática y QA independientes. La suite pura actual contiene 52 pruebas.

### Limitaciones y riesgos

- La implementación sólo se ha probado con informes sintéticos; todavía no existen dos informes reales autorizados para comparar.
- Dos Check Points aportan evidencia exploratoria, no una caracterización robusta de exactitud.
- El comparador no reabre Metashape ni revalida por sí mismo CRS, restricciones GNSS/P1, identidad criptográfica de las imágenes o ausencia actual de productos; esas limitaciones se declaran en su salida.
- La altura comparada es elipsoidal `h`. No se convierte ni se reinterpreta como altura ortométrica `H`.
- Ninguna salida del comparador selecciona una rama o autoriza productos. Ambas decisiones siguen siendo gates humanos.
- La API 2.3.1 permite observar el conjunto solicitado y la calibración antes/después, pero no expone un conjunto efectivo posterior completo ni un estado documentado de correcciones adicionales. El informe debe declarar esa limitación y no inferir resultados ausentes.
- Los dos Check Points sólo proporcionan evidencia exploratoria y no justifican por sí solos una caracterización robusta de exactitud externa.

Fuente canónica del dictamen y evidencias: [`palmeri_metashape_adapter_v0_9_0/FIXED_MODEL_V1_REVIEW.md`](palmeri_metashape_adapter_v0_9_0/FIXED_MODEL_V1_REVIEW.md).
