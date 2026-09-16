# v0.8.1 — corrección de rutas de fotografías

## Problema detectado en v0.8

Metashape podía guardar las rutas de las fotografías de forma relativa al proyecto
`*_INCOMPLETE.psx`.

Al mover el proyecto desde:

`...\2025\work\...`

a:

`...\2025\projects\metashape\...`

esas rutas relativas pasaban a resolverse desde otra carpeta y Metashape buscaba las
imágenes en una ubicación incorrecta.

## Solución

v0.8.1 fuerza:

```python
Metashape.app.settings.project_absolute_paths = True
```

antes de añadir/guardar las fotografías.

Además normaliza explícitamente:

```python
camera.photo.path = str(Path(camera.photo.path).resolve())
```

y valida que:

- todas las rutas sean absolutas;
- todos los archivos existan;
- la validación vuelva a pasar después de promover el MASTER.

## Configuración

`config/global.json`:

```json
"processing": {
  "keep_incomplete_on_success": false,
  "verify_promoted_master": true,
  "store_photo_paths_absolute": true
}
```

La promoción MOVE/RENAME se mantiene, pero ya no altera la localización de las
fotografías porque el proyecto conserva sus rutas absolutas.
