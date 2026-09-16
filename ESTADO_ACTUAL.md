# Estado actual de Orthomation

Fecha: 2026-09-16.

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

- Campaña 2026: falta el JobXML 2026 auténtico.
- Precisión horizontal Trimble: la asignación X=Y=Horizontal es provisional hasta confirmar su definición estadística.

## Punto seguro de reanudación

1. Ejecutar las pruebas del paquete.
2. Ejecutar el inventario 2025.
3. Reprocesar solo el piloto 29/04/2025.
4. Revisar calidad y marcar GCP/CP.
5. Validar el marcado y crear ramas.

No debe ejecutarse el procesamiento masivo 2025 ni ningún vuelo 2026 antes de completar y aceptar el nuevo piloto.
