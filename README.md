# Presupuesto Público — Daniel Vidarte García

Página de una sola pieza: portada/autor → marco normativo (DL 1440) → tablero de seguimiento de la ejecución del gasto público peruano 2026 (datos abiertos del MEF, Consulta Amigable — Gasto Diario). Publicada en:

**https://seguimiento-presupuestal.vidartegarcia.com/**

## Qué hay en este repositorio

- `index.html` — la página completa (portada, DL 1440, y el tablero incrustado por `<iframe>`). Esto es lo que carga la URL raíz.
- `assets/*.jpg` — fotos de la portada.
- `tablero/index.html` — el tablero en sí: un archivo HTML/CSS/JS autocontenido (los datos ya están incrustados adentro como JSON; no depende de ningún backend). Se puede abrir solo (`/tablero/`) o incrustado dentro de `index.html`.
- `CNAME` — le dice a GitHub Pages que este sitio responde en `seguimiento-presupuestal.vidartegarcia.com`. No borrar.
- `build_dashboard_data.py` — lee el parquet crudo del MEF y genera los cubos agregados (`data/*.json`).
- `inject_data.py` — inyecta esos cubos dentro de la plantilla y genera `tablero/index.html`.

Los archivos originales del MEF (`ppto_mef.parquet`, ~260 MB) y la plantilla fuente (`dashboard_template.html`) **no viven aquí** — son demasiado grandes para un repo de git y no hace falta publicarlos. Viven en el proyecto local ("Seguimiento Presupuestal 2026").

## Cómo actualizar el tablero con datos nuevos

1. En el proyecto local, correr `1. Script de extracción/Script_01.R` para bajar la data más reciente del MEF (genera un `ppto_mef.parquet` nuevo).
2. Correr `4. Tablero/build_dashboard_data.py` — regenera los JSON en `4. Tablero/data/`.
3. Correr `4. Tablero/inject_data.py` — regenera el HTML del tablero.
4. Subir ese HTML a este repositorio como `tablero/index.html` (reemplazando el actual, mismo nombre) — por la interfaz web de GitHub ("Add file → Upload files") o con `git`. El `index.html` de la raíz (portada + DL 1440) normalmente no cambia.
5. GitHub Pages redespliega solo en menos de un minuto. No hace falta tocar nada más (ni el CNAME, ni el DNS).

No hay actualización automática — es un snapshot manual, a propósito: se actualiza cuando el usuario decida volver a correr el pipeline.

## Enlace a Power BI

La sección "Tablero" también enlaza a un reporte de Power BI más profundo (análisis del PIA, eficiencia por entidad, mapa) publicado con "Publicar en la web (público)". Si se vuelve a publicar esa URL cambia — hay que actualizar el `href` de `#pbiLink` en `index.html`.
