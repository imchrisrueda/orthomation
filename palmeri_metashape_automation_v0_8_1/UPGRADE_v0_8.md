# v0.8 — promoción INCOMPLETE -> MASTER

## Cambio principal

El proyecto se procesa en:

`work/<fecha>/RGB_P1/*_INCOMPLETE.psx`

Si alguna etapa falla, ese proyecto se conserva para diagnóstico.

Si todas las validaciones pasan, por defecto:

1. se guarda el proyecto INCOMPLETE;
2. se liberan los manejadores del documento Metashape;
3. se mueve/renombra el par `.psx` + `.files`;
4. se convierte en `projects/.../*_MASTER.psx`;
5. se vuelve a abrir el MASTER en modo lectura;
6. se ejecuta de nuevo la validación final;
7. se eliminan las carpetas `work/<fecha>/RGB_P1` vacías.

Por tanto, tras una ejecución correcta no queda una segunda copia completa.

## Configuración

En `config/global.json`:

```json
"processing": {
  "keep_incomplete_on_success": false,
  "verify_promoted_master": true
}
```

### `keep_incomplete_on_success: false`
Modo recomendado. Se PROMUEVE mediante move/rename y no queda duplicado.

### `keep_incomplete_on_success: true`
Modo de depuración. Se conserva INCOMPLETE y se crea también MASTER.

### `verify_promoted_master: true`
Después de la promoción, el MASTER se vuelve a abrir y se valida.

## Si falla el procesamiento

El INCOMPLETE se conserva deliberadamente en `work/`.

No se crea un MASTER válido.
