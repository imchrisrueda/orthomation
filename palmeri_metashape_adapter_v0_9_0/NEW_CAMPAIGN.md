# Añadir una campaña o un JobXML específico de vuelo

1. Copiar `campaigns/_template_campaign.json` a `campaigns/<id>.json`, usar un identificador estable y mantener `status` como `BLOCKED_REVIEW` mientras la campaña no tenga revisión geomática aprobada. El adaptador rechaza estados que empiezan por `BLOCKED`.
2. Copiar el JobXML aprobado a `control/jobxml/`. Los `*.jxl` están excluidos de Git; intercambiar los originales por un canal autorizado.
3. Configurar año observado esperado, geoide, CRS, método requerido y correspondencia completa `job_id -> label/role`. Comprobar los roles con geomatic_agent: los Check Points nunca entran al ajuste.
4. Para un JobXML común, usar `default_jobxml`. Para un vuelo con control distinto, añadir `jobxml` en la definición de ese vuelo. Verificar que el archivo local existe en la ruta que realmente resolverá la configuración.
5. Revisar todas las rutas `input_dir` y configurar `generated_root` en `config/global.json`. Confirmar que cada carpeta corresponde al vuelo correcto y que contiene el conjunto de imágenes previsto.
6. Tras aprobación geomática, quitar el estado `BLOCKED_*`, ejecutar primero el modo `inventory` y revisar el informe y los logs. Un JobXML ausente, de otro año, sin precisión, con advertencia de precisión o con método distinto de `NetworkFix` invalida el vuelo.
7. Seguir el flujo completo del [README del adaptador](README.md), empezando por el piloto. No procesar vuelos restantes ni campañas completas antes de aceptar el piloto.

No se mantienen CSV manuales paralelos: evita divergencias entre coordenadas, alturas, precisiones y trazabilidad.
