---
name: release-package
description: Preparar una versión del adaptador Orthomation con pruebas, documentación y exclusiones revisadas, sin publicarla automáticamente.
---

# Release package

Resuelve las rutas del paquete activo desde la raíz del repositorio, incluso si la sesión se inició en una subcarpeta.

Usar para preparar una versión, no para publicarla automáticamente.

1. Confirma alcance, versión objetivo, rama y autorizaciones necesarias.
2. Ejecuta pruebas relevantes y revisa resultados, documentación, changelog y Definition of Done.
3. Actualiza versión y manifiesto/hash sólo cuando el cambio lo requiera.
4. Revisa diff, archivos generados y exclusiones; excluye JobXML, imágenes, proyectos, datos de vuelo, secretos y salidas pesadas.
5. Prepara el commit/release con lista de cambios, pruebas, hashes, riesgos y pendientes. Publicar, etiquetar o subir requiere autorización explícita.
