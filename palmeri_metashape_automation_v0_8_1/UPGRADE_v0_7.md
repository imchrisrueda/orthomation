# v0.6 -> v0.7

- Los GCP/CP se importan antes del alineamiento.
- Se valida su existencia antes de Match Photos.
- Los proyectos de trabajo usan `_INCOMPLETE.psx`.
- `_MASTER.psx` solo se crea después de una validación final satisfactoria.
- El directorio `work/` queda separado de `projects/`.
- Se mantiene Camera Reference en WGS84, Marker Reference en el CRS de campaña.
- Marker accuracy y projection accuracy siguen siendo específicos de campaña.
