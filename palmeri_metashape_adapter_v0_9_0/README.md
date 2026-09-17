# Palmeri Metashape Adapter v0.9.0

Adaptador reproducible para preparar y comparar proyectos RGB de Agisoft Metashape Professional 2.3.

## Principios

- Cada campaña usa un JobXML validado como fuente primaria de GCP/CP.
- El ajuste se realiza con altura elipsoidal `h` tanto para cámaras como para marcadores.
- La altura ortométrica EGM08IGN se conserva y se aplicará de forma explícita a los productos finales.
- Las precisiones de marcadores son individuales: `X=Y=Horizontal`, `Z=Vertical`.
- Las posiciones P1 se leen de XMP y deben ser RTK fixed, `SurveyingMode=1` y `AltitudeType=RtkAlt`.
- DJI P1 registra en la fotografía la posición compensada del centro de perspectiva/salida pupilar; no se añade otro lever arm.
- Las orientaciones P1 nunca participan en el experimento actual.
- El marcado de GCP/CP es una puerta QA manual obligatoria.
- No se sobrescriben proyectos previos automáticamente.

## Flujo

1. `palmeri_pipeline.py` valida JobXML y XMP, estima calidad de imagen, alinea y crea un MASTER sin restricciones externas.
2. Revisar el informe `*_image_quality.json`; no se excluye ninguna fotografía automáticamente.
3. Marcar manualmente GCP y CP, preferentemente en 5 imágenes adecuadas; 3 es el mínimo absoluto justificado manualmente.
4. `validate_marking.py` valida el MASTER y registra la puerta manual.
5. `prepare_branches.py` crea `GCP_ONLY` y `GCP_P1` de forma no repetible.
6. `validate_before_optimize.py` debe dar PASS en cada rama.
7. Ejecutar `optimize_branch.py` en cada rama. El script exige un informe pre-optimize PASS reciente y usa exactamente el mismo conjunto bloqueado de parámetros.
8. Evaluar principalmente los Check Points. Con dos CP, la inferencia es exploratoria y debe declararse así.

## Selección de JobXML

Prioridad:

1. variable `PALMERI_JOBXML`;
2. campo `jobxml` del vuelo;
3. `default_jobxml` de la campaña.

El modo individual usa `PALMERI_MODE=single` y `PALMERI_FLIGHT_DATE=AAAA-MM-DD`.

## Preset seleccionado

`MORPHOLOGY_MAX` usa imágenes a resolución original, 40 000 key points, 10 000 tie points, Generic Preselection, Guided Matching y Adaptive Camera Model Fitting. `Exclude stationary tie points` queda desactivado. Reference Preselection queda desactivado porque el piloto ya obtuvo conectividad completa y no debe confundirse el uso de GNSS para seleccionar pares con el uso de GNSS como restricción del bundle.

`BASELINE_A0` conserva los mismos parámetros salvo Guided Matching, para una comparación específica si fuera necesaria.

## Optimización bloqueada

Se ajustan `f`, `cx`, `cy`, `k1-k3` y `p1-p2`, con Adaptive Fitting y covarianza de tie points. No se ajustan `b1`, `b2`, `k4` ni correcciones adicionales. La elección evita ampliar innecesariamente el modelo en un bloque aéreo débil y mantiene idénticas ambas ramas. El script registra calibración y huellas de transformaciones antes y después.

## Estado de campañas

- 2025: preparado para repetir el piloto.
- 2026: el candidato recibido el 17/09/2026 (SHA-256 `3b8a66c5475505b90c7be77dfb9a42537971af963f0e01d55c307fa64aa7cd5`) pasa el parser al indicarle su ruta explícitamente. La ruta predeterminada aún contiene la copia anterior de 2025 y la campaña permanece bloqueada. Tras el dictamen geomático, copiar el JobXML aceptado a `control/jobxml/2026-GPS-ensayopalmeri-poveda.jxl`; los JobXML están excluidos de Git.

## Pruebas locales

```powershell
python -m unittest discover -s tests -v
```

Las pruebas puras no requieren Metashape. La prueba de integración requiere Metashape 2.3 y los JPG originales.
