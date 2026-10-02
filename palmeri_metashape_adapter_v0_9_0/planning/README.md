# Preparación offline de borradores

`identity.version` identifica la revisión del borrador; `identity.metashape_version` reserva la versión exacta declarada de software (`major.minor.patch`), inicialmente pendiente. Declararla no concede aprobación de esa versión. Las unidades del protocolo son metros para residuos, píxeles para reproyección y nativas de cada parámetro para calibración. El marco local del comparador se construye en la posición estimada.

Estos JSON son propuestas, separadas de `config/global.json` y de las campañas activas. Ningún script de procesamiento los consume. No autorizan fases ni productos; no existe promotor a configuración activa. Se conservan los parámetros de optimización vigentes, sin copiar las huellas, los 43/688 conteos ni la equivalencia/tolerancias del piloto a otros vuelos.

Desde la raíz del repositorio:

```powershell
python palmeri_metashape_adapter_v0_9_0/scripts/validate_planning.py
python palmeri_metashape_adapter_v0_9_0/scripts/validate_planning.py ruta_al_borrador.json
```

La CLI lee únicamente los JSON seleccionados y escribe un informe JSON redactado a stdout. Devuelve 0 para estructura válida, incluso incompleta; 1 para documento inválido; 2 para uso incorrecto. No genera archivos ni abre referencias documentales. Rechaza claves adicionales o ausentes, estados aprobados, tipos ambiguos y JSON duplicado/no finito. Los diagnósticos sólo contienen códigos y nombres de campos del esquema, nunca identificadores, huellas ni rutas suministrados. `schema_version=planning-1` es propia de preparación, no el esquema operativo 0.9.0.

En [_template_flight_contract.json](_template_flight_contract.json), se pueden completar manualmente identidad, fecha, versión de borrador, conteos esperados y evidencia declarada (`sha256`, `documentary_source`). `null` significa pendiente. Cada evidencia necesita una huella documental y su procedencia; la existencia o autenticidad del documento no se comprueba. Datum y época requieren evidencia independiente. El control, CRS y unidades son propuestas de la política del proyecto con aceptación `NOT_GRANTED`, sin atribuir aceptación a una campaña nueva. Cámara y marcadores mantienen altura elipsoidal h. Los estados admitidos del contrato son DRAFT, REVIEW_REQUIRED y REJECTED; las fases sólo REVIEW_REQUIRED o BLOCKED.

`structure_valid` comprueba la estructura. `evidence_complete` sólo significa que los campos declarativos ya no son nulos: no demuestra comparabilidad, aceptación humana, identidad de imágenes/MASTER ni evidencia científica. Incluso un contrato lleno sigue `REVIEW_REQUIRED`, `NOT_EXECUTABLE`, `evidence_verified=false`, `execution_authorized=false`, `products_authorized=false` y `geomatic_acceptance=NOT_GRANTED`. Revisión, marcado, selección de imágenes/exclusiones y selección de solución son gates humanos separados.

[evaluation_protocol.json](evaluation_protocol.json) conserva una propuesta fija y validable, pendiente de aceptación humana; no cierra FACTS §9. Separa evaluación geométrica previa de evaluación de productos posterior a selección humana y autorización registradas. Reserva evidencia de imágenes aceptadas/excluidas, MASTER común, marcado/proyecciones, calibración inicial, parámetros y restricciones de ramas; hashes y conteos solos no justifican comparabilidad. No calcula nuevas métricas, no ordena ramas y no define algoritmos ni umbrales de aceptación de productos.

CP C2/C5 se informan individualmente y agregados por separado de GCP, que representan ajuste interno. Dos CP aportan evidencia exploratoria, sin caracterización robusta, extrapolación espacial ni intervalos de confianza calculados desde n=2. El código vigente ofrece sesgos x/y/z y RMSE x/y/z/xy/3d; FACTS §9 menciona también sesgos XY/3D: esa discrepancia queda abierta, sin añadir cálculos. Residuos: estimated-reference en el marco local del comparador; deltas CRS 25830 separados y no usados para RMSE; delta de ramas GCP_P1-GCP_ONLY. La reproyección en píxeles indica consistencia interna, no exactitud externa; un cambio de calibración es diagnóstico, no prueba de sobreajuste. H sólo mediante transformación posterior explícita validada.

Limitaciones heredadas del comparador (FACTS §12/13): no verifica de nuevo CRS/GNSS/P1, huella exacta de imágenes ni ausencia actual de productos. La observación completa de parámetros efectivos posteriores y correcciones adicionales en API 2.3.1 sigue pendiente. Esta preparación sólo reserva evidencia declarada y no subsana esas limitaciones. Los contratos reales y el protocolo requieren aceptación geomática humana antes de cualquier especificación operativa posterior.

`reference_metadata` reserva datum, referencia elipsoidal de altura y época declarados, todos inicialmente nulos y con aceptación NOT_GRANTED. Cada valor requiere procedencia documental en la evidencia correspondiente. La época se expresa como cadena de año decimal (`YYYY` o `YYYY.fracción`, hasta ocho decimales), sin conversión numérica ni rango geodésico asumido. `source_review_status` conserva DRAFT/REVIEW_REQUIRED/REJECTED del documento; el estado del informe no revoca un rechazo.
