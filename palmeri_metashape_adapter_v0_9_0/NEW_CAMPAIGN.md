# Añadir una campaña o un JobXML específico de vuelo

1. Copiar `campaigns/_template_campaign.json` con el identificador deseado.
2. Copiar el JobXML a `control/jobxml/`.
3. Declarar año de levantamiento, geoide, CRS y correspondencia `job_id -> label/role`.
4. Para un JobXML común, usar `default_jobxml`.
5. Para un vuelo con control distinto, añadir `jobxml` dentro de ese vuelo.
6. Ejecutar primero el modo `inventory`. Un JobXML ausente, de otro año, sin precisión o con método distinto de `NetworkFix` bloquea el proceso.

No se mantienen CSV manuales paralelos: evita divergencias entre coordenadas, alturas, precisiones y trazabilidad.
