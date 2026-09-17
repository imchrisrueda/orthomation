# Estado actual de Orthomation

Fecha: 2026-09-17.

## Resultado alcanzado

Se ha creado `palmeri_metashape_adapter_v0_9_0` como nueva base, manteniendo intactos `palmeri_metashape_automation_v0_8_1` y `palmeri_metashape_v8_0_2` para trazabilidad.

La v0.9.0 ya no depende de CSV con alturas provisionales. Integra directamente el JobXML, usa altura elipsoidal, aplica precisiones individuales, valida XMP P1, registra QA de imagen y controla el paso MASTER -> marcado manual -> ramas -> validación pre-optimización.

## Verificaciones ejecutadas

- Sintaxis Python de todos los scripts: correcta.
- JSON de configuración: correcto.
- Pruebas unitarias puras: 3/3 correctas.
- Parser JobXML 2025: seis puntos, `NetworkFix`, EGM08IGN, año y precisiones correctos.
- XMP reales del piloto: 43/43 válidos, RTK fixed y altura elipsoidal coherente.
- Diferencia cámara-terreno elipsoidal observada: 14,558-14,960 m.
- JobXML denominado 2026: rechazado por ser idéntico al de 2025.
- Prueba directa con Metashape 2.3.1: carga correcta de ubicación, precisión XMP, `AnalyzeImages` y precisión individual de marcador.
- Firma de `optimizeCameras` comprobada y script de optimización bloqueada implementado.
- Manifiesto `SHA256SUMS.txt`: 30 entradas verificadas, sin fallos.

## Lo que todavía no se ha ejecutado

- No se ha reprocesado el piloto fotogramétrico con v0.9.0.
- No se ha validado visualmente la calidad de las imágenes señaladas por Metashape.
- No se han repetido los marcados en el nuevo MASTER.
- No se han optimizado las ramas.
- No se han generado nube, DSM/DTM u ortomosaico.
- No se ha implementado el adaptador Pix4D.

## Bloqueos

- Campaña 2026: el JobXML recibido en la raíz del repo supera la validación automática cuando se pasa explícitamente al parser (seis puntos; Trimble JobXML 5.72; observaciones de 2026; ETRS89 / UTM 30 North; EGM08IGN). La ruta predeterminada configurada, `palmeri_metashape_adapter_v0_9_0/control/jobxml/2026-GPS-ensayopalmeri-poveda.jxl`, todavía contiene el fichero anterior con SHA-256 de 2025, por lo que el flujo de campaña aún no acepta el nuevo fichero. La campaña sigue bloqueada hasta instalar la versión recibida en esa ruta local, obtener dictamen geomático y registrar su aceptación.
- Precisión horizontal Trimble: la asignación X=Y=Horizontal es provisional hasta confirmar su definición estadística.

El JobXML recibido se conserva localmente en la raíz del repo y está excluido de Git por contener datos de control. Su SHA-256 es `3b8a66c5475505b90c7be77dfb9a42537971af963f0e01d55c307fa64aa7cd5`. El fichero que aún está en la ruta configurada y el de 2025 tienen SHA-256 `877c73e9a409d41c1262adf6921713d009db4a395d977550755b15d8f2b63d18`.

## Punto seguro de reanudación

1. Revisar geomáticamente el candidato 2026 y, tras aceptación, colocarlo en la ruta local `control/jobxml/` configurada para la campaña.
2. Ejecutar las pruebas del paquete.
3. Ejecutar el inventario 2025.
4. Reprocesar solo el piloto 29/04/2025.
5. Revisar calidad y marcar GCP/CP.
6. Validar el marcado y crear ramas.

No debe ejecutarse el procesamiento masivo 2025 ni ningún vuelo 2026 antes de completar y aceptar el nuevo piloto.
